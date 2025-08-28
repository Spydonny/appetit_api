from typing import List, Optional
from pydantic import BaseModel, validator
from datetime import datetime


class CartItemModificationOut(BaseModel):
    id: int
    modification_type_id: int
    modification_name: str
    action: str  # 'add' or 'remove'

    class Config:
        from_attributes = True


class CartItemOut(BaseModel):
    id: int
    item_id: int
    item_name: str
    item_price: float
    qty: int
    line_total: float
    modifications: List[CartItemModificationOut] = []
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class CartOut(BaseModel):
    id: int
    user_id: int
    items: List[CartItemOut] = []
    subtotal: float
    total_items: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class AddToCartRequest(BaseModel):
    item_id: int
    qty: int = 1
    modifications: List[dict] = []  # [{"modification_type_id": 1, "action": "add"}]


class UpdateCartItemRequest(BaseModel):
    qty: int
    modifications: Optional[List[dict]] = None  # [{"modification_type_id": 1, "action": "add"}]


class CartItemResponse(BaseModel):
    message: str
    cart_item: Optional[CartItemOut] = None
    cart: Optional[CartOut] = None


class CartResponse(BaseModel):
    message: str
    cart: CartOut


class CartPriceRequest(BaseModel):
    promocode: Optional[str] = None
    pickup_or_delivery: Optional[str] = None  # delivery|pickup
    address: Optional[str] = None


class CartPriceResponse(BaseModel):
    subtotal: float
    discount: float
    total: float
    promocode_valid: bool = False
    promocode_message: Optional[str] = None


# Test-compatible schema that matches test expectations
class CartItemCreate(BaseModel):
    """Test-compatible cart item creation schema"""
    dish_id: int
    quantity: int
    modifications: List[dict] = []
    
    @validator('quantity')
    def validate_quantity(cls, v):
        if v <= 0:
            raise ValueError('Quantity must be greater than 0')
        return v