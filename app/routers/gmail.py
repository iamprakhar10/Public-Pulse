"""
Routes for connecting a public pulse user
account to gmail
"""

from fastapi import (
    APIRouter, 
    Depends,
    HTTPException,
    Query,
    status,
)

from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.config import (
    get_google_oauth_config,
    get_token_encryption_key,
)
from app.database.dependencies import (
    get_current_user,
    get_db,
)
from app.database.models import User
from app.services.gmail_oauth import (
    build_google_authorization_url,
    GmailOAuthError,
    GoogleAccountAlreadyConnectedError,
    complete_gmail_oauth_connection,
    MissingRequiredGoogleScopeError
)
from app.services.gmail_oauth_state import (
    create_oauth_state,
    InvalidOAuthStateError,
)

from app.database.gmail_credential_crud import (
    delete_gmail_credential,
    get_gmail_credential_by_user_id,
)

from app.schemas.gmail import (
    GmailConnectionResponse,
    GmailDisconnectResponse,
    GmailStatusResponse,
)
from app.services.google_token_revocation import (
    GoogleTokenRevocationError,
    revoke_google_token,
)
from app.utils.token_encryption import (
    TokenEncryptionError,
    decrypt_token
)
















router = APIRouter(
    prefix="/gmail",
    tags=['Gmail'],
)








@router.get(
    '/connect',
)
def connect_gmail(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> RedirectResponse:
    """
    Starts google OAuth for the authenticated public pulse user

    - identifies user
    - creates a one time OAuth state
    - build's google's consent url
    - redirects te browser to google
    """

    google_config = get_google_oauth_config()

    state, code_verifier = create_oauth_state(
        db=db,
        user_id=current_user.id,
    )

    authorization_url = build_google_authorization_url(
        config=google_config,
        state=state,
        code_verifier=code_verifier,
    )

    return RedirectResponse(
        url=authorization_url,

        # 302 is the conventional status code for redirecting 
        status_code=302,
    )




















@router.get(
    "/callback",
)
def gmail_callback(
    code: str | None = Query(default=None),
    state: str | None = Query(default=None),
    error: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> RedirectResponse:
    """
    Complete Google's OAuth callback

    This route is not protected using get_current_user because Google's 
    browser redirect doesn't normally include the public pulse JWT

    tHE one time OAuth state identifies the public pulse user here instead
    """
    if error is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Google authorization was denied or failed: "
                f"{error}"
            ),
        )

    if not code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Google authorization code is missing.",
        )

    if not state:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="OAuth state is missing.",
        )

    try:
        complete_gmail_oauth_connection(
            db=db,
            state=state,
            authorization_code=code,
            config=get_google_oauth_config(),
            encryption_key=get_token_encryption_key(),
        )

    except InvalidOAuthStateError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    except GoogleAccountAlreadyConnectedError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    except MissingRequiredGoogleScopeError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    except GmailOAuthError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    # return GmailConnectionResponse(
    #     message="Gmail connected successfully.",
    #     google_email=connection.google_email,
    # )
    return RedirectResponse(
        url="http://localhost:8501",
        status_code=status.HTTP_302_FOUND,
    )





















@router.get(
    "/status",
    response_model=GmailStatusResponse,
)
def get_gmail_connection_status(
    db: Session = Depends(get_db),
    current_user : User = Depends(get_current_user),
) -> GmailStatusResponse:
    """
    Returns the gmail connection status of a authenticated 
    public pulse user

    This doesn't contact google

    Just checks whether public pulse has a GmailCredential
    row for this current user or not
    """

    gmail_credential = get_gmail_credential_by_user_id(
        db=db,
        user_id=current_user.id,
    )

    if gmail_credential is None:
        return GmailStatusResponse(
            connected=False,
        )
    
    return GmailStatusResponse(
        connected=True,
        google_email=gmail_credential.google_email,
    )






















@router.delete(
    "/disconnect",
    response_model=GmailDisconnectResponse,
)
def disconnect_gmail(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> GmailDisconnectResponse:
    """
    This disconnects the gmail of an authenticated public pulse
    user

    The stored refresh token is:
    -loaded from PostgreSQL
    -Decrypted
    -revoked wiht google
    -deleted from public pul;se

    local credentials will only be deleted if google can 
    successfully revoke the token

    If this succeeds, public pulse user won't be able to send 
    gmail messages for this user unless they connect their
    gmail again
    """
    gmail_credential = get_gmail_credential_by_user_id(
        db=db,
        user_id=current_user.id,
    )

    if gmail_credential is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Gmail is not connected.",
        )

    try:
        refresh_token = decrypt_token(
            encrypted_token=gmail_credential.encrypted_refresh_token,
            encryption_key=get_token_encryption_key(),
        )

        revoke_google_token(
            token=refresh_token,
        )

    except TokenEncryptionError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=(
                "Stored gmail credential could not be read."
            ),
        ) from exc

    except GoogleTokenRevocationError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail= str(exc),
        ) from exc


    delete_gmail_credential(
        db=db,
        user_id=current_user.id,
    )
    return GmailDisconnectResponse(
        message="Gmail disconnected successfully."
    )



"""
Google’s official revocation endpoint accepts either an access
token or refresh token
via POST https://oauth2.googleapis.com/revoke. 
Since we persist the refresh token, that’s what we should 
revoke. Google also recommends revoking tokens once they are
no longer needed and deleting them from our system
"""