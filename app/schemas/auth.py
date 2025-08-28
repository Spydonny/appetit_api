from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime


class RegisterRequest(BaseModel):
    full_name: str
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    dob: Optional[str] = None
    password: str


class UserOut(BaseModel):
    id: int
    full_name: str
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    dob: Optional[str] = None
    role: str
    is_email_verified: bool = False
    is_phone_verified: bool = False
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class LoginRequest(BaseModel):
    email_or_phone: str
    password: str
