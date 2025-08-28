import hmac
import hashlib
from fastapi import APIRouter, Request, Header, HTTPException

from app.core.config import settings
from app.schemas.payments import PaymentInitRequest, PaymentInitResponse
from app.services.payments.mock import MockPayments

router = APIRouter(prefix="/payments", tags=["payments"]) 


@router.post("/init", response_model=PaymentInitResponse)
def init_payment(payload: PaymentInitRequest):
    provider = MockPayments()
    res = provider.init(order_id=payload.order_id, amount=payload.amount)
    if res.get("status") != "ok" or "checkout_url" not in res:
        raise HTTPException(status_code=400, detail="Unable to init payment")
    return PaymentInitResponse(checkout_url=res["checkout_url"]) 


@router.post("/callback")
async def callback(request: Request, x_signature: str | None = Header(None)):
    body = await request.body()
    secret = (settings.WEBHOOK_SECRET or "").encode()
    computed = hmac.new(secret, body, hashlib.sha256).hexdigest()
    if not x_signature or not hmac.compare_digest(computed, x_signature):
        raise HTTPException(status_code=401, detail="Invalid signature")
    return {"status": "ok"}
