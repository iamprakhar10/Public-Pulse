"""
Schemas returned by Gmail connection endpoints.
"""

from pydantic import BaseModel, EmailStr

class GmailConnectionResponse(BaseModel):
    """
    Public response after successfully connecting gmail

    No google access token or refresh token is exposed

    """

    message: str
    google_email: EmailStr
