from pydantic import BaseModel, EmailStr, StringConstraints
from typing import Annotated

PhoneNumber = Annotated[
    str,
    StringConstraints(
        pattern=r"^\d{10}$"
    ),
]

class UserCreate(BaseModel): # Creating Frontend schema
    name: str
    email: EmailStr
    phone: PhoneNumber

# Note there is no is_verified as we don't want users to decide it
# Therefore only our Database model has it