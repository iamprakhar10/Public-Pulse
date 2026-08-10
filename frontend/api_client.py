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





def start_complaint(
        *,
        access_token: str,
        message: str,
) -> dict:
    """
    Start a new complaint conversation.

    POST /complaints

    The first user message is sent in the JSON body
    """

    try :
        response = requests.post(
            f"{API_BASE_URL}/complaints",
            headers=_authorization_headers(
                access_token,
            ),
            json={
                'message': message,
            },
            timeout=60,
        )

    except requests.RequestException as exc:
        raise APIClientError(
            "Could not start the complaint."
        ) from exc

    if response.status_code != 201:
        raise APIClientError(
            _get_error_detail(
                response,
                "Could not start the complaint.",
            )
        )

    return response.json()






def send_complaint_message(
        *,
        access_token: str,
        complaint_id: int,
        content: str,
) -> dict:
    """
    Add another user message to an existing complaint

    POST /complaints/{complaint_id}/messages

    The backend runs the complaint workflow again and returns
    the updated complaint conversation
    """
    try:
        response = requests.post(
            f"{API_BASE_URL}/complaints/"
            f"{complaint_id}/messages",
            headers=_authorization_headers(
                access_token,
            ),
            json={
                "content": content,
            },
# Here we set timeout=60 instead of 10 because these complaint messages can 
# run our entire Langgraph/LLM workflow, so ti may take some more time
# than simplae login request 
            timeout=60
        )

    except requests.RequestException as exc:
        raise APIClientError(
            "Could not send the complaint message."
        ) from exc

    if response.status_code != 201:
        raise APIClientError(
            _get_error_detail(
                response,
                "Could not send the complaint message.",
            )
        )

    return response.json()



def generate_email_draft(
        *,
        access_token: str,
        complaint_id: int,
) -> dict:
    """
    Generate and save email draft from completed complaint

    POST /complaints/{complaint_id}/email-draft
    """

    try :
        response = requests.post(
            (
                f"{API_BASE_URL}/complaints/"
                f"{complaint_id}/email-draft"
            ),
            headers=_authorization_headers(
                access_token,
            ),
            timeout=60,
        )

    except requests.RequestException as exc:
        raise APIClientError(
            "Could not generate the email draft."
        ) from exc

    if response.status_code != 201:
        raise APIClientError(
            _get_error_detail(
                response,
                "Could not generate the email draft."
            )
        )

    return response.json()





def update_email_draft(
        *,
        access_token: str,
        complaint_id: int,
        subject: str,
        body: str,
) -> dict:
    """
    Save user edits to an existing complaint email draft.

    PATCH /complaints/{complaint_id}/email-draft
    """

    try:
        response = requests.patch(
            (
                f"{API_BASE_URL}/complaints/"
                f"{complaint_id}/email-draft"
            ),
            headers=_authorization_headers(
                access_token,
            ),
            json={
                "subject": subject,
                "body": body,
            },
            timeout=10,
        )

    except requests.RequestException as exc:
        raise APIClientError(
            "Could not update the email draft."
        ) from exc

    if response.status_code != 200:
        raise APIClientError(
            _get_error_detail(
                response,
                "Could not update the email draft.",
            )
        )

    return response.json()






def approve_email_draft(
        *,
        access_token: str,
        complaint_id: int,
) -> dict:
    """
    Approve the current complaint email draft.

    POST /complaints/{compleint_id}/approve
    """

    try:
        response = requests.post(
            (
                f"{API_BASE_URL}/complaints/"
                f"{complaint_id}/approve"
            ),
            headers=_authorization_headers(
                access_token,
            ),
            timeout=10,
        )

    except requests.RequestException as exc:
        raise APIClientError(
            "Could not approve the email."
        ) from exc

    if response.status_code != 200:
        raise APIClientError(
            _get_error_detail(
                response,
                'Could not approve the email.'
            )
        )

    return response.json()



def send_complaint_email(
        *,
        access_token: str,
        complaint_id: int,
) -> dict:
    """
    Send an approved complaint email through the user's gmail

    POST /complaints/{complaint_id}/send
    """

    try:
        response = requests.post(
            (
                f"{API_BASE_URL}/complaints/"
                f"{complaint_id}/send"
            ),
            headers=_authorization_headers(
                access_token,
            ),
            timeout=60,
        )

    except requests.RequestException as exc:
        raise APIClientError(
            "Could not send the complaint email."
        ) from exc

    if response.status_code != 200:
        raise APIClientError(
            _get_error_detail(
                response,
                "Could not send the complaint email."
            )
        )

    return response.json()





# ---------------------------------------------------------
# Complaint history
# ---------------------------------------------------------


def get_my_complaints(
        *,
        access_token: str,
) -> list[dict]:
    """
    Fetch all complaints belonging to the logged-in user.

    GET /complaints
    """

    try:
        response = requests.get(
            f"{API_BASE_URL}/complaints",
            headers=_authorization_headers(
                access_token,
            ),
            timeout=10,
        )

    except requests.RequestException as exc:
        raise APIClientError(
            "Could not load your complaints."
        ) from exc

    if response.status_code != 200:
        raise APIClientError(
            _get_error_detail(
                response,
                "Could not load your complaints.",
            )
        )

    return response.json()






def get_complaint(
        *,
        access_token: str,
        complaint_id: int,
) -> dict:
    """
    Fetch one complaint together with its full conversation history.

    GET /complaints/{complaint_id}
    """

    try:
        response = requests.get(
            (
                f"{API_BASE_URL}/complaints/"
                f"{complaint_id}"
            ),
            headers=_authorization_headers(
                access_token,
            ),
            timeout=10,
        )

    except requests.RequestException as exc:
        raise APIClientError(
            "Could not load the complaint."
        ) from exc

    if response.status_code != 200:
        raise APIClientError(
            _get_error_detail(
                response,
                "Could not load the complaint.",
            )
        )

    return response.json()