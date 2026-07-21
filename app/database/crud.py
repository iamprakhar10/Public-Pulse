from sqlalchemy.orm import Session

from app.database.models import User
from app.schemas.user import UserCreate

from sqlalchemy import select


#Create a user using this database Session 
# and this validated UserCreate object. 
# Return a User ORM object.
def create_user(db:Session, user:UserCreate) -> User:
    db_user = User(
        name=user.name,
        email=user.email,
        phone=user.phone
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    return db_user

def get_user_by_id(db:Session, user_id:int) -> User|None:
    statement = select(User).where(User.id == user_id)

    return db.execute(statement).scalar_one_or_none()

# db.execute() returns a Result object

def get_user_by_email(db:Session, user_email:str) -> User|None:
    statement = select(User).where(User.email == user_email)

    return db.execute(statement).scalar_one_or_none()


def get_user_by_phone(db:Session, phone:str) -> User|None:
    statement = select(User).where(User.phone == phone)

    return db.execute(statement).scalar_one_or_none()


def verify_user(db:Session, user:User) -> User:
    user.is_verified = True

    db.commit()
    db.refresh(user)

    return user

def delete_user(db:Session, user:User) -> None:
    db.delete(user)
    db.commit()