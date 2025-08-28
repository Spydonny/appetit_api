from datetime import datetime
from typing import Optional
from decimal import Decimal

from sqlalchemy.orm import Session

from app import models


class PromoValidationResult:
    def __init__(self, valid: bool, discount: Decimal = Decimal('0.0'), reason: Optional[str] = None):
        self.valid = valid
        self.discount = Decimal(str(discount))
        self.reason = reason

    def dict(self):
        return {"valid": self.valid, "discount": float(self.discount), "reason": self.reason}


def calculate_discount(db: Session, code: Optional[str], subtotal: Decimal, user_id: Optional[int] = None) -> PromoValidationResult:
    if not code:
        return PromoValidationResult(valid=True, discount=Decimal('0.0'))

    promo: models.Promocode | None = db.query(models.Promocode).filter(models.Promocode.code == code).first()
    if not promo or not promo.is_active:
        return PromoValidationResult(valid=False, reason="invalid_or_inactive")

    now = datetime.utcnow()
    if promo.valid_from and now < promo.valid_from:
        return PromoValidationResult(valid=False, reason="not_started")
    if promo.valid_to and now > promo.valid_to:
        return PromoValidationResult(valid=False, reason="expired")

    if promo.min_subtotal is not None and subtotal < Decimal(str(promo.min_subtotal)):
        return PromoValidationResult(valid=False, reason="min_subtotal_not_met")

    # note: max_redemptions and per_user_limit aren't tracked in MVP without redemption logs
    # apply discount
    discount = Decimal('0.0')
    if promo.kind == "percent":
        discount = (subtotal * Decimal(str(promo.value)) / Decimal('100')).quantize(Decimal('0.01'))
    elif promo.kind == "amount":
        discount = Decimal(str(promo.value))

    # ensure non-negative total
    discount = min(discount, subtotal)
    return PromoValidationResult(valid=True, discount=discount)


def is_promo_valid(promo_code: str, order_total: float = 0.0, db: Session = None) -> bool:
    """Check if a promo code is valid (for tests)"""
    if not promo_code or db is None:
        return False
    
    promo = db.query(models.Promocode).filter(models.Promocode.code == promo_code).first()
    if not promo or not promo.is_active:
        return False
    
    # Check minimum order amount if specified
    if hasattr(promo, 'min_subtotal') and promo.min_subtotal and order_total < float(promo.min_subtotal):
        return False
    
    return True