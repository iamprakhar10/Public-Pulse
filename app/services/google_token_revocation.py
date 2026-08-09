"""
Google OAuth token revocation

when a user will disconnect gmail, public uplse should revoke
the stored Google refresh token before deleting it locally
"""

import requests

GOOGLE_REVOCATION_URL = "https://oauth2.googleapis.com/revoke"



class GoogleTokenRevocationError(RuntimeError):
    """
    This error will be raised when google cannot revoke the
    OAuth refresh token
    """


def revoke_google_token(
        token: str,
) -> None:
    """
    Revokes a google OAuth access or refresh token

    Public pulse uses this with stored refresh token when the
    user disconnects gmail
    """

    if not token:
        raise GoogleTokenRevocationError(
            "Google token is required for revocation."
        )

    try:
        response = requests.post(
            GOOGLE_REVOCATION_URL,
            params={
                'token': token,
            },
            timeout=10,
        )

    except requests.RequestException as exc:
        raise GoogleTokenRevocationError(
            " Could not contact Google to revoke Gmail access."
        ) from exc

    if response.status_code != 200:
        raise GoogleTokenRevocationError(
            " Google could not revoke Gmail access."
        )