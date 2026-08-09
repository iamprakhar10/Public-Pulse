"""
HTTP client for the public pulse streamlit frontend

This file is only responsible for talking to the FastAPI backend
and then giving results back to thhe UI
"""

import requests



API_BASE_URL = "http://127.0.0.1:8000"




class APIClientError(RuntimeError):
    """
    Raised when a frontend request to FastAPI fails
    """



def register_user(
        *,
        name:str,
        email: str,
        phone: str,
        password: str,
) -> dict:
    """
    Register a new Public pulse user
    """

    try:
        response = requests.post(
            f"{API_BASE_URL}/auth/register",

            # Convert this Python dictionary into JSON and
            # send it as the HTTP request body.
            json={
                "name": name,
                "email": email,
                "phone": phone,
                "password": password,
            },

            # If FastAPI doesn't answer within 10 seconds,
            # requests stops waiting and raises an exception.
            timeout=10,
        )
    # Catch networking-related errors produced by requests.
    except requests.RequestException as exc:
        raise APIClientError(
            "Could not connect to the public pulse backend."
        ) from exc
# from exc preserves the original exception relationship.
# So conceptually:
# requests.ConnectionError
#           ↓
# APIClientError
    if response.status_code not in {200, 201}:
        try:
            # FastAPI errors commonly look like:

            # {
            #   "detail": "Email already registered"
            # }
            detail = response.json().get(
                'detail',
                'Registration failed.',
            )
        except ValueError:
            detail = "Registration failed."

        raise APIClientError(str(detail))

    return response.json()





def login_user(
        *,
        email: str,
        password: str,
) -> dict:
    """
    Login to public pulse and return the token response
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
            "Could not connect to the Public pulse backend."
        ) from exc

    if response.status_code != 200:
        try:
            detail = response.json().get(
                "detail",
                "Login failed.",
            )
        except ValueError:
            detail = "Login failed."

        raise APIClientError(
            str(detail),
        )

    return response.json()