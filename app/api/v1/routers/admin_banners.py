from typing import List, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.security import require_manager
from app.db.session import get_db
from app import models
from app.schemas.admin import BannerCreate, BannerUpdate, BannerOut

router = APIRouter(prefix="/admin/banners", tags=["admin"])


@router.get("", response_model=List[BannerOut])
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


@router.get("/all", response_model=List[BannerOut])
def list_all_banners(
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    db: Session = Depends(get_db),
    _: models.User = Depends(require_manager),
):
    """list all banners including expired ones (admin view)"""
    query = db.query(models.Banner)
    
    if is_active is not None:
        query = query.filter(models.Banner.is_active == is_active)
    
    banners = query.order_by(models.Banner.sort_order.asc(), models.Banner.created_at.desc()).all()
    return banners


@router.get("/{banner_id}", response_model=BannerOut)
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


@router.post("", response_model=BannerOut)
def create_banner(
    payload: BannerCreate,
    db: Session = Depends(get_db),
    admin: models.User = Depends(require_manager),
):
    """create a new banner"""
    banner_data = payload.dict()
    banner_data["created_by"] = admin.id
    
    banner = models.Banner(**banner_data)
    db.add(banner)
    db.commit()
    db.refresh(banner)
    return banner


@router.put("/{banner_id}", response_model=BannerOut)
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


@router.delete("/{banner_id}")
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


@router.post("/{banner_id}/activate")
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


@router.post("/{banner_id}/deactivate")
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


@router.post("/reorder")
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
