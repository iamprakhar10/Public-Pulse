import os

from typing import Any
from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt
from pwdlib import PasswordHash

from dotenv import load_dotenv
load_dotenv()


# Password Hashing configuration
password_hash= PasswordHash.recommended()

# JWT configuration
SECRET_KEY= os.getenv("SECRET_KEY")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30


if not SECRET_KEY:
    raise RuntimeError(
    )

def hash_password(password:str)->str:
    """
    Convert a plain-text password into a secure password hash.

    The plain password must never be stored in the database. lol
    """
    return password_hash.hash(password)


def verify_password(plain_password:str,
                    hashed_password:str,) -> bool:
    """
    Check whether a plain-text password matches a stored password hash.
    """
    return password_hash.verify(
        plain_password,
        hashed_password
    )

def create_access_token(
        data:dict[str,Any],
        expires_delta: timedelta | None=None,
) -> str:
    """
    Create and return a signed JWT access token.

    Example data:
        {'sub':"12"}

    Here, 'sub' represents the authenticated user's ID.
    """
    payload = data.copy()

    if expires_delta is not None:
        expiration_time = datetime.now(timezone.utc) + expires_delta
    else:
        expiration_time = datetime.now(timezone.utc) + timedelta(
            minutes=ACCESS_TOKEN_EXPIRE_MINUTES
        )

    payload["exp"] = expiration_time

    encoded_token = jwt.encode(
        payload,
        SECRET_KEY,
        algorithm=ALGORITHM
    )
    return encoded_token

def decode_access_token(token: str) -> dict[str, Any]:
    """
    Decode and validate a JWT access token.

    Raises JWTError when:
    - The signature is invalid
    - The token has expired
    - The token is malformed
    """

    payload = jwt.decode(
        token,
        SECRET_KEY,
        algorithms=[ALGORITHM],
    )
    return payload


"""
Instead of asking for the password every time after login, for example 
complaint, check status etc. After login the server says:
"I verified you" 
and gives alice a token : eyJhbGciOiJIUzI1NiIsInR...

Now every request becomes
Authorization:
Bearer eyJhbGc...

Now password is not required

Then what stops me from changing
{
"sub":"999"
}
to become another user?

This is where SECRET_KEY comes in

It's like our stamp
JWT + Secret Key ----> Signed JWT
"""