from typing import Optional, List, Dict, Any, Union
from datetime import datetime
from pydantic import BaseModel, Field


class StatusUpdateRequest(BaseModel):
    status: str  # NEW|COOKING|ON_WAY|DELIVERED|CANCELLED


class PromoGenerateRequest(BaseModel):
    prefix: str
    length: int = 6
    count: int = 10
    kind: str = "percent"  # percent|amount
    value: float = 10.0
    active: bool = True
    valid_from: Optional[datetime] = None
    valid_to: Optional[datetime] = None
    max_redemptions: Optional[int] = None
    per_user_limit: Optional[int] = None
    min_subtotal: Optional[float] = None


class PromoGenerateResponse(BaseModel):
    batch_id: int
    generated: int
    prefix: str
    length: int


class PromoOut(BaseModel):
    code: str
    kind: str  # percent|amount
    value: float
    active: bool
    used_count: int
    valid_from: Optional[datetime] = None
    valid_to: Optional[datetime] = None
    max_redemptions: Optional[int] = None
    per_user_limit: Optional[int] = None
    min_subtotal: Optional[float] = None
    created_at: datetime
    created_by: Optional[int] = None

    class Config:
        from_attributes = True


class PromoUpdate(BaseModel):
    kind: Optional[str] = None  # percent|amount
    value: Optional[float] = None
    active: Optional[bool] = None
    valid_from: Optional[datetime] = None
    valid_to: Optional[datetime] = None
    max_redemptions: Optional[int] = None
    per_user_limit: Optional[int] = None
    min_subtotal: Optional[float] = None


class AdminPushTargeting(BaseModel):
    """advanced targeting options for push notifications."""
    audience: str = Field("all", description="Target audience: all, topic, platform, verified_users, role")
    topic: Optional[str] = Field(None, description="Topic name for topic-based messaging")
    platform: Optional[str] = Field(None, description="Target specific platform: android, ios, web")
    user_role: Optional[str] = Field(None, description="Target users with specific role: user, admin")
    verified_only: Optional[bool] = Field(None, description="Target only verified users (email or phone)")
    max_devices: Optional[int] = Field(None, description="Maximum number of devices to target")


class AdminPushRequest(BaseModel):
    title: str = Field(..., description="Notification title", max_length=100)
    body: str = Field(..., description="Notification body", max_length=500)
    targeting: AdminPushTargeting = Field(default_factory=AdminPushTargeting, description="Targeting options")
    data: Optional[Dict[str, str]] = Field(None, description="Custom data payload")
    priority: str = Field("normal", description="Message priority: normal or high")
    ttl: Optional[int] = Field(None, description="Time to live in seconds", ge=0, le=2419200)  # Max 4 weeks
    dry_run: bool = Field(False, description="Validate request without sending")


class PushResult(BaseModel):
    """individual push notification result."""
    token: Optional[str] = None
    success: bool
    message_id: Optional[str] = None
    error: Optional[str] = None


class AdminPushResponse(BaseModel):
    status: str = Field(..., description="Overall status: completed, error, skipped")
    sent: int = Field(0, description="Number of successfully sent notifications")
    failed: int = Field(0, description="Number of failed notifications")
    total: int = Field(0, description="Total number of devices targeted")
    targeting_method: str = Field(..., description="Method used for targeting")
    timestamp: str = Field(..., description="Response timestamp")
    message_id: Optional[str] = Field(None, description="Message ID for topic messages")
    topic: Optional[str] = Field(None, description="Topic name if topic messaging was used")
    errors: Optional[List[str]] = Field(None, description="List of error reasons")
    results: Optional[List[PushResult]] = Field(None, description="Detailed per-device results")
    reason: Optional[str] = Field(None, description="Reason for skipped or error status")


class AdminSmsRequest(BaseModel):
    message: str
    audience: str = "all"  # currently supports only "all"


class AdminSmsResponse(BaseModel):
    sent: int


class ImageUploadResponse(BaseModel):
    """response for successful image upload."""
    filename: str = Field(..., description="Generated filename of the processed image")
    image_url: str = Field(..., description="URL path to access the image")
    original_filename: str = Field(..., description="Original filename of uploaded image")
    size_bytes: int = Field(..., description="Size of processed image in bytes")


class MenuItemImageUpdate(BaseModel):
    """schema for updating menu item image via file upload."""
    image_url: Optional[str] = Field(None, description="New image URL for the menu item")


class BannerCreate(BaseModel):
    """schema for creating a new banner."""
    title: str = Field(..., description="Banner title", max_length=255)
    title_translations: Optional[Dict[str, str]] = Field(None, description="Title translations (ru, kk, en)")
    description: Optional[str] = Field(None, description="Banner description")
    description_translations: Optional[Dict[str, str]] = Field(None, description="Description translations (ru, kk, en)")
    image_url: str = Field(..., description="WebP format image URL")
    link_url: Optional[str] = Field(None, description="Optional click URL")
    is_active: bool = Field(True, description="Whether banner is active")
    sort_order: int = Field(0, description="Sort order for banner display")
    start_date: Optional[datetime] = Field(None, description="When banner becomes active")
    end_date: Optional[datetime] = Field(None, description="When banner expires")


class BannerUpdate(BaseModel):
    """schema for updating an existing banner."""
    title: Optional[str] = Field(None, description="Banner title", max_length=255)
    title_translations: Optional[Dict[str, str]] = Field(None, description="Title translations (ru, kk, en)")
    description: Optional[str] = Field(None, description="Banner description")
    description_translations: Optional[Dict[str, str]] = Field(None, description="Description translations (ru, kk, en)")
    image_url: Optional[str] = Field(None, description="WebP format image URL")
    link_url: Optional[str] = Field(None, description="Optional click URL")
    is_active: Optional[bool] = Field(None, description="Whether banner is active")
    sort_order: Optional[int] = Field(None, description="Sort order for banner display")
    start_date: Optional[datetime] = Field(None, description="When banner becomes active")
    end_date: Optional[datetime] = Field(None, description="When banner expires")


class BannerOut(BaseModel):
    """schema for banner output."""
    id: int
    title: str
    title_translations: Optional[Dict[str, str]] = None
    description: Optional[str] = None
    description_translations: Optional[Dict[str, str]] = None
    image_url: str
    link_url: Optional[str] = None
    is_active: bool
    sort_order: int
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    created_by: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
