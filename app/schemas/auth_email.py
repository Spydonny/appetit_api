from pydantic import BaseModel, EmailStr
from typing import Optional


class EmailStartRequest(BaseModel):
    email: Optional[EmailStr] = None


class EmailStartResponse(BaseModel):
    status: str = "ok"


class EmailVerifyCodeRequest(BaseModel):
    email: EmailStr
    code: str


class EmailVerifyResponse(BaseModel):
    status: str = "verified"
