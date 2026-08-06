"""
Secure state handling for google OAuth

The original random state value is sent through the browser
only it's SHA-256 has is stored in postgresql
"""

import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.models import GmailOAuthState


class InvalidOAuthStateError(ValueError):
    """
    This will be raised when an OAuth state is missing, expired,
    used, or unknown
    """


def hash_oauth_state(state:str) -> str:
    """
    Creates a SHA-256 hash of an OAuth state value.

    Unlike refresh tokens, state doesn't need to be recovered
    from the database, therefore hashing is approproiate
    """

    if not state:
        raise InvalidOAuthStateError(
            "OAuth state can't be empty"
        )

    return hashlib.sha256(
        state.encode('utf-8'),
    ).hexdigest()


def create_oauth_state(
        db: Session,
        user_id: int,
        lifetime_minutes: int = 10,
) -> str:
    """
    Generate and store a short lived oauth state

    Returns the original random value that will be sent to google.
    PostgreSQL will only store it's hash.
    """

    if lifetime_minutes <= 0:
        raise ValueError(
            "OAuth state lifetime must be positive"
        )

    # Generating a cryptographically secure, unpredictable
    # value 
    state = secrets.token_urlsafe(32)

    oauth_state = GmailOAuthState(
        user_id=user_id,
        state_hash=hash_oauth_state(state),
        expires_at=(
            datetime.now(timezone.utc)
            + timedelta(minutes=lifetime_minutes)
        ),
    )

    db.add(oauth_state)
    db.commit()

    return state






def consume_oauth_state(
        db: Session,
        state: str,
) -> int:
    """
    Validate and permanently consume an OAuth state

    returns the public pulse user id that started the
    OAuth flow

    A state can only be used once
    """

    state_hash = hash_oauth_state(state)

    statement = (
        select(GmailOAuthState)
        .where(
            GmailOAuthState.state_hash== state_hash,
        )
    )

    oauth_state = db.execute(
        statement,
    ).scalar_one_or_none()

    if oauth_state is None:
        raise InvalidOAuthStateError(
            "OAuth state is invalid"
        )

    if oauth_state.used_at is not None:
        raise InvalidOAuthStateError(
            "OAuth state has already been used."
        )

    current_time = datetime.now(timezone.utc)

    if oauth_state.expires_at <= current_time:
        raise InvalidOAuthStateError(
            " OAuth state has expired"
        )

    # Marking it used before continuing with the token exchange 
    oauth_state.used_at = current_time

    db.commit()

    return oauth_state.user_id

