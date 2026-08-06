"""
Google OAuth authorization flow helpers

This module will build Google's authorization url. 
It doesn't perform database operations and doesn't define
FastAPI routes
"""

from google_auth_oauthlib.flow import Flow

from app.config import GoogleOAuthConfig



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

def build_google_oauth_flow(
        config: GoogleOAuthConfig,
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
    )

    flow.redirect_uri = config.redirect_uri

    return flow




def build_google_authorization_url(
        config: GoogleOAuthConfig,
        state: str,
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

    flow = build_google_oauth_flow(
        config=config,
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