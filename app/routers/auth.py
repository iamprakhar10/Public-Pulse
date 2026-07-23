from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.crud import (
    create_user,
    get_user_by_email,
    get_user_by_phone
)

from app.database.dependencies import get_db
from app.schemas.auth import UserRegister, Token, UserLogin
from app.schemas.user import UserResponse
from app.utils.security import create_access_token, verify_password

router = APIRouter(
    prefix="/auth",
    tags=['Authentication'],
)
# An APIRouter is a container for related API endpoints
# Routers allow us to split these endpoints
# routers/auth.py         → authentication endpoints
# routers/users.py        → user endpoints
# routers/complaints.py   → complaint endpoints
# routers/dashboard.py    → dashboard endpoints
# 
#  into separate files.
@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED
)

def register_user(
    user_data:UserRegister,
    db: Session = Depends(get_db),
) -> UserResponse:
    existing_user = get_user_by_email(db, user_data.email)

    if existing_user is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email is already Registered",
        )
    
    existing_user = get_user_by_phone(db, user_data.phone)
    if existing_user is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Phone number is already registered",
        )
    
    return create_user(db, user_data)
""" data comes from the request body then user_data is created:

JSON request → UserRegister → user_data"""
# Depends tells FastAPI:
# This parameter should be provided by another function.
# FastAPI sees Depends(get_db) and calls get_db() automatically.
# The route does not manually do this:
# db = SessionLocal()


# Session represents a conversation between
#  your Python code and the database.
# You use it to:
# execute queries
# add rows
# update rows
# delete rows
# commit transactions

@router.post('/login',
             response_model=Token,)
def login_user(
    login_data:UserLogin,
    db:Session = Depends(get_db)
) -> Token:
    user = get_user_by_email(db, login_data.email)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    if not verify_password(
        login_data.password,
        user.hashed_password,
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    access_token = create_access_token(
        data={'sub':str(user.id)},
    )

    return Token(
        access_token=access_token,
        token_type='bearer',
        )



"""
app/routers/auth.py defines authentication-related API endpoints.
That endpoint allows a new user to register.

HTTP request arrives
        ↓
router receives it
        ↓
schema validates it
        ↓
CRUD talks to database
        ↓
router returns response
"""