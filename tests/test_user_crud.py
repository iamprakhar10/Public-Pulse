import random

from app.database.crud import create_user
from app.database.session import SessionLocal
from app.schemas.auth import UserRegister
from app.utils.security import verify_password


def test_create_user() -> None:
    unique_number = random.randint(1_000_000_000, 9_999_999_999)

    user_data = UserRegister(
        name='Test user',
        email=f"test-{unique_number}@example.com",
        phone=str(unique_number),
        password="test_password123",
    )

    with SessionLocal() as db:
        created_user = create_user(db, user_data)

        assert created_user.id is not None
        assert created_user.email == user_data.email
        assert created_user.hashed_password != user_data.password

        assert verify_password(
            user_data.password,
            created_user.hashed_password,
        )