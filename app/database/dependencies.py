from collections.abc import Generator

from sqlalchemy.orm import Session

from app.database.session import SessionLocal
from app.database.models import User
from app.utils.security import ALGORITHM, SECRET_KEY, decode_access_token


from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWSError, jwt

from app.database.crud import get_user_by_id


def get_db() -> Generator[Session, None, None]:
#This creates one database session for each API request and closes it afterward.
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()
    

"""
get_db() starts
    ↓
creates db session
    ↓
yield db
    ↓
route uses db
    ↓
route finishes
    ↓
get_db() resumes
    ↓
db.close()


What would happen with return?

Suppose we write:

def get_db():
    db = SessionLocal()
    return db
"""

oauth2_scheme = OAuth2PasswordBearer(tokenUrl='/auth/login')
# OAuth2PasswordBearer only extracts the bearer token 
# from the request


# OAuth2PasswordBearer does not:
# verify the password
# create the JWT
# decode the JWT
# check the JWT signature
# fetch the user from PostgreSQL

def get_current_user(
        token:str = Depends(oauth2_scheme),
        db:Session = Depends(get_db),
) -> User:
    credential_exceptions = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    # Reuse the JWT-decoding logic from security.py.
    payload = decode_access_token(token)

    if payload is None:
        raise credential_exceptions

    # `sub` contains the user ID that we stored during login.
    user_id = payload.get('sub')

    if user_id is None:
        raise credential_exceptions

    try :
        user_id = int(user_id)
    except ValueError:
        raise credential_exceptions

    # Loading the actual user from the database
    user = get_user_by_id(db, user_id)

    if user is None:
        raise credential_exceptions

    return user

"""
When FastAPI sees:
token: str = Depends(oauth2_scheme)
it asks oauth2_scheme to extract the token.

The result passed into token is only this part:
eyJhbGciOiJIUzI1NiIs...
It removes:
Bearer 
from the beginning.
"""