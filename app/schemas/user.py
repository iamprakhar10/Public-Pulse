from pydantic import BaseModel, EmailStr, StringConstraints, Field, ConfigDict
from typing import Annotated


# describing which user fields your API is allowed to return to 
# the frontend.
class UserResponse(BaseModel):
    id: int
    name: str
    email: EmailStr
    phone: str
    is_verified: bool

    model_config = ConfigDict(from_attributes=True)

# Note there is no is_verified as we don't want users to decide it
# Therefore only our Database model has it