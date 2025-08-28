from pydantic import BaseModel, field_validator
from typing import Optional

from app.services.sms.otp_utils import validate_phone_format


class PhoneStartRequest(BaseModel):
    phone: Optional[str] = None
    
    @field_validator('phone')
    @classmethod
    def validate_phone_format_field(cls, v):
        if v and not validate_phone_format(v):
            raise ValueError('Invalid phone number format')
        return v


class PhoneStartResponse(BaseModel):
    message: str = "OTP sent to your phone number"


class PhoneVerifyResponse(BaseModel):
    message: str = "Phone number verified successfully"


class PhoneVerifyCodeRequest(BaseModel):
    phone: str
    code: str
    
    @field_validator('phone')
    @classmethod
    def validate_phone_format_field(cls, v):
        if not validate_phone_format(v):
            raise ValueError('Invalid phone number format')
        return v
    
    @field_validator('code')
    @classmethod
    def validate_code_format(cls, v):
        if not v or len(v) != 6 or not v.isdigit():
            raise ValueError('Code must be 6 digits')
        return v


class PhoneLoginRequest(BaseModel):
    phone: str
    code: str
    
    @field_validator('phone')
    @classmethod
    def validate_phone_format_field(cls, v):
        if not validate_phone_format(v):
            raise ValueError('Invalid phone number format')
        return v
    
    @field_validator('code')
    @classmethod
    def validate_code_format(cls, v):
        if not v or len(v) != 6 or not v.isdigit():
            raise ValueError('Code must be 6 digits')
        return v