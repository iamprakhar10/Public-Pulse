from sqlalchemy.orm import sessionmaker

from app.database.db import engine

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
)
