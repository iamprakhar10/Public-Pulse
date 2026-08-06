"""
Central application configuration.

Environment variables are loaded from the project's .env file.

Configuration is validated only when a feature requests it. This prevents
the entire application and unrelated tests from failing merely because
Google OAuth has not been configured.
"""

import os
from dataclasses import dataclass

from dotenv import load_dotenv


load_dotenv()


class ConfigurationError(RuntimeError):
    """
    Raised when required application configuration is missing.
    """


@dataclass(frozen=True)
class GoogleOAuthConfig:
    """
    Configuration required for Google's OAuth authorization-code flow.
    """

    client_id: str
    client_secret: str
    redirect_uri: str


def get_google_oauth_config() -> GoogleOAuthConfig:
    """
    Load and validate Google OAuth settings.

    This function is called only when Gmail OAuth functionality is used.
    Therefore, unrelated routes and tests can continue running even when
    Google OAuth has not yet been configured.
    """

    client_id = os.getenv("GOOGLE_CLIENT_ID")
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
    redirect_uri = os.getenv("GOOGLE_REDIRECT_URI")

    missing_variables = []

    if not client_id:
        missing_variables.append("GOOGLE_CLIENT_ID")

    if not client_secret:
        missing_variables.append("GOOGLE_CLIENT_SECRET")

    if not redirect_uri:
        missing_variables.append("GOOGLE_REDIRECT_URI")

    if missing_variables:
        missing_names = ", ".join(missing_variables)

        raise ConfigurationError(
            f"Missing required Google OAuth configuration: "
            f"{missing_names}"
        )

    return GoogleOAuthConfig(
        client_id=client_id,
        client_secret=client_secret,
        redirect_uri=redirect_uri,
    )


def get_token_encryption_key() -> str:
    """
    Load the key used to encrypt and decrypt stored OAuth tokens.
    """

    encryption_key = os.getenv("TOKEN_ENCRYPTION_KEY")

    if not encryption_key:
        raise ConfigurationError(
            "Missing required configuration: TOKEN_ENCRYPTION_KEY"
        )

    return encryption_key