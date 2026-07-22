from pydantic import BaseModel, EmailStr, Field


#This schema validates the data sent when a new user creates an account.
class UserRegister(BaseModel):
    name:str = Field(min_length=2, max_length=100)
    email:EmailStr
    phone:str = Field(min_length=10, max_length=12)
    password:str = Field(min_length=8, max_length=128)


# This validates the credentials sent when an existing user logs in.
# The backend then uses these values to:

# Find the user by email.
# Retrieve the stored hashed_password.
# Compare the submitted password against the hash.
# Generate a JWT if the password is correct.
class UserLogin(BaseModel):
    email: EmailStr
    password: str


# This represents the response returned after successful login.
class Token(BaseModel):
    access_token:str
    token_type:str


# This represents useful information extracted after decoding a JWT
class TokenData(BaseModel):
    user_id:int | None=None