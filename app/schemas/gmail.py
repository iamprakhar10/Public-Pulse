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



class GmailStatusResponse(BaseModel):
    """
    Tells the frontend whether the current user has connectd
    their gmail or not

    connected -> bool
    google_email -> EmailStr | None=None
    """

    connected : bool
    google_email : EmailStr | None=None



class GmailDisconnectResponse(BaseModel):
    """
    Response returned after Gmail has been disconnected
    
    message-> str
    """

    message: str