from urllib.parse import parse_qs, urlparse

import pytest

from app.config import GoogleOAuthConfig
from app.services.gmail_oauth import (
    GMAIL_SEND_SCOPE,
    build_google_authorization_url,
)


@pytest.fixture
def google_config() -> GoogleOAuthConfig:
    """
    Provide non-secret Google OAuth configuration for tests.
    """

    return GoogleOAuthConfig(
        client_id=(
            "test-client-id.apps.googleusercontent.com"
        ),
        client_secret="test-client-secret",
        redirect_uri=(
            "http://127.0.0.1:8000/gmail/callback"
        ),
    )


def test_build_google_authorization_url(
        google_config,
) -> None:
    """
    The generated URL should contain the values required by Google's
    authorization endpoint.
    """

    state = "secure-test-state"

    authorization_url = build_google_authorization_url(
        config=google_config,
        state=state,
    )

    parsed_url = urlparse(authorization_url)
    query = parse_qs(parsed_url.query)

    assert parsed_url.scheme == "https"
    assert parsed_url.netloc == "accounts.google.com"

    assert query["client_id"] == [
        google_config.client_id
    ]

    assert query["redirect_uri"] == [
        google_config.redirect_uri
    ]

    assert query["response_type"] == ["code"]
    assert query["state"] == [state]
    assert query["access_type"] == ["offline"]
    assert query["prompt"] == ["consent"]

    requested_scopes = set(
        query["scope"][0].split()
    )

    assert GMAIL_SEND_SCOPE in requested_scopes
    assert "openid" in requested_scopes
    assert (
        "https://www.googleapis.com/auth/userinfo.email"
        in requested_scopes
    )


def test_build_google_authorization_url_requires_state(
        google_config,
) -> None:
    """
    An authorization URL must never be created without state.
    """

    with pytest.raises(
        ValueError,
        match="OAuth state is required",
    ):
        build_google_authorization_url(
            config=google_config,
            state="",
        )