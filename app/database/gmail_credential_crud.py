"""
Database operations for gmail OAuth credentials

"""

from sqlalchemy.orm import Session
from sqlalchemy import select

from app.database.models import GmailCredential


def get_gmail_credential_by_user_id(
        db: Session,
        user_id: int,
) -> GmailCredential | None:
    """
    Retrieve the gmail credential belonging to a public pulse user

    Returns None if user has not connected Gmail
    """
    statement = (
        select(GmailCredential)
        .where(GmailCredential.user_id == user_id)
    )

    return db.execute(
        statement
    ).scalar_one_or_none()


def get_gmail_credential_by_google_account_id(
        db:Session,
        google_account_id: str,
) -> GmailCredential | None:
    """
    Retrieving a Gmail credential using Google's stable account ID.

    This helps detect whether the same Google account has already been
    connected to another Public Pulse user.
    """

    statement = (
        select(GmailCredential)
        .where(
            GmailCredential.google_account_id
            == google_account_id
        )
    )

    return db.execute(
        statement
    ).scalar_one_or_none()


def save_gmail_credential(
        db: Session,
        user_id: int,
        google_account_id: str,
        google_email: str,
        encrypted_refresh_token: str,
        scopes: str,
) -> GmailCredential:
    """
    Create or update a user's gmail credential

    When user reconnects Gmail, the existing row gets updated instead of 
    creating a new row
    """
    credential = get_gmail_credential_by_user_id(
        db=db,
        user_id=user_id,
    )

    if credential is None:
        credential = GmailCredential(
            user_id=user_id,
            google_account_id=google_account_id,
            google_email=google_email,
            encrypted_refresh_token=encrypted_refresh_token,
            scopes=scopes,
        )

        db.add(credential)

    else:
        credential.google_account_id = google_account_id
        credential.google_email = google_email
        credential.encrypted_refresh_token = (
            encrypted_refresh_token
        )
        credential.scopes=scopes

    db.commit()
    db.refresh(credential)

    return credential




def delete_gmail_credential(
        db:Session,
        user_id:int,
) -> bool:
    """
    Deletes a user's stored Gmail credential

    Return True if credential existed and then deleted
    """

    credential = get_gmail_credential_by_user_id(
        db=db,
        user_id=user_id,
    )

    if credential is None:
        return False

    db.delete(credential)
    db.commit()

    return True