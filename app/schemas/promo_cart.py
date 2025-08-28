from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel


class CartItem(BaseModel):
    item_id: int
    qty: int


class PromoValidateRequest(BaseModel):
    code: Optional[str] = None
    cart: Optional[List[CartItem]] = None
    subtotal: Optional[float] = None


class PromoValidateResponse(BaseModel):
    valid: bool
    discount: float
    reason: Optional[str] = None
    promocode: Optional[dict] = None


class PriceRequest(BaseModel):
    items: List[CartItem]
    promocode: Optional[str] = None
    pickup_or_delivery: Optional[str] = None  # delivery|pickup
    address: Optional[str] = None


class PriceDetailsLine(BaseModel):
    item_id: int
    name: str
    qty: int
    unit_price: float
    line_total: float


class PriceResponse(BaseModel):
    subtotal: float
    discount: float
    total: float
    details: List[PriceDetailsLine]


class PromoCodeCreate(BaseModel):
    code: str
    discount_percent: float
    min_order_amount: Optional[float] = None
    max_uses: Optional[int] = None
    expires_at: Optional[datetime] = None


class PromoCodeUpdate(BaseModel):
    discount_percent: Optional[float] = None
    is_active: Optional[bool] = None
