from pydantic import BaseModel


class PaymentInitRequest(BaseModel):
    order_id: int
    amount: float


class PaymentInitResponse(BaseModel):
    checkout_url: str
