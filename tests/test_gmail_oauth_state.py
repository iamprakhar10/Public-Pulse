"""
Tests for Gmail OAuth state creation and consumption.
"""

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import delete, select

from app.database.db import SessionLocal
from app.database.models import (
    GmailOAuthState,
    User,
)
from app.services.gmail_oauth_state import (
    InvalidOAuthStateError,
    consume_oauth_state,
    create_oauth_state,
    hash_oauth_state,
)
from app.utils.security import hash_password


TEST_EMAIL = "oauth-state-test@example.com"
TEST_PHONE = "9333333333"


@pytest.fixture
def db_session():
    """
    Provide a clean database session for OAuth-state tests.
    """

    db = SessionLocal()

    try:
        # Clean dependent rows first.
        db.execute(delete(GmailOAuthState))

        db.execute(
            delete(User).where(
                User.email == TEST_EMAIL,
            )
        )

        db.commit()

        yield db

    finally:
        db.rollback()

        db.execute(delete(GmailOAuthState))

        db.execute(
            delete(User).where(
                User.email == TEST_EMAIL,
            )
        )

        db.commit()
        db.close()


@pytest.fixture
def test_user(
        db_session,
) -> User:
    """
    Create a real database user for OAuth-state tests.

    GmailOAuthState.user_id is a foreign key, so the referenced
    user must actually exist.
    """

    user = User(
        name="OAuth State Test User",
        email=TEST_EMAIL,
        phone=TEST_PHONE,
        hashed_password=hash_password(
            "test-password",
        ),
    )

    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    return user


def test_create_and_consume_oauth_state(
        db_session,
        test_user,
) -> None:
    """
    A newly created OAuth state should be consumable once.

    The PKCE verifier recovered during callback must be the same
    verifier created when the OAuth flow started.
    """

    state, code_verifier = create_oauth_state(
        db=db_session,
        user_id=test_user.id,
    )

    assert state
    assert code_verifier

    user_id, consumed_code_verifier = consume_oauth_state(
        db=db_session,
        state=state,
    )

    assert user_id == test_user.id
    assert consumed_code_verifier == code_verifier


def test_plain_state_is_not_stored(
        db_session,
        test_user,
) -> None:
    """
    The plaintext OAuth state must not be stored in PostgreSQL.
    """

    state, _code_verifier = create_oauth_state(
        db=db_session,
        user_id=test_user.id,
    )

    stored_state = db_session.execute(
        select(GmailOAuthState)
    ).scalar_one()

    assert stored_state.state_hash != state

    assert (
        stored_state.state_hash
        == hash_oauth_state(state)
    )


def test_oauth_state_cannot_be_used_twice(
        db_session,
        test_user,
) -> None:
    """
    OAuth state should only be usable once.
    """

    state, _code_verifier = create_oauth_state(
        db=db_session,
        user_id=test_user.id,
    )

    # First use succeeds.
    consume_oauth_state(
        db=db_session,
        state=state,
    )

    # Second use must fail.
    with pytest.raises(
        InvalidOAuthStateError,
        match="used",
    ):
        consume_oauth_state(
            db=db_session,
            state=state,
        )


def test_unknown_oauth_state_is_rejected(
        db_session,
) -> None:
    """
    A state Public Pulse never created must be rejected.
    """

    with pytest.raises(
        InvalidOAuthStateError,
        match="invalid",
    ):
        consume_oauth_state(
            db=db_session,
            state="this-state-was-never-created",
        )


def test_expired_oauth_state_is_rejected(
        db_session,
        test_user,
) -> None:
    """
    An expired OAuth state must be rejected.
    """

    state = "expired-test-state"

    oauth_state = GmailOAuthState(
        user_id=test_user.id,
        state_hash=hash_oauth_state(state),
        code_verifier="expired-test-code-verifier",
        expires_at=(
            datetime.now(timezone.utc)
            - timedelta(minutes=1)
        ),
    )

    db_session.add(oauth_state)
    db_session.commit()

    with pytest.raises(
        InvalidOAuthStateError,
        match="expired",
    ):
        consume_oauth_state(
            db=db_session,
            state=state,
        )