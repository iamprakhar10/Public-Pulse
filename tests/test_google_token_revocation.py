"""
Tests for Google OAuth token revocation.

No real Google requests are made.
"""

from unittest.mock import MagicMock

import pytest
import requests

from app.services import google_token_revocation
from app.services.google_token_revocation import (
    GOOGLE_REVOCATION_URL,
    GoogleTokenRevocationError,
    revoke_google_token,
)


def test_revoke_google_token(
        monkeypatch,
) -> None:
    """
    A successful Google revocation should complete without error.
    """

    fake_response = MagicMock()
    fake_response.status_code = 200

    fake_post = MagicMock(
        return_value=fake_response,
    )

    monkeypatch.setattr(
        google_token_revocation.requests,
        "post",
        fake_post,
    )

    revoke_google_token(
        token="test-refresh-token",
    )

    fake_post.assert_called_once_with(
        GOOGLE_REVOCATION_URL,
        params={
            "token": "test-refresh-token",
        },
        timeout=10,
    )


def test_revoke_google_token_requires_token() -> None:
    """
    Revocation cannot happen without a token.
    """

    with pytest.raises(
        GoogleTokenRevocationError,
        match="required",
    ):
        revoke_google_token(
            token="",
        )


def test_revoke_google_token_google_failure(
        monkeypatch,
) -> None:
    """
    A non-200 Google response should become a domain error.
    """

    fake_response = MagicMock()
    fake_response.status_code = 400

    monkeypatch.setattr(
        google_token_revocation.requests,
        "post",
        MagicMock(
            return_value=fake_response,
        ),
    )

    with pytest.raises(
        GoogleTokenRevocationError,
        match="could not revoke",
    ):
        revoke_google_token(
            token="bad-refresh-token",
        )


def test_revoke_google_token_network_failure(
        monkeypatch,
) -> None:
    """
    Network failures should become a predictable domain error.
    """

    def fake_post(*args, **kwargs):
        raise requests.RequestException(
            "network unavailable"
        )

    monkeypatch.setattr(
        google_token_revocation.requests,
        "post",
        fake_post,
    )

    with pytest.raises(
        GoogleTokenRevocationError,
        match="Could not contact Google",
    ):
        revoke_google_token(
            token="test-refresh-token",
        )