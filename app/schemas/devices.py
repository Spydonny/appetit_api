from pydantic import BaseModel
from typing import Optional


class DeviceRegisterRequest(BaseModel):
    fcm_token: str
    platform: str  # android|ios|web


class DeviceOut(BaseModel):
    id: int
    platform: str
    fcm_token: str

    class Config:
        from_attributes = True
