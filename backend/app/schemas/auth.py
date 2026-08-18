import re
from pydantic import BaseModel, Field, field_validator
KENYAN_PHONE=re.compile(r"^\+254[17]\d{8}$")
class RegisterRequest(BaseModel):
    full_name:str=Field(min_length=2,max_length=100)
    phone_number:str
    password:str=Field(min_length=12,max_length=128)
    referral_code:str|None=Field(default=None,max_length=24)
    @field_validator("phone_number")
    @classmethod
    def phone(cls,v):
        if not KENYAN_PHONE.fullmatch(v): raise ValueError("Use +254XXXXXXXXX")
        return v
class LoginRequest(BaseModel):
    phone_number:str
    password:str
class UserResponse(BaseModel):
    id:str
    full_name:str
    phone_number:str
    referral_code:str
