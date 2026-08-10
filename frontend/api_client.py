"""
HTTP client for the Public Pulse Streamlit frontend.

This module is responsible for communication between
the Streamlit frontend and the FastAPI backend.
"""

import requests


API_BASE_URL = "http://127.0.0.1:8000"


class APIClientError(RuntimeError):
    """
    Raised when communication with the FastAPI backend fails.
    """


def _authorization_headers(
        access_token: str,
) -> dict[str, str]:
    """
    Build the Authorization header required by protected endpoints.

    Example:

    Authorization: Bearer eyJhbGciOi...
    """

    return {
        "Authorization": f"Bearer {access_token}",
    }


def _get_error_detail(
        response: requests.Response,
        default_message: str,
) -> str:
    """
    Extract FastAPI's error message from an HTTP response.

    FastAPI usually returns errors like:

    {
        "detail": "Something went wrong"
    }

    If the response is not JSON, return the fallback message.
    """

    try:
        response_data = response.json()

    except ValueError:
        return default_message

    detail = response_data.get(
        "detail",
        default_message,
    )

    return str(detail)


# ---------------------------------------------------------
# Authentication
# ---------------------------------------------------------


def register_user(
        *,
        name: str,
        email: str,
        phone: str,
        password: str,
) -> dict:
    """
    Register a new Public Pulse user.
    """

    try:
        response = requests.post(
            f"{API_BASE_URL}/auth/register",
            json={
                "name": name,
                "email": email,
                "phone": phone,
                "password": password,
            },
            timeout=10,
        )

    except requests.RequestException as exc:
        raise APIClientError(
            "Could not connect to the Public Pulse backend."
        ) from exc

    if response.status_code not in {200, 201}:
        raise APIClientError(
            _get_error_detail(
                response,
                "Registration failed.",
            )
        )

    return response.json()


def login_user(
        *,
        email: str,
        password: str,
) -> dict:
    """
    Login using the normal Public Pulse JSON endpoint.

    POST /auth/login

    Request body:

    {
        "email": "...",
        "password": "..."
    }
    """

    try:
        response = requests.post(
            f"{API_BASE_URL}/auth/login",
            json={
                "email": email,
                "password": password,
            },
            timeout=10,
        )

    except requests.RequestException as exc:
        raise APIClientError(
            "Could not connect to the Public Pulse backend."
        ) from exc

    if response.status_code != 200:
        raise APIClientError(
            _get_error_detail(
                response,
                "Login failed.",
            )
        )

    return response.json()


# ---------------------------------------------------------
# Gmail
# ---------------------------------------------------------


def get_gmail_status(
        *,
        access_token: str,
) -> dict:
    """
    Ask FastAPI whether the logged-in user has connected Gmail.

    GET /gmail/status
    """

    try:
        response = requests.get(
            f"{API_BASE_URL}/gmail/status",
            headers=_authorization_headers(
                access_token,
            ),
            timeout=10,
        )

    except requests.RequestException as exc:
        raise APIClientError(
            "Could not check Gmail connection status."
        ) from exc

    if response.status_code != 200:
        raise APIClientError(
            _get_error_detail(
                response,
                "Could not check Gmail connection status.",
            )
        )

    return response.json()


def get_gmail_connect_url(
        *,
        access_token: str,
) -> str:
    """
    Begin the Gmail OAuth connection.

    GET /gmail/connect returns a 302 redirect to Google.

    We intentionally DO NOT follow that redirect here.

    Instead, we take Google's authorization URL from the
    Location header and give it back to Streamlit.
    """

    try:
        response = requests.get(
            f"{API_BASE_URL}/gmail/connect",

            headers=_authorization_headers(
                access_token,
            ),

            # Important:
            # We want the Google URL itself.
            # Do not let requests follow the redirect.
            allow_redirects=False,

            timeout=10,
        )

    except requests.RequestException as exc:
        raise APIClientError(
            "Could not start Gmail connection."
        ) from exc

    if response.status_code not in {
        302,
        307,
    }:
        raise APIClientError(
            _get_error_detail(
                response,
                "Could not start Gmail connection.",
            )
        )

    google_url = response.headers.get(
        "location",
    )

    if not google_url:
        raise APIClientError(
            "Google authorization URL was missing."
        )

    return google_url


def disconnect_gmail(
        *,
        access_token: str,
) -> dict:
    """
    Disconnect Gmail from the logged-in Public Pulse user.

    DELETE /gmail/disconnect
    """

    try:
        response = requests.delete(
            f"{API_BASE_URL}/gmail/disconnect",
            headers=_authorization_headers(
                access_token,
            ),
            timeout=10,
        )

    except requests.RequestException as exc:
        raise APIClientError(
            "Could not disconnect Gmail."
        ) from exc

    if response.status_code != 200:
        raise APIClientError(
            _get_error_detail(
                response,
                "Could not disconnect Gmail.",
            )
        )

    return response.json()