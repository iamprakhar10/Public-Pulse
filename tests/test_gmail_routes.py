"""
HTTP-level tests for Gmail OAuth routes.

External Google calls are mocked. These tests verify FastAPI routing,
query parameters, status codes, and response bodies.
"""

from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.main import app
from app.services import gmail_oauth
from app.services.gmail_oauth import (
    GmailConnectionResult,
    GoogleAccountAlreadyConnectedError,
)
from app.services.gmail_oauth_state import (
    InvalidOAuthStateError,
)


client = TestClient(app)


def test_gmail_callback_success(
        monkeypatch,
) -> None:
    """
    A valid callback should return a successful connection response.
    """

    def fake_complete_connection(
            db,
            state,
            authorization_code,
            config,
            encryption_key,
    ) -> GmailConnectionResult:
        assert state == "valid-state"
        assert authorization_code == "valid-code"

        return GmailConnectionResult(
            user_id=1,
            google_account_id="google-user-123",
            google_email="connected@gmail.com",
            scopes=(
                "openid "
                "https://www.googleapis.com/auth/gmail.send"
            ),
        )

    monkeypatch.setattr(
        "app.routers.gmail.complete_gmail_oauth_connection",
        fake_complete_connection,
    )

    monkeypatch.setattr(
        "app.routers.gmail.get_google_oauth_config",
        lambda: SimpleNamespace(
            client_id="test-client",
            client_secret="test-secret",
            redirect_uri=(
                "http://127.0.0.1:8000/gmail/callback"
            ),
        ),
    )

    monkeypatch.setattr(
        "app.routers.gmail.get_token_encryption_key",
        lambda: "test-encryption-key",
    )

    response = client.get(
        "/gmail/callback",
        params={
            "code": "valid-code",
            "state": "valid-state",
        },
        follow_redirects=False,
    )

    assert response.status_code == 302
    assert response.headers["location"] == "http://localhost:8501"
    # assert response.json() == {
    #     "message": "Gmail connected successfully.",
    #     "google_email": "connected@gmail.com",
    # }


def test_gmail_callback_missing_code() -> None:
    """
    Google callbacks without an authorization code must be rejected.
    """

    response = client.get(
        "/gmail/callback",
        params={
            "state": "valid-state",
        },
    )

    assert response.status_code == 400
    assert (
        response.json()["detail"]
        == "Google authorization code is missing."
    )


def test_gmail_callback_missing_state() -> None:
    """
    Google callbacks without state must be rejected.
    """

    response = client.get(
        "/gmail/callback",
        params={
            "code": "valid-code",
        },
    )

    assert response.status_code == 400
    assert (
        response.json()["detail"]
        == "OAuth state is missing."
    )


def test_gmail_callback_google_denied_access() -> None:
    """
    Google may redirect back with an error when the user presses Cancel.
    """

    response = client.get(
        "/gmail/callback",
        params={
            "error": "access_denied",
        },
    )

    assert response.status_code == 400
    assert "access_denied" in response.json()["detail"]


def test_gmail_callback_invalid_state(
        monkeypatch,
) -> None:
    """
    Invalid OAuth state should become an HTTP 400 response.
    """

    def fake_complete_connection(**kwargs):
        raise InvalidOAuthStateError(
            "OAuth state is invalid."
        )

    monkeypatch.setattr(
        "app.routers.gmail.complete_gmail_oauth_connection",
        fake_complete_connection,
    )

    monkeypatch.setattr(
        "app.routers.gmail.get_google_oauth_config",
        lambda: SimpleNamespace(),
    )

    monkeypatch.setattr(
        "app.routers.gmail.get_token_encryption_key",
        lambda: "test-key",
    )

    response = client.get(
        "/gmail/callback",
        params={
            "code": "valid-code",
            "state": "invalid-state",
        },
    )

    assert response.status_code == 400
    assert "invalid" in response.json()["detail"]


def test_gmail_callback_google_account_conflict(
        monkeypatch,
) -> None:
    """
    A Google account already linked to another user should return 409.
    """

    def fake_complete_connection(**kwargs):
        raise GoogleAccountAlreadyConnectedError(
            "This Google account is already connected to another "
            "Public Pulse user."
        )

    monkeypatch.setattr(
        "app.routers.gmail.complete_gmail_oauth_connection",
        fake_complete_connection,
    )

    monkeypatch.setattr(
        "app.routers.gmail.get_google_oauth_config",
        lambda: SimpleNamespace(),
    )

    monkeypatch.setattr(
        "app.routers.gmail.get_token_encryption_key",
        lambda: "test-key",
    )

    response = client.get(
        "/gmail/callback",
        params={
            "code": "valid-code",
            "state": "valid-state",
        },
    )

    assert response.status_code == 409