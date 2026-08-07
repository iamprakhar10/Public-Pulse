"""
Real Gmail implementation of the EmailSender interface

This module converts the encrypted Gmail credential stored 
by public pulse into google credentials and uses gmail API
to send an email
"""

import base64
from email.message import EmailMessage

from google.auth.exceptions import RefreshError
from google.auth.transport.requests import Request as GoogleRequest
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from sqlalchemy.orm import Session

from app.config import (
    GoogleOAuthConfig,
    get_token_encryption_key,
    get_google_oauth_config,
)
from app.database.gmail_credential_crud import (
    get_gmail_credential_by_user_id,
)
from app.utils.token_encryption import decrypt_token


GOOGLE_TOKEN_URI = "https://oauth2.googleapis.com/token"








class GmailConnectionRequiredError(RuntimeError):
    """
    Raised when the public pulse user has not connected his/her
    gmail
    """


class GmailSendError(RuntimeError):
    """
    This will be raised when gmail can't send the email
    """



class GmailEmailSender:
    """
    Send email through user's connected Gmail account

    This calss will follow the same send_email() interface as
    ConsoleEmailSender

    This class recieves an already decrypted Google refresh token
    It will use the refresh token to obtain a temporary access token

    and then calls the gmail API
    """

    def __init__(
            self,
            *,
            refresh_token: str,
            sender_email: str,
            scopes: list[str],
            config: GoogleOAuthConfig,
    ) -> None:
        """
        Stores everything needed to authenticate with google

        we don't store the access tokens as they are short lived. 
        Refresh token can generate access token whenever an email needs to be 
        sent
        """

        self.refresh_token = refresh_token
        self.sender_email = sender_email
        self.scopes = scopes
        self.config = config

    def _build_credentials(self) -> Credentials:
        """
        Build Google credentials from the stored refresh token

        token = None is intentional

        We donot currently have an access token. Google will issue one 
        when credentials.refresh() is called
        """

        return Credentials(
            token=None,
            refresh_token=self.refresh_token,
            token_uri=GOOGLE_TOKEN_URI,
            client_id=self.config.client_id,
            client_secret=self.config.client_secret,
            scopes=self.scopes,
        )

    def send_email(
            self,
            *,
            recipient: str,
            subject: str,
            body: str,
    ) -> None:
        """
        Sends the email using gmail API

        process:
        stored refresh token
        obtain access token
        build GmailAPI client
        create email message
        Gmail users.messages.send()
        """

        credentials = self._build_credentials()

        try:
            # Exchanging the refresh token for a short lived
            # google access token 
            credentials.refresh(
                GoogleRequest()
            )

            # Create the gmail api client
            gmail_service = build(
                'gmail',
                'v1',
                credentials=credentials,
                cache_discovery=False,
            )

            # Constructing a normal RFC email message
            message = EmailMessage()

            message['To'] = recipient
            message['From'] = self.sender_email
            message['Subject'] = subject

            message.set_content(body)

            # Gmail API expects the complete email encoded using
            # URL-safe base64.
            encoded_message = base64.urlsafe_b64encode(
                message.as_bytes()
            ).decode("utf-8")

            # Sending fro the gmail account represented by the
            # google credentials 
            gmail_service.users().messages().send(
                userId="me",
                body={
                    'raw': encoded_message,
                }
            ).execute()

        except (RefreshError, HttpError) as exc:
            raise GmailSendError(
                "Gmail could not send the email"
            ) from exc




















def get_gmail_email_sender_for_user(
        *,
        db: Session,
        user_id: int,
) -> GmailEmailSender:
    """
    Building a GmailEmailSender for one Pulic pulse user

    This is where the database credentia is loaded and the 
    stored refresh token is decrypted
    """

    gmail_credential = get_gmail_credential_by_user_id(
        db=db,
        user_id=user_id
    )

    if gmail_credential is None:
        raise GmailConnectionRequiredError(
            "Connect Gmail before sending a complaint."
        )

    encryption_key = get_token_encryption_key()

    refresh_token = decrypt_token(
        encrypted_token=gmail_credential.encrypted_refresh_token,
        encryption_key=encryption_key,
    )

    google_config = get_google_oauth_config()

    scopes = gmail_credential.scopes.split()

    return GmailEmailSender(
        refresh_token=refresh_token,
        sender_email=gmail_credential.google_email,
        scopes=scopes,
        config=google_config,
    )
