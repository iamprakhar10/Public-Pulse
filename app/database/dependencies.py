from collections.abc import Generator

from sqlalchemy.orm import Session

from app.database.session import SessionLocal


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