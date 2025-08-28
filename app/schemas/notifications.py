from typing import Optional, Dict
from pydantic import BaseModel, EmailStr


class EmailSendRequest(BaseModel):
    to: EmailStr
    subject: str
    html: str
    tags: Optional[Dict[str, str]] = None


class PushSendRequest(BaseModel):
    token: str
    title: str
    body: str
    data: Optional[Dict[str, str]] = None
