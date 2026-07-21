from sqlalchemy import Boolean, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from database.base import Base
"""print(type(mapped_column))
print("---")
print(type(Mapped))
print(Mapped)"""

class User(Base):
    __tablename__ = 'users'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    phone: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
