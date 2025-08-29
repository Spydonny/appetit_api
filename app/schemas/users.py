from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, EmailStr, validator


class SavedAddressCreate(BaseModel):
    address_text: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    label: Optional[str] = None
    is_default: Optional[bool] = False


class SavedAddressUpdate(BaseModel):
    address_text: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    label: Optional[str] = None
    is_default: Optional[bool] = None


class SavedAddressOut(BaseModel):
    id: int
    address_text: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    label: Optional[str] = None
    is_default: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    dob: Optional[str] = None
    address: Optional[str] = None


class UserMeOut(BaseModel):
    id: int
    full_name: str
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    role: str
    dob: Optional[str] = None
    address: Optional[str] = None
    is_email_verified: bool
    is_phone_verified: bool
    saved_addresses: List[SavedAddressOut] = []

    class Config:
        from_attributes = True


# Test-compatible schema that matches test expectations
class AddressCreate(BaseModel):
    """Test-compatible address creation schema"""
    address: str  # This maps to address_text
    city: Optional[str] = None  
    is_default: Optional[bool] = False
    
    # Optional fields for compatibility
    address_text: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    label: Optional[str] = None


# User Management Schemas for Admin/Manager CRUD operations

class UserCreate(BaseModel):
    """Schema for creating new users (managers/couriers)"""
    full_name: str
    email: EmailStr
    phone: Optional[str] = None
    password: str
    role: str
    dob: Optional[str] = None
    
    @validator('role')
    def validate_role(cls, v):
        valid_roles = ["manager", "courier"]
        if v not in valid_roles:
            raise ValueError(f"Role must be one of: {', '.join(valid_roles)}")
        return v
    
    @validator('password')
    def validate_password(cls, v):
        if len(v) < 6:
            raise ValueError("Password must be at least 6 characters long")
        return v


class UserUpdateAdmin(BaseModel):
    """Schema for admin updates to user profiles"""
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    role: Optional[str] = None
    dob: Optional[str] = None
    is_email_verified: Optional[bool] = None
    is_phone_verified: Optional[bool] = None
    
    @validator('role')
    def validate_role(cls, v):
        if v is not None:
            valid_roles = ["user", "courier", "manager", "admin"]
            if v not in valid_roles:
                raise ValueError(f"Role must be one of: {', '.join(valid_roles)}")
        return v


class UserOut(BaseModel):
    """Schema for user output in admin/manager views"""
    id: int
    full_name: str
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    role: str
    is_email_verified: bool
    is_phone_verified: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class CourierCreate(BaseModel):
    """Schema for managers creating courier users"""
    full_name: str
    email: EmailStr
    phone: Optional[str] = None
    password: str
    dob: Optional[str] = None
    
    @validator('password')
    def validate_password(cls, v):
        if len(v) < 6:
            raise ValueError("Password must be at least 6 characters long")
        return v


class CourierUpdate(BaseModel):
    """Schema for managers updating courier profiles"""
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    dob: Optional[str] = None
    is_email_verified: Optional[bool] = None
    is_phone_verified: Optional[bool] = None
