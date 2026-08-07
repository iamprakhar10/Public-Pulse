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
)
from app.services.gmail_oauth_state import (
    create_oauth_state,
    InvalidOAuthStateError,
)
from app.schemas.gmail import GmailConnectionResponse


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
    response_model=GmailConnectionResponse,
)
def gmail_callback(
    code: str | None = Query(default=None),
    state: str | None = Query(default=None),
    error: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> GmailConnectionResponse:
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
        connection = complete_gmail_oauth_connection(
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

    except GmailOAuthError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    return GmailConnectionResponse(
        message="Gmail connected successfully.",
        google_email=connection.google_email,
    )