"""
Google OAuth authorization flow helpers

This module will build Google's authorization url. 
It doesn't perform database operations and doesn't define
FastAPI routes
"""

from sqlalchemy.orm import Session
from google_auth_oauthlib.flow import Flow

from app.config import GoogleOAuthConfig
from dataclasses import dataclass

from google.auth.transport.requests import (
    Request as GoogleRequest
)
from google.oauth2 import id_token

from app.database.gmail_credential_crud import (
    get_gmail_credential_by_google_account_id,
    get_gmail_credential_by_user_id,
    save_gmail_credential,
)
from app.services.gmail_oauth_state import consume_oauth_state
from app.utils.token_encryption import encrypt_token














GMAIL_SEND_SCOPE = (
    "https://www.googleapis.com/auth/gmail.send"
)

GOOGLE_IDENTITY_SCOPES = [
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
]

GOOGLE_OAUTH_SCOPES = [
    GMAIL_SEND_SCOPE,
    *GOOGLE_IDENTITY_SCOPES,
]












class GmailOAuthError(RuntimeError):
    """
    Base exception for errors while completing Gmail OAuth.
    """


class MissingGoogleIdentityError(GmailOAuthError):
    """
    Raised when Google does not return a usable verified identity.
    """


class MissingRefreshTokenError(GmailOAuthError):
    """
    Raised when a first-time Gmail connection has no refresh token.
    """


class GoogleAccountAlreadyConnectedError(GmailOAuthError):
    """
    Raised when one Google account already belongs to another
    Public Pulse user.
    """


class MissingRequiredGoogleScopeError(GmailOAuthError):
    """
    Raised when google doesn't grant a scope required by Publis
    pulse user
    """


@dataclass(frozen=True)
class GoogleAuthorizationResult:
    """
    Information obtained after exchanging Google's authorization code
    
    <google_account_id,google_email,refresh_token,scopes>
    """

    google_account_id: str
    google_email: str
    refresh_token: str | None
    scopes: str




@dataclass(frozen=True)
class GmailConnectionResult:
    """
    Safe result returned after gmail has been connected

    sensitive tokens are on purpose excluded
    """
    user_id: int
    google_account_id: str
    google_email: str
    scopes: str




def exchange_google_authorization_code(
        config: GoogleOAuthConfig,
        authorization_code: str,
        code_verifier:str,
) -> GoogleAuthorizationResult:
    """
    Exchange Google's one time authorization code for credentials

    The returned google ID is verified before it's subject and email
    addresss are trusted
    """

    if not authorization_code:
        raise GmailOAuthError(
            "Google authorization code is required."
        )

    flow = build_google_oauth_flow(
        config=config,
        code_verifier=code_verifier,
    )

    # Makes a backend->Google POST request to google's token
    # endpoint
    flow.fetch_token(
        code=authorization_code,
    )

    credentials = flow.credentials

    if not credentials.id_token:
        raise MissingGoogleIdentityError(
            " Google did not return an identity token."
        )

    try:
        identity = id_token.verify_oauth2_token(
            # Tells Public Pulse the identity of the Google user who approved access
            credentials.id_token, 

            GoogleRequest(),
            config.client_id,
        )

    except ValueError as exc:
        raise MissingGoogleIdentityError(
            "Google identity token could not be verified."
        ) from exc

    google_account_id = identity.get('sub')
    google_email = identity.get('email')
    email_verified = identity.get('email_verified')

    if not google_account_id:
        raise MissingGoogleIdentityError(
            "Google account ID is missing."
        )

    if not google_email:
        raise MissingGoogleIdentityError(
            "Google email address is missing."
        )

    if email_verified is not True:
        raise MissingGoogleIdentityError(
            "Google email address is not verified."
        )

    granted_scopes = credentials.scopes or GOOGLE_OAUTH_SCOPES

    return GoogleAuthorizationResult(
        google_account_id=str(google_account_id),
        google_email=str(google_email),
        refresh_token=credentials.refresh_token,
        scopes=" ".join(granted_scopes),
    )
"""
ID token
────────
Question:
“Who is this Google user?”

Gives us:
sub, email, email_verified

Used for:
identifying the connected Google account

Stored permanently?
Usually not necessary
===========================================
Refresh token
─────────────
Question:
“May Public Pulse continue accessing Gmail later?”

Gives us:
ability to obtain new access tokens

Used for:
future Gmail API access

Stored permanently?
Yes, encrypted
"""



















def complete_gmail_oauth_connection(
        db: Session,
        state: str,
        authorization_code: str,
        config: GoogleOAuthConfig,
        encryption_key: str,
) -> GmailConnectionResult:
    """
    Complete one Google OAuth callback

    1. validates the one time OAuth state
    2. determines which public pulse user started the flow
    3. exchanges Gogle's code for credentials
    4. Verifies the connected Google identity
    5. Encrypts and store the refresh tokens
    """

    user_id, code_verifier = consume_oauth_state(
        db=db,
        state=state,
    )

    google_result = exchange_google_authorization_code(
        config=config,
        authorization_code=authorization_code,
        code_verifier=code_verifier,
    )


    credentials_for_google_account = (
        get_gmail_credential_by_google_account_id(
            db=db,
            google_account_id=google_result.google_account_id,
        )
    )

    if (
        credentials_for_google_account is not None
        and credentials_for_google_account.user_id != user_id
    ):
        raise GoogleAccountAlreadyConnectedError(
            "This google account is already connected to another"
            "Public pulse user"
        )

    existing_user_credential = (
        get_gmail_credential_by_user_id(
            db=db,
            user_id=user_id,
        )
    )

    if google_result.refresh_token:
        encrypted_refresh_token = encrypt_token(
            token=google_result.refresh_token,
            encryption_key=encryption_key,
        )

    elif existing_user_credential is not None:
        # Google may omit a refresh token during reconnection.
        # Preserve the user's existing encrypted token.
        encrypted_refresh_token = (
            existing_user_credential.encrypted_refresh_token
        )

    else:
        raise MissingRefreshTokenError(
            "Google did not return a refresh token. "
            "Please start the Gmail connection again."
        )
    
    credential = save_gmail_credential(
        db=db,
        user_id=user_id,
        google_account_id=(
            google_result.google_account_id
        ),
        google_email=google_result.google_email,
        encrypted_refresh_token=encrypted_refresh_token,
        scopes=google_result.scopes,
    )

    return GmailConnectionResult(
        user_id=credential.user_id,
        google_account_id=credential.google_account_id,
        google_email=credential.google_email,
        scopes=credential.scopes,
    )












def build_google_oauth_flow(
        config: GoogleOAuthConfig,
        code_verifier:str,
) -> Flow:
    """
    Building gogle's OAuth Flow bject from public pulse 
    configuration

    The flow object knows:
    - Public pulse'sgogle client id
    - Public pulse's google client secret
    - The registered callback url
    - The permission Public pulse is requesting 
    """

    client_config = {
        "web": {
            "client_id": config.client_id,
            "client_secret": config.client_secret,
            "auth_uri": (
                "https://accounts.google.com/o/oauth2/auth"
            ),
            "token_uri": (
                "https://oauth2.googleapis.com/token"
            ),
            "redirect_uris": [
                config.redirect_uri,
            ],
        }
    }

    flow = Flow.from_client_config(
        client_config=client_config,
        scopes=GOOGLE_OAUTH_SCOPES,
        code_verifier=code_verifier,
    )

    flow.redirect_uri = config.redirect_uri

    return flow




def build_google_authorization_url(
        config: GoogleOAuthConfig,
        state: str,
        code_verifier: str,
) -> str:
    """
    Building the google's consent-page url for one OAuth attempt

    The caller creates and stores the state before calling
    this function
    """

    if not state:
        raise ValueError(
            "OAuth state is required."
        )

    if not code_verifier:
        raise ValueError(
            "PKCE code verifier is required."
        )

    flow = build_google_oauth_flow(
        config=config,
        code_verifier=code_verifier,
    )

    authorization_url, returned_state = (
        flow.authorization_url(
            access_type='offline',

            # Ask google to display consent during development
            # This will help google return a refresh token
            # when connecting 
            prompt='consent',

            # Include previously granted permissions where
            # applicable 
            include_granted_scopes='true',

            state=state,
        )
    )

    # The google library should preserve our supplied state
    if returned_state != state:
        raise RuntimeError(
            "Google OAuth flow returned an unexpected state."
        ) 

    return authorization_url

















def validate_required_google_scopes(
        granted_scopes: list[str] | tuple[str, ...] | set[str],
) -> None:
    """
    Ensuring Google granted every permission required by Public Pulse.

    Public Pulse needs gmail.send because approved complaints are
    sent through the user's Gmail account.
    """

    granted_scope_set = set(granted_scopes)

    required_scopes = {
        "https://www.googleapis.com/auth/gmail.send",
    }

    missing_scopes = (
        required_scopes-granted_scope_set
    )

    if missing_scopes:
        raise MissingRequiredGoogleScopeError(
            "Gmail sending permission was not granted. "
            "Please connect Gmail again and allow email sending."
        )