"""
Routes for connecting a public pulse user
account to gmail
"""

from fastapi import APIRouter, Depends
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.config import get_google_oauth_config
from app.database.dependencies import (
    get_current_user,
    get_db,
)
from app.database.models import User
from app.services.gmail_oauth import (
    build_google_authorization_url,
)
from app.services.gmail_oauth_state import (
    create_oauth_state,
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

    state = create_oauth_state(
        db=db,
        user_id=current_user.id,
    )

    authorization_url = build_google_authorization_url(
        config=google_config,
        state=state,
    )

    return RedirectResponse(
        url=authorization_url,

        # 302 is the conventional status code for redirecting 
        status_code=302,
    )