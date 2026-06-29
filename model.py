from pydantic import BaseModel, EmailStr,field_validator

# Registration Model
class User(BaseModel):
    name: str
    email: EmailStr
    phone: int
    password: str
    confirm_password: str

    @field_validator("email")
    def check_gmail(cls, v):
        if not v.endswith("@gmail.com"):
            raise ValueError("Email must end with @gmail.com")
        return v
    

# Registration Model
class LoginUser(BaseModel):
    email: EmailStr
    password: str
