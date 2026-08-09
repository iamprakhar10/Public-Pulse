"""
Global pytest configuration.

Tests must never run against the development Public Pulse database.

Before the application database module is imported, this file changes
DATABASE_URL so all SQLAlchemy sessions created during pytest use the
separate publicpulse_test database.
"""

import os

from dotenv import load_dotenv


# Load values from .env.
load_dotenv()


TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL"
)


if not TEST_DATABASE_URL:
    raise RuntimeError(
        "TEST_DATABASE_URL is not configured. "
        "Tests must use a separate test database."
    )


# Safety check:
# Never allow pytest to accidentally use the normal development DB.
if "publicpulse_test" not in TEST_DATABASE_URL:
    raise RuntimeError(
        "TEST_DATABASE_URL must point to publicpulse_test."
    )


# IMPORTANT:
#
# app/database/db.py reads DATABASE_URL when it is imported.
#
# Therefore we replace DATABASE_URL here BEFORE pytest imports
# the application modules.
os.environ["DATABASE_URL"] = TEST_DATABASE_URL