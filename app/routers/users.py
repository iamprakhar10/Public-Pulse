from fastapi import APIRouter, Depends

from app.database.dependencies import get_current_user
from app.database.models import User
from app.schemas.user import UserResponse

#Grouping all user-related endpoints under the /user prefix.

router = APIRouter(
    prefix='/users',
    tags=['Users'],
)

@router.get(
    '/me',
    response_model=UserResponse,
)
def get_my_profile(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    We will return the profile of currently authenticated user,

    FastAPI will make sure that the returned response is of schema
    UserResponse, even though we are returning according to User schema
    """

    return current_user

