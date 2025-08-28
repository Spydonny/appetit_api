import random
import string
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.security import require_manager, require_admin
from app.db.session import get_db
from app import models
from app.schemas.admin import PromoGenerateRequest, PromoGenerateResponse, PromoOut, PromoUpdate
from app.schemas.promo_cart import PromoCodeCreate, PromoCodeUpdate

router = APIRouter(prefix="/admin/promo", tags=["admin"])


def _gen_code(prefix: str, length: int) -> str:
    alphabet = string.ascii_uppercase + string.digits
    return prefix + "".join(random.choice(alphabet) for _ in range(length))


@router.post("/generate", response_model=PromoGenerateResponse)
def generate_promo(req: PromoGenerateRequest, db: Session = Depends(get_db), admin = Depends(require_manager)):
    if req.length <= 0 or req.count <= 0:
        raise HTTPException(status_code=400, detail="Invalid length or count")

    # create batch record
    batch = models.PromoBatch(prefix=req.prefix, length=req.length, count=req.count, created_by=admin.id)
    db.add(batch)
    db.commit()
    db.refresh(batch)

    created = 0
    attempts = 0
    max_attempts = req.count * 10
    while created < req.count and attempts < max_attempts:
        attempts += 1
        code = _gen_code(req.prefix, req.length)
        # try insert
        if db.get(models.Promocode, code):
            continue
        pc = models.Promocode(
            code=code,
            kind=req.kind,
            value=req.value,
            active=req.active,
            valid_from=req.valid_from,
            valid_to=req.valid_to,
            max_redemptions=req.max_redemptions,
            per_user_limit=req.per_user_limit,
            min_subtotal=req.min_subtotal,
            created_by=admin.id,
        )
        db.add(pc)
        try:
            db.commit()
            created += 1
        except Exception:
            db.rollback()
            # collision or other issue, continue trying
            continue

    return PromoGenerateResponse(batch_id=batch.id, generated=created, prefix=req.prefix, length=req.length)


# promocode CRUD operations

@router.get("", response_model=List[PromoOut])
def list_promocodes(
    active: bool = None,
    db: Session = Depends(get_db),
    admin = Depends(require_manager)
):
    """list all promocodes"""
    q = db.query(models.Promocode)
    if active is not None:
        q = q.filter(models.Promocode.active == active)
    q = q.order_by(models.Promocode.created_at.desc())
    return q.all()


@router.get("/{code}", response_model=PromoOut)
def get_promocode(
    code: str,
    db: Session = Depends(get_db),
    admin = Depends(require_manager)
):
    """get a specific promocode"""
    promo = db.query(models.Promocode).filter(models.Promocode.code == code).first()
    if not promo:
        raise HTTPException(status_code=404, detail="Promocode not found")
    return promo


@router.put("/{code}", response_model=PromoOut)
def update_promocode(
    code: str,
    payload: PromoUpdate,
    db: Session = Depends(get_db),
    admin = Depends(require_manager)
):
    """update a promocode"""
    promo = db.query(models.Promocode).filter(models.Promocode.code == code).first()
    if not promo:
        raise HTTPException(status_code=404, detail="Promocode not found")
    
    # update fields if provided
    if payload.kind is not None:
        if payload.kind not in ["percent", "amount"]:
            raise HTTPException(status_code=400, detail="Invalid kind. Must be 'percent' or 'amount'")
        promo.kind = payload.kind
    
    if payload.value is not None:
        if payload.value <= 0:
            raise HTTPException(status_code=400, detail="Value must be greater than 0")
        promo.value = payload.value
    
    if payload.active is not None:
        promo.active = payload.active
    
    if payload.valid_from is not None:
        promo.valid_from = payload.valid_from
    
    if payload.valid_to is not None:
        promo.valid_to = payload.valid_to
    
    if payload.max_redemptions is not None:
        promo.max_redemptions = payload.max_redemptions
    
    if payload.per_user_limit is not None:
        promo.per_user_limit = payload.per_user_limit
    
    if payload.min_subtotal is not None:
        promo.min_subtotal = payload.min_subtotal
    
    db.add(promo)
    db.commit()
    db.refresh(promo)
    return promo


@router.delete("/{code}")
def delete_promocode(
    code: str,
    db: Session = Depends(get_db),
    admin = Depends(require_manager)
):
    """delete a promocode"""
    promo = db.query(models.Promocode).filter(models.Promocode.code == code).first()
    if not promo:
        raise HTTPException(status_code=404, detail="Promocode not found")
    
    # check if promocode has been used
    if promo.used_count > 0:
        raise HTTPException(status_code=400, detail="Cannot delete promocode that has been used. Consider deactivating instead.")
    
    db.delete(promo)
    db.commit()
    return {"message": "Promocode deleted successfully"}


# Additional functions expected by tests
@router.post("/create")
def create_promo(payload: PromoCodeCreate, db: Session = Depends(get_db), _=Depends(require_admin)):
    """Create a single promo code"""
    # Check if code already exists
    existing = db.query(models.Promocode).filter(models.Promocode.code == payload.code).first()
    if existing:
        raise HTTPException(status_code=400, detail="Promo code already exists")
    
    # Create new promo code
    promo = models.Promocode(
        code=payload.code,
        kind="percent",  # Assuming discount_percent means percentage
        value=payload.discount_percent,
        active=True,  # Default to active
        min_subtotal=payload.min_order_amount,
        max_redemptions=payload.max_uses,
        valid_to=payload.expires_at,
        created_by=_.id
    )
    
    db.add(promo)
    db.commit()
    db.refresh(promo)
    return promo


def list_promos(db: Session = Depends(get_db), _=Depends(require_admin)):
    """Alias for list_promocodes with require_admin"""
    return list_promocodes(db=db, admin=_)


def update_promo(promo_id: int, payload: PromoCodeUpdate, db: Session = Depends(get_db), _=Depends(require_admin)):
    """Update a promo code by ID"""
    promo = db.query(models.Promocode).filter(models.Promocode.id == promo_id).first()
    if not promo:
        raise HTTPException(status_code=404, detail="Promo code not found")
    
    if payload.discount_percent is not None:
        promo.value = payload.discount_percent
        # Also set discount_percent for test compatibility
        if hasattr(promo, 'discount_percent'):
            promo.discount_percent = payload.discount_percent
    
    if payload.is_active is not None:
        promo.active = payload.is_active
        # Also set is_active for test compatibility
        if hasattr(promo, 'is_active'):
            promo.is_active = payload.is_active
    
    db.commit()
    db.refresh(promo)
    return promo


def delete_promo(promo_id: int, db: Session = Depends(get_db), _=Depends(require_admin)):
    """Delete a promo code by ID"""
    promo = db.query(models.Promocode).filter(models.Promocode.id == promo_id).first()
    if not promo:
        raise HTTPException(status_code=404, detail="Promo code not found")
    
    db.delete(promo)
    db.commit()
    return {"message": "Promo code deleted successfully"}
