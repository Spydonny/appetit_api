from typing import Optional, Dict
from pydantic import BaseModel, Field
from datetime import datetime


class CategoryCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    name_translations: Optional[Dict[str, str]] = None
    sort: int = Field(default=0, ge=0)


class CategoryUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    name_translations: Optional[Dict[str, str]] = None
    sort: Optional[int] = Field(None, ge=0)


class CategoryOut(BaseModel):
    id: int
    name: str
    name_translations: Optional[Dict[str, str]] = None
    sort: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class MenuItemCreate(BaseModel):
    category_id: Optional[int] = None
    name: str = Field(..., min_length=1, max_length=200)
    name_translations: Optional[Dict[str, str]] = None
    description: Optional[str] = Field(None, max_length=500)
    description_translations: Optional[Dict[str, str]] = None
    price: float = Field(..., gt=0)
    image_url: Optional[str] = Field(None, max_length=500)
    is_active: bool = Field(default=True)
    is_available: bool = Field(default=True)


class MenuItemUpdate(BaseModel):
    category_id: Optional[int] = None
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    name_translations: Optional[Dict[str, str]] = None
    description: Optional[str] = Field(None, max_length=500)
    description_translations: Optional[Dict[str, str]] = None
    price: Optional[float] = Field(None, gt=0)
    image_url: Optional[str] = Field(None, max_length=500)
    is_active: Optional[bool] = None
    is_available: Optional[bool] = None


class MenuItemOut(BaseModel):
    id: int
    category_id: Optional[int] = None
    name: str
    name_translations: Optional[Dict[str, str]] = None
    description: Optional[str] = None
    description_translations: Optional[Dict[str, str]] = None
    price: float
    image_url: Optional[str] = None
    is_active: bool
    is_available: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class CategoryLocalizedOut(BaseModel):
    """localized category response that provides translated name based on locale."""
    id: int
    name: str  # Localized name based on user's language preference
    sort: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class MenuItemLocalizedOut(BaseModel):
    """localized menu item response that provides translated name and description based on locale."""
    id: int
    category_id: Optional[int] = None
    name: str  # Localized name based on user's language preference
    description: Optional[str] = None  # Localized description based on user's language preference
    price: float
    image_url: Optional[str] = None
    is_active: bool
    is_available: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
