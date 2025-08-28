from typing import List, Optional, Literal
from datetime import datetime
from pydantic import BaseModel, validator

from .modifications import OrderItemModificationIn, OrderItemModificationOut


class OrderItemIn(BaseModel):
    item_id: int
    qty: int
    modifications: Optional[List[OrderItemModificationIn]] = []


class OrderCreateRequest(BaseModel):
    items: List[OrderItemIn]
    pickup_or_delivery: str  # delivery|pickup
    address_text: Optional[str] = None
    lat: Optional[float] = None
    lng: Optional[float] = None
    promocode: Optional[str] = None
    payment_method: Optional[str] = "cod"  # cod|online
    utm_source: Optional[str] = None
    utm_medium: Optional[str] = None
    utm_campaign: Optional[str] = None
    ga_client_id: Optional[str] = None


class OrderUpdate(BaseModel):
    status: Optional[str] = None
    pickup_or_delivery: Optional[str] = None  # delivery|pickup
    address_text: Optional[str] = None
    lat: Optional[float] = None
    lng: Optional[float] = None
    paid: Optional[bool] = None
    payment_method: Optional[str] = None


class OrderStatusUpdate(BaseModel):
    """Schema for updating order status - used by couriers"""
    status: str
    
    @validator('status')
    def validate_status(cls, v):
        valid_statuses = ["NEW", "COOKING", "ON_WAY", "DELIVERED", "CANCELLED"]
        if v not in valid_statuses:
            raise ValueError(f"Status must be one of: {', '.join(valid_statuses)}")
        return v


class OrderItemOut(BaseModel):
    id: int
    item_id: Optional[int]
    name_snapshot: str
    qty: int
    price_at_moment: float
    modifications: Optional[List[OrderItemModificationOut]] = []

    class Config:
        from_attributes = True


class OrderOut(BaseModel):
    id: int
    number: str
    status: str
    pickup_or_delivery: str
    address_text: Optional[str] = None
    lat: Optional[float] = None
    lng: Optional[float] = None
    subtotal: float
    discount: float
    total: float
    paid: bool
    payment_method: str
    promocode_code: Optional[str] = None
    created_at: datetime
    items: List[OrderItemOut]

    class Config:
        from_attributes = True


class OrderListResponse(BaseModel):
    items: List[OrderOut]


class CommentIn(BaseModel):
    text: str


class CommentOut(BaseModel):
    id: int
    author_user_id: Optional[int]
    author_role: str
    text: str
    created_at: datetime

    class Config:
        from_attributes = True


# Test-compatible schemas that match test expectations
class OrderItemForTest(BaseModel):
    dish_id: int
    quantity: int
    modifications: Optional[List[dict]] = []
    
    def __getitem__(self, key):
        """Allow subscript access like a dictionary"""
        return getattr(self, key)


class OrderCreate(BaseModel):
    """Test-compatible order creation schema"""
    pickup_or_delivery: Literal["delivery", "pickup"]
    address: Optional[str] = None
    phone: Optional[str] = None
    items: List[OrderItemForTest]
