import random
import string
from datetime import datetime, timedelta
from typing import List, Optional, Dict

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, case, and_, or_, distinct

from app.core.security import require_manager, get_password_hash
from app.db.session import get_db
from app import models
from app.schemas.admin import PromoGenerateRequest, PromoGenerateResponse, PromoOut, PromoUpdate, BannerCreate, BannerUpdate, BannerOut
from app.schemas.users import CourierCreate, CourierUpdate, UserOut

router = APIRouter(prefix="/manager", tags=["manager"])

# =======================
# PROMO CODE MANAGEMENT
# =======================

def _gen_code(prefix: str, length: int) -> str:
    alphabet = string.ascii_uppercase + string.digits
    return prefix + "".join(random.choice(alphabet) for _ in range(length))


@router.post("/promo/generate", response_model=PromoGenerateResponse)
def generate_promo(req: PromoGenerateRequest, db: Session = Depends(get_db), manager = Depends(require_manager)):
    if req.length <= 0 or req.count <= 0:
        raise HTTPException(status_code=400, detail="Invalid length or count")

    # create batch record
    batch = models.PromoBatch(prefix=req.prefix, length=req.length, count=req.count, created_by=manager.id)
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
            created_by=manager.id,
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


@router.get("/promo", response_model=List[PromoOut])
def list_promocodes(
    active: bool = None,
    db: Session = Depends(get_db),
    manager = Depends(require_manager)
):
    """list all promocodes"""
    q = db.query(models.Promocode)
    if active is not None:
        q = q.filter(models.Promocode.active == active)
    q = q.order_by(models.Promocode.created_at.desc())
    promocodes = q.all()
    
    # Transform the data to handle NULL values and ensure schema compliance
    result = []
    for promo in promocodes:
        result.append(PromoOut(
            code=promo.code,
            kind=promo.kind,
            value=promo.value or 0.0,  # Handle NULL values
            active=promo.active,
            used_count=promo.used_count,
            valid_from=promo.valid_from,
            valid_to=promo.valid_to,
            max_redemptions=promo.max_redemptions,
            per_user_limit=promo.per_user_limit,
            min_subtotal=promo.min_subtotal,
            created_at=promo.created_at,
            created_by=promo.created_by
        ))
    return result


@router.get("/promo/{code}", response_model=PromoOut)
def get_promocode(
    code: str,
    db: Session = Depends(get_db),
    manager = Depends(require_manager)
):
    """get a specific promocode"""
    promo = db.query(models.Promocode).filter(models.Promocode.code == code).first()
    if not promo:
        raise HTTPException(status_code=404, detail="Promocode not found")
    
    # Transform the data to handle NULL values and ensure schema compliance
    return PromoOut(
        code=promo.code,
        kind=promo.kind,
        value=promo.value or 0.0,  # Handle NULL values
        active=promo.active,
        used_count=promo.used_count,
        valid_from=promo.valid_from,
        valid_to=promo.valid_to,
        max_redemptions=promo.max_redemptions,
        per_user_limit=promo.per_user_limit,
        min_subtotal=promo.min_subtotal,
        created_at=promo.created_at,
        created_by=promo.created_by
    )


@router.put("/promo/{code}", response_model=PromoOut)
def update_promocode(
    code: str,
    payload: PromoUpdate,
    db: Session = Depends(get_db),
    manager = Depends(require_manager)
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
    
    # Transform the data to handle NULL values and ensure schema compliance
    return PromoOut(
        code=promo.code,
        kind=promo.kind,
        value=promo.value or 0.0,  # Handle NULL values
        active=promo.active,
        used_count=promo.used_count,
        valid_from=promo.valid_from,
        valid_to=promo.valid_to,
        max_redemptions=promo.max_redemptions,
        per_user_limit=promo.per_user_limit,
        min_subtotal=promo.min_subtotal,
        created_at=promo.created_at,
        created_by=promo.created_by
    )


@router.delete("/promo/{code}")
def delete_promocode(
    code: str,
    db: Session = Depends(get_db),
    manager = Depends(require_manager)
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


# =======================
# BANNER MANAGEMENT
# =======================

@router.get("/banners", response_model=List[BannerOut])
def list_banners(
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    db: Session = Depends(get_db),
    _: models.User = Depends(require_manager),
):
    """list all banners with optional filtering"""
    query = db.query(models.Banner)
    
    if is_active is not None:
        query = query.filter(models.Banner.is_active == is_active)
    
    # filter by date range - only show banners that are currently valid or have no date restrictions
    now = datetime.utcnow()
    query = query.filter(
        (models.Banner.start_date.is_(None) | (models.Banner.start_date <= now)) &
        (models.Banner.end_date.is_(None) | (models.Banner.end_date >= now))
    )
    
    banners = query.order_by(models.Banner.sort_order.asc(), models.Banner.created_at.desc()).all()
    return banners


@router.get("/banners/all", response_model=List[BannerOut])
def list_all_banners(
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    db: Session = Depends(get_db),
    _: models.User = Depends(require_manager),
):
    """list all banners including expired ones (manager view)"""
    query = db.query(models.Banner)
    
    if is_active is not None:
        query = query.filter(models.Banner.is_active == is_active)
    
    banners = query.order_by(models.Banner.sort_order.asc(), models.Banner.created_at.desc()).all()
    return banners


@router.get("/banners/{banner_id}", response_model=BannerOut)
def get_banner(
    banner_id: int,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_manager),
):
    """get a specific banner"""
    banner = db.get(models.Banner, banner_id)
    if not banner:
        raise HTTPException(status_code=404, detail="Banner not found")
    return banner


@router.post("/banners", response_model=BannerOut)
def create_banner(
    payload: BannerCreate,
    db: Session = Depends(get_db),
    manager: models.User = Depends(require_manager),
):
    """create a new banner"""
    banner_data = payload.dict()
    banner_data["created_by"] = manager.id
    
    banner = models.Banner(**banner_data)
    db.add(banner)
    db.commit()
    db.refresh(banner)
    return banner


@router.put("/banners/{banner_id}", response_model=BannerOut)
def update_banner(
    banner_id: int,
    payload: BannerUpdate,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_manager),
):
    """update a banner"""
    banner = db.get(models.Banner, banner_id)
    if not banner:
        raise HTTPException(status_code=404, detail="Banner not found")
    
    # update fields if provided
    update_data = payload.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(banner, key, value)
    
    db.add(banner)
    db.commit()
    db.refresh(banner)
    return banner


@router.delete("/banners/{banner_id}")
def delete_banner(
    banner_id: int,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_manager),
):
    """delete a banner"""
    banner = db.get(models.Banner, banner_id)
    if not banner:
        raise HTTPException(status_code=404, detail="Banner not found")
    
    db.delete(banner)
    db.commit()
    return {"message": "Banner deleted successfully"}


@router.post("/banners/{banner_id}/activate")
def activate_banner(
    banner_id: int,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_manager),
):
    """activate a banner"""
    banner = db.get(models.Banner, banner_id)
    if not banner:
        raise HTTPException(status_code=404, detail="Banner not found")
    
    banner.is_active = True
    db.add(banner)
    db.commit()
    return {"message": "Banner activated successfully"}


@router.post("/banners/{banner_id}/deactivate")
def deactivate_banner(
    banner_id: int,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_manager),
):
    """deactivate a banner"""
    banner = db.get(models.Banner, banner_id)
    if not banner:
        raise HTTPException(status_code=404, detail="Banner not found")
    
    banner.is_active = False
    db.add(banner)
    db.commit()
    return {"message": "Banner deactivated successfully"}


@router.post("/banners/reorder")
def reorder_banners(
    banner_order: List[int],
    db: Session = Depends(get_db),
    _: models.User = Depends(require_manager),
):
    """reorder banners by updating their sort_order"""
    if not banner_order:
        raise HTTPException(status_code=400, detail="Banner order list cannot be empty")
    
    # verify all banner IDs exist
    banners = db.query(models.Banner).filter(models.Banner.id.in_(banner_order)).all()
    if len(banners) != len(banner_order):
        raise HTTPException(status_code=400, detail="One or more banner IDs not found")
    
    # update sort_order for each banner
    for index, banner_id in enumerate(banner_order):
        banner = next((b for b in banners if b.id == banner_id), None)
        if banner:
            banner.sort_order = index
            db.add(banner)
    
    db.commit()
    return {"message": f"Reordered {len(banner_order)} banners successfully"}


# =======================
# ANALYTICS (READ-ONLY)
# =======================

@router.get("/analytics/summary")
def analytics_summary(
    from_: Optional[str] = Query(None, alias="from"),
    to: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    _: models.User = Depends(require_manager)
):
    """Get summary analytics - read-only for managers"""
    from datetime import datetime
    
    # parse date range
    if from_:
        from_date = datetime.fromisoformat(from_.replace('Z', '+00:00'))
    else:
        from_date = None
    
    if to:
        to_date = datetime.fromisoformat(to.replace('Z', '+00:00'))
    else:
        to_date = None
    
    # base query
    query = db.query(models.Order)
    
    if from_date:
        query = query.filter(models.Order.created_at >= from_date)
    if to_date:
        query = query.filter(models.Order.created_at <= to_date)
    
    # aggregate metrics
    orders = query.all()
    
    total_orders = len(orders)
    total_revenue = sum(order.total for order in orders)
    avg_order_value = total_revenue / total_orders if total_orders > 0 else 0
    unique_customers = len(set(order.user_id for order in orders if order.user_id))
    
    # status breakdown
    status_counts = {}
    for order in orders:
        status_counts[order.status] = status_counts.get(order.status, 0) + 1
    
    return {
        "total_orders": total_orders,
        "total_revenue": float(total_revenue),
        "avg_order_value": float(avg_order_value),
        "unique_customers": unique_customers,
        "status_breakdown": status_counts,
    }


@router.get("/analytics/orders-by-period")
def orders_by_period(
    period: str = Query("day", description="Period: day, week, month"),
    from_: Optional[str] = Query(None, alias="from"),
    to: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    _: models.User = Depends(require_manager)
):
    """Get orders grouped by time period - read-only for managers"""
    from datetime import datetime, timedelta
    
    # parse date range
    if from_:
        from_date = datetime.fromisoformat(from_.replace('Z', '+00:00'))
    else:
        from_date = datetime.utcnow() - timedelta(days=30)
    
    if to:
        to_date = datetime.fromisoformat(to.replace('Z', '+00:00'))
    else:
        to_date = datetime.utcnow()
    
    # get orders in date range
    orders = db.query(models.Order).filter(
        models.Order.created_at >= from_date,
        models.Order.created_at <= to_date
    ).all()
    
    # group by period
    def period_key(dt: datetime):
        if period == "day":
            return dt.date().isoformat()
        elif period == "week":
            # get Monday of the week
            monday = dt.date() - timedelta(days=dt.weekday())
            return monday.isoformat()
        elif period == "month":
            return f"{dt.year}-{dt.month:02d}"
        else:
            return dt.date().isoformat()
    
    period_data = {}
    for order in orders:
        key = period_key(order.created_at)
        if key not in period_data:
            period_data[key] = {"orders": 0, "revenue": 0}
        period_data[key]["orders"] += 1
        period_data[key]["revenue"] += float(order.total)
    
    # convert to list and sort
    result = []
    for period_key, data in sorted(period_data.items()):
        result.append({
            "period": period_key,
            "orders": data["orders"],
            "revenue": data["revenue"]
        })
    
    return result


@router.get("/analytics/dish-popularity")
def dish_popularity(
    from_: Optional[str] = Query(None, alias="from"),
    to: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=1000),
    db: Session = Depends(get_db),
    _: models.User = Depends(require_manager)
):
    """Get dish popularity analytics - read-only for managers"""
    from datetime import datetime
    
    # parse date range
    if from_:
        from_date = datetime.fromisoformat(from_.replace('Z', '+00:00'))
    else:
        from_date = None
    
    if to:
        to_date = datetime.fromisoformat(to.replace('Z', '+00:00'))
    else:
        to_date = None
    
    # build query for order items
    query = db.query(models.OrderItem).join(models.Order)
    
    if from_date:
        query = query.filter(models.Order.created_at >= from_date)
    if to_date:
        query = query.filter(models.Order.created_at <= to_date)
    
    order_items = query.all()
    
    # aggregate by dish name
    dish_stats = {}
    for item in order_items:
        name = item.name_snapshot
        if name not in dish_stats:
            dish_stats[name] = {"qty": 0, "revenue": 0}
        dish_stats[name]["qty"] += item.qty
        dish_stats[name]["revenue"] += float(item.price_at_moment * item.qty)
    
    # convert to list, calculate avg price, and sort by quantity
    result = []
    for name, stats in dish_stats.items():
        avg_price = stats["revenue"] / stats["qty"] if stats["qty"] > 0 else 0
        result.append({
            "name": name,
            "qty": stats["qty"],
            "revenue": stats["revenue"],
            "avg_price": avg_price
        })
    
    # sort by quantity (descending) and limit
    result.sort(key=lambda x: x["qty"], reverse=True)
    return result[:limit]


# =======================
# COURIER USER MANAGEMENT
# =======================

@router.post("/couriers", response_model=UserOut)
def create_courier(
    payload: CourierCreate,
    db: Session = Depends(get_db),
    manager: models.User = Depends(require_manager),
):
    """Create a new courier user (managers only)"""
    # Check if user with email already exists
    existing_user = db.query(models.User).filter(models.User.email == payload.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="User with this email already exists")
    
    # Check if phone number is already taken (if provided)
    if payload.phone:
        existing_phone = db.query(models.User).filter(models.User.phone == payload.phone).first()
        if existing_phone:
            raise HTTPException(status_code=400, detail="User with this phone number already exists")
    
    # Hash password
    password_hash = get_password_hash(payload.password)
    
    # Create new courier user
    new_courier = models.User(
        full_name=payload.full_name,
        email=payload.email,
        phone=payload.phone,
        password_hash=password_hash,
        role="courier",  # Managers can only create couriers
        dob=payload.dob,
        is_email_verified=False,
        is_phone_verified=False
    )
    
    db.add(new_courier)
    db.commit()
    db.refresh(new_courier)
    
    return new_courier


@router.get("/couriers", response_model=List[UserOut])
def list_couriers(
    search: Optional[str] = Query(None, description="Search by name or email"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    _: models.User = Depends(require_manager),
):
    """List all courier users"""
    query = db.query(models.User).filter(models.User.role == "courier")
    
    # Search functionality
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            or_(
                models.User.full_name.ilike(search_term),
                models.User.email.ilike(search_term)
            )
        )
    
    # Apply pagination
    couriers = query.offset(offset).limit(limit).all()
    
    return couriers


@router.get("/couriers/{courier_id}", response_model=UserOut)
def get_courier(
    courier_id: int,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_manager),
):
    """Get specific courier by ID"""
    courier = db.get(models.User, courier_id)
    if not courier:
        raise HTTPException(status_code=404, detail="Courier not found")
    
    if courier.role != "courier":
        raise HTTPException(status_code=400, detail="User is not a courier")
    
    return courier


@router.put("/couriers/{courier_id}", response_model=UserOut)
def update_courier(
    courier_id: int,
    payload: CourierUpdate,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_manager),
):
    """Update courier details"""
    courier = db.get(models.User, courier_id)
    if not courier:
        raise HTTPException(status_code=404, detail="Courier not found")
    
    if courier.role != "courier":
        raise HTTPException(status_code=400, detail="User is not a courier")
    
    # Check email uniqueness if email is being changed
    if payload.email and payload.email != courier.email:
        existing_email = db.query(models.User).filter(
            models.User.email == payload.email,
            models.User.id != courier_id
        ).first()
        if existing_email:
            raise HTTPException(status_code=400, detail="Email already taken by another user")
    
    # Check phone uniqueness if phone is being changed
    if payload.phone and payload.phone != courier.phone:
        existing_phone = db.query(models.User).filter(
            models.User.phone == payload.phone,
            models.User.id != courier_id
        ).first()
        if existing_phone:
            raise HTTPException(status_code=400, detail="Phone number already taken by another user")
    
    # Update fields if provided
    update_data = payload.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(courier, key, value)
    
    db.add(courier)
    db.commit()
    db.refresh(courier)
    
    return courier


@router.delete("/couriers/{courier_id}")
def delete_courier(
    courier_id: int,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_manager),
):
    """Delete a courier user"""
    courier = db.get(models.User, courier_id)
    if not courier:
        raise HTTPException(status_code=404, detail="Courier not found")
    
    if courier.role != "courier":
        raise HTTPException(status_code=400, detail="User is not a courier")
    
    # Check if courier has any orders
    order_count = db.query(models.Order).filter(models.Order.user_id == courier_id).count()
    if order_count > 0:
        raise HTTPException(
            status_code=400, 
            detail=f"Cannot delete courier with {order_count} orders. Consider deactivating instead."
        )
    
    db.delete(courier)
    db.commit()
    
    return {"message": f"Courier {courier.full_name} deleted successfully"}


@router.get("/couriers/stats/summary")
def get_courier_stats(
    db: Session = Depends(get_db),
    _: models.User = Depends(require_manager),
):
    """Get courier statistics"""
    total_couriers = db.query(models.User).filter(models.User.role == "courier").count()
    verified_email_couriers = db.query(models.User).filter(
        models.User.role == "courier",
        models.User.is_email_verified == True
    ).count()
    verified_phone_couriers = db.query(models.User).filter(
        models.User.role == "courier",
        models.User.is_phone_verified == True
    ).count()
    
    return {
        "total_couriers": total_couriers,
        "email_verified_couriers": verified_email_couriers,
        "phone_verified_couriers": verified_phone_couriers,
        "verification_rate_email": round((verified_email_couriers / total_couriers * 100), 2) if total_couriers > 0 else 0,
        "verification_rate_phone": round((verified_phone_couriers / total_couriers * 100), 2) if total_couriers > 0 else 0,
    }