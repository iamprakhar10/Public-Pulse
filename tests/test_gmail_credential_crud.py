"""
Tests for Gmail credential database operations.
"""
import pytest
from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.database.models import User
from app.database.session import SessionLocal
from app.database.gmail_credential_crud import (
    delete_gmail_credential,
    get_gmail_credential_by_google_account_id,
    get_gmail_credential_by_user_id,
    save_gmail_credential,
)
from app.database.models import User
from app.utils.security import hash_password

TEST_USER_EMAILS = [
    "gmail-create@example.com",
    "gmail-get@example.com",
    "gmail-missing@example.com",
    "gmail-update@example.com",
    "gmail-google-id@example.com",
    "gmail-delete@example.com",
    "gmail-delete-missing@example.com",
]


def delete_gmail_test_users(
        db: Session,
) -> None:
    """
    Remove only the temporary users created by this test module.

    GmailCredential rows are deleted automatically because the
    foreign key uses ON DELETE CASCADE.
    """

    statement = (
        delete(User)
        .where(User.email.in_(TEST_USER_EMAILS))
    )

    db.execute(statement)
    db.commit()


@pytest.fixture
def db_session():
    """
    Provide a real SQLAlchemy session to each CRUD test.

    Cleanup runs before and after every test so a failed previous test
    cannot leave duplicate users behind.
    """

    db = SessionLocal()

    try:
        delete_gmail_test_users(db)
        yield db

    finally:
        # Roll back any currently failed transaction before cleanup.
        db.rollback()

        delete_gmail_test_users(db)
        db.close()
def create_test_user(
        db_session,
        email: str,
        phone: str,
) -> User:
    """
    Create a Public Pulse user required by Gmail credential tests.
    """

    user = User(
        name="Gmail Test User",
        email=email,
        phone=phone,
        hashed_password=hash_password(
            "test-password",
        ),
    )

    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    return user


def test_save_gmail_credential_creates_new_credential(
        db_session,
) -> None:
    """
    A user without Gmail connected should receive a new credential row.
    """

    user = create_test_user(
        db_session=db_session,
        email="gmail-create@example.com",
        phone="9000000001",
    )

    credential = save_gmail_credential(
        db=db_session,
        user_id=user.id,
        google_account_id="google-account-123",
        google_email="connected@gmail.com",
        encrypted_refresh_token="encrypted-token-one",
        scopes="https://www.googleapis.com/auth/gmail.send",
    )

    assert credential.id is not None
    assert credential.user_id == user.id
    assert credential.google_account_id == "google-account-123"
    assert credential.google_email == "connected@gmail.com"
    assert (
        credential.encrypted_refresh_token
        == "encrypted-token-one"
    )


def test_get_gmail_credential_by_user_id(
        db_session,
) -> None:
    """
    A stored Gmail credential should be retrievable using user ID.
    """

    user = create_test_user(
        db_session=db_session,
        email="gmail-get@example.com",
        phone="9000000002",
    )

    save_gmail_credential(
        db=db_session,
        user_id=user.id,
        google_account_id="google-account-456",
        google_email="retrieve@gmail.com",
        encrypted_refresh_token="encrypted-token-two",
        scopes="https://www.googleapis.com/auth/gmail.send",
    )

    credential = get_gmail_credential_by_user_id(
        db=db_session,
        user_id=user.id,
    )

    assert credential is not None
    assert credential.google_email == "retrieve@gmail.com"


def test_get_gmail_credential_returns_none_when_missing(
        db_session,
) -> None:
    """
    Users without a Gmail connection should return None.
    """

    user = create_test_user(
        db_session=db_session,
        email="gmail-missing@example.com",
        phone="9000000003",
    )

    credential = get_gmail_credential_by_user_id(
        db=db_session,
        user_id=user.id,
    )

    assert credential is None


def test_save_gmail_credential_updates_existing_row(
        db_session,
) -> None:
    """
    Reconnecting Gmail should update the existing row rather than
    creating another one.
    """

    user = create_test_user(
        db_session=db_session,
        email="gmail-update@example.com",
        phone="9000000004",
    )

    original_credential = save_gmail_credential(
        db=db_session,
        user_id=user.id,
        google_account_id="google-account-old",
        google_email="old@gmail.com",
        encrypted_refresh_token="old-encrypted-token",
        scopes="old-scope",
    )

    updated_credential = save_gmail_credential(
        db=db_session,
        user_id=user.id,
        google_account_id="google-account-new",
        google_email="new@gmail.com",
        encrypted_refresh_token="new-encrypted-token",
        scopes="new-scope",
    )

    assert updated_credential.id == original_credential.id
    assert (
        updated_credential.google_account_id
        == "google-account-new"
    )
    assert updated_credential.google_email == "new@gmail.com"
    assert (
        updated_credential.encrypted_refresh_token
        == "new-encrypted-token"
    )
    assert updated_credential.scopes == "new-scope"


def test_get_gmail_credential_by_google_account_id(
        db_session,
) -> None:
    """
    Google's stable account ID should locate the credential.
    """

    user = create_test_user(
        db_session=db_session,
        email="gmail-google-id@example.com",
        phone="9000000005",
    )

    save_gmail_credential(
        db=db_session,
        user_id=user.id,
        google_account_id="google-account-789",
        google_email="google-id@gmail.com",
        encrypted_refresh_token="encrypted-token-three",
        scopes="https://www.googleapis.com/auth/gmail.send",
    )

    credential = get_gmail_credential_by_google_account_id(
        db=db_session,
        google_account_id="google-account-789",
    )

    assert credential is not None
    assert credential.user_id == user.id


def test_delete_gmail_credential(
        db_session,
) -> None:
    """
    Deleting a Gmail credential should disconnect the user.
    """

    user = create_test_user(
        db_session=db_session,
        email="gmail-delete@example.com",
        phone="9000000006",
    )

    save_gmail_credential(
        db=db_session,
        user_id=user.id,
        google_account_id="google-account-delete",
        google_email="delete@gmail.com",
        encrypted_refresh_token="encrypted-token-delete",
        scopes="https://www.googleapis.com/auth/gmail.send",
    )

    was_deleted = delete_gmail_credential(
        db=db_session,
        user_id=user.id,
    )

    credential = get_gmail_credential_by_user_id(
        db=db_session,
        user_id=user.id,
    )

    assert was_deleted is True
    assert credential is None


def test_delete_missing_gmail_credential_returns_false(
        db_session,
) -> None:
    """
    Deleting a nonexistent connection should not raise an error.
    """

    user = create_test_user(
        db_session=db_session,
        email="gmail-delete-missing@example.com",
        phone="9000000007",
    )

    was_deleted = delete_gmail_credential(
        db=db_session,
        user_id=user.id,
    )

    assert was_deleted is False