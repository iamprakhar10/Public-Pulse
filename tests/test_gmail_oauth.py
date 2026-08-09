"""
Tests for Google OAuth URL creation.

These tests do not contact Google.
They verify that Public Pulse builds the authorization URL correctly,
including the PKCE code challenge.
"""

from urllib.parse import parse_qs, urlparse

import pytest

from app.config import GoogleOAuthConfig
from app.services.gmail_oauth import (
    build_google_authorization_url,
    MissingRequiredGoogleScopeError,
    validate_required_google_scopes,
)


@pytest.fixture
def google_config() -> GoogleOAuthConfig:
    """
    Return safe fake Google OAuth configuration for tests.

    These are not real credentials.
    """

    return GoogleOAuthConfig(
        client_id="test-client-id",
        client_secret="test-client-secret",
        redirect_uri=(
            "http://127.0.0.1:8000/gmail/callback"
        ),
    )


def test_build_google_authorization_url(
        google_config,
) -> None:
    """
    Google authorization URL should contain the values required
    for OAuth and PKCE.
    """

    authorization_url = build_google_authorization_url(
        config=google_config,
        state="test-state",

        # NEW:
        # The same verifier will later be recovered during
        # /gmail/callback and used for the token exchange.
        code_verifier="test-code-verifier",
    )

    parsed_url = urlparse(authorization_url)
    query = parse_qs(parsed_url.query)

    # We should be sending the browser to Google over HTTPS.
    assert parsed_url.scheme == "https"
    assert parsed_url.netloc == "accounts.google.com"

    # Public Pulse's Google OAuth client.
    assert query["client_id"] == [
        google_config.client_id
    ]

    # Google must redirect back to our callback endpoint.
    assert query["redirect_uri"] == [
        google_config.redirect_uri
    ]

    # We want an authorization code, not tokens directly
    # through the browser.
    assert query["response_type"] == ["code"]

    # State protects and identifies this particular OAuth flow.
    assert query["state"] == ["test-state"]

    # Offline access allows Google to issue a refresh token.
    assert query["access_type"] == ["offline"]

    # We explicitly ask Google for consent during development.
    assert query["prompt"] == ["consent"]

    # Gmail sending permission must be requested.
    scopes = query["scope"][0].split()

    assert (
        "https://www.googleapis.com/auth/gmail.send"
        in scopes
    )

    # OpenID scopes allow us to identify the Google account.
    assert "openid" in scopes

    assert (
        "https://www.googleapis.com/auth/userinfo.email"
        in scopes
    )

    # -----------------------------
    # PKCE checks
    # -----------------------------

    # Google should receive a code challenge derived from the
    # code_verifier.
    #
    # The verifier itself must NOT be sent in this browser URL.
    assert "code_challenge" in query

    # S256 means the verifier was transformed using SHA-256.
    assert query["code_challenge_method"] == ["S256"]

    # The secret verifier stays server-side.
    assert "code_verifier" not in query
    assert "test-code-verifier" not in authorization_url


def test_build_google_authorization_url_requires_state(
        google_config,
) -> None:
    """
    An OAuth authorization URL must not be created without state.
    """

    with pytest.raises(
        ValueError,
        match="state",
    ):
        build_google_authorization_url(
            config=google_config,
            state="",
            code_verifier="test-code-verifier",
        )


def test_build_google_authorization_url_requires_code_verifier(
        google_config,
) -> None:
    """
    PKCE requires a code verifier for the OAuth transaction.
    """

    with pytest.raises(
        ValueError,
        match="verifier",
    ):
        build_google_authorization_url(
            config=google_config,
            state="test-state",
            code_verifier="",
        )


def test_validate_required_google_scopes_accepts_gmail_send() -> None:
    """
    gmail.send should satisfy Public Pulse's required Gmail permission.
    """

    validate_required_google_scopes(
        granted_scopes=[
            "openid",
            "https://www.googleapis.com/auth/userinfo.email",
            "https://www.googleapis.com/auth/gmail.send",
        ],
    )


def test_validate_required_google_scopes_rejects_missing_gmail_send() -> None:
    """
    OAuth connection must fail when the user does not grant gmail.send.
    """

    with pytest.raises(
        MissingRequiredGoogleScopeError,
        match="sending permission",
    ):
        validate_required_google_scopes(
            granted_scopes=[
                "openid",
                "https://www.googleapis.com/auth/userinfo.email",
            ],
        )