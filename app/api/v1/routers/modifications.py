from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.security import get_current_user, require_admin
from app.db.session import get_db
from app import models
from app.schemas.modifications import (
    ModificationTypeOut,
    ModificationTypeIn,
    BulkModificationRequest,
    SingleModificationRequest,
    ModificationResponse,
    OrderItemModificationOut,
)
from app.services.locale.locale_helper import get_localized_modification_type_name
from app.services.locale.translation_service import get_translation_service

router = APIRouter(prefix="/modifications", tags=["modifications"])


# cRUD endpoints for modification types
@router.get("/types", response_model=List[ModificationTypeOut])
def get_modification_types(
    category: str = Query(None, description="Filter by category: sauce or removal"),
    is_active: bool = Query(True, description="Filter by active status"),
    lc: str = Query("en", pattern="^(ru|kz|en)$"),
    db: Session = Depends(get_db),
):
    """get all available modification types"""
    query = db.query(models.ModificationType)
    
    if category:
        query = query.filter(models.ModificationType.category == category)
    
    query = query.filter(models.ModificationType.is_active == is_active)
    
    modification_types = query.order_by(models.ModificationType.name).all()
    
    # apply localization
    for mod_type in modification_types:
        mod_type.name = get_localized_modification_type_name(mod_type, lc)
    
    return modification_types


@router.post("/types", response_model=ModificationTypeOut)
def create_modification_type(
    payload: ModificationTypeIn,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_admin),
):
    """create a new modification type (admin only)"""
    # Auto-generate translations if Russian text is provided
    translation_service = get_translation_service()
    name_translations = payload.name_translations
    if translation_service.is_available():
        name_translations = translation_service.auto_populate_translations(
            payload.name, 
            existing_translations=payload.name_translations
        )
    
    modification_type = models.ModificationType(
        name=payload.name,
        name_translations=name_translations,
        category=payload.category,
        is_default=payload.is_default,
        is_active=payload.is_active
    )
    db.add(modification_type)
    db.commit()
    db.refresh(modification_type)
    return modification_type


@router.put("/types/{type_id}", response_model=ModificationTypeOut)
def update_modification_type(
    type_id: int,
    payload: ModificationTypeIn,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_admin),
):
    """update a modification type (admin only)"""
    modification_type = db.get(models.ModificationType, type_id)
    if not modification_type:
        raise HTTPException(status_code=404, detail="Modification type not found")
    
    # Auto-generate translations if Russian text is provided
    translation_service = get_translation_service()
    
    # update fields explicitly to handle translations properly
    if payload.name is not None:
        modification_type.name = payload.name
        # Auto-translate name if translation service is available
        if translation_service.is_available():
            modification_type.name_translations = translation_service.auto_populate_translations(
                payload.name, 
                existing_translations=modification_type.name_translations
            )
    if payload.name_translations is not None:
        modification_type.name_translations = payload.name_translations
    if payload.category is not None:
        modification_type.category = payload.category
    if payload.is_default is not None:
        modification_type.is_default = payload.is_default
    if payload.is_active is not None:
        modification_type.is_active = payload.is_active
    
    db.commit()
    db.refresh(modification_type)
    return modification_type


@router.delete("/types/{type_id}")
def delete_modification_type(
    type_id: int,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_admin),
):
    """delete a modification type (admin only)"""
    modification_type = db.get(models.ModificationType, type_id)
    if not modification_type:
        raise HTTPException(status_code=404, detail="Modification type not found")
    
    db.delete(modification_type)
    db.commit()
    return {"message": "Modification type deleted successfully"}


# single dish modification endpoints
@router.post("/single", response_model=ModificationResponse)
def apply_single_modification(
    payload: SingleModificationRequest,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    """apply modifications to a single order item"""
    # verify order item exists and belongs to user
    order_item = db.get(models.OrderItem, payload.order_item_id)
    if not order_item:
        raise HTTPException(status_code=404, detail="Order item not found")
    
    order = db.get(models.Order, order_item.order_id)
    if not order or order.user_id != user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # check if order can still be modified (not delivered/cancelled)
    if order.status in ["DELIVERED", "CANCELLED"]:
        raise HTTPException(status_code=400, detail="Cannot modify completed order")
    
    # clear existing modifications for this order item
    db.query(models.OrderItemModification).filter(
        models.OrderItemModification.order_item_id == payload.order_item_id
    ).delete()
    
    # apply new modifications
    for mod in payload.modifications:
        # verify modification type exists
        mod_type = db.get(models.ModificationType, mod.modification_type_id)
        if not mod_type or not mod_type.is_active:
            raise HTTPException(status_code=400, detail=f"Invalid modification type: {mod.modification_type_id}")
        
        # create modification
        order_mod = models.OrderItemModification(
            order_item_id=payload.order_item_id,
            modification_type_id=mod.modification_type_id,
            action=mod.action,
        )
        db.add(order_mod)
    
    db.commit()
    
    return ModificationResponse(
        success=True,
        message="Modifications applied successfully",
        modified_items=[payload.order_item_id]
    )


# bulk modification endpoints
@router.post("/bulk", response_model=ModificationResponse)
def apply_bulk_modifications(
    payload: BulkModificationRequest,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    """apply modifications to multiple order items"""
    if not payload.order_item_ids:
        raise HTTPException(status_code=400, detail="Order item IDs required")
    
    # verify all order items exist and belong to user
    order_items = db.query(models.OrderItem).filter(
        models.OrderItem.id.in_(payload.order_item_ids)
    ).all()
    
    if len(order_items) != len(payload.order_item_ids):
        raise HTTPException(status_code=404, detail="Some order items not found")
    
    # verify all orders belong to user and can be modified
    order_ids = list(set(item.order_id for item in order_items))
    orders = db.query(models.Order).filter(models.Order.id.in_(order_ids)).all()
    
    for order in orders:
        if order.user_id != user.id:
            raise HTTPException(status_code=403, detail="Access denied")
        if order.status in ["DELIVERED", "CANCELLED"]:
            raise HTTPException(status_code=400, detail=f"Cannot modify completed order {order.number}")
    
    modified_items = []
    
    for order_item_id in payload.order_item_ids:
        # clear existing modifications for this order item
        db.query(models.OrderItemModification).filter(
            models.OrderItemModification.order_item_id == order_item_id
        ).delete()
        
        # apply new modifications
        for mod in payload.modifications:
            # verify modification type exists
            mod_type = db.get(models.ModificationType, mod.modification_type_id)
            if not mod_type or not mod_type.is_active:
                raise HTTPException(status_code=400, detail=f"Invalid modification type: {mod.modification_type_id}")
            
            # create modification
            order_mod = models.OrderItemModification(
                order_item_id=order_item_id,
                modification_type_id=mod.modification_type_id,
                action=mod.action,
            )
            db.add(order_mod)
        
        modified_items.append(order_item_id)
    
    db.commit()
    
    return ModificationResponse(
        success=True,
        message=f"Modifications applied to {len(modified_items)} items",
        modified_items=modified_items
    )


@router.get("/order-item/{order_item_id}", response_model=List[OrderItemModificationOut])
def get_order_item_modifications(
    order_item_id: int,
    lc: str = Query("en", pattern="^(ru|kz|en)$"),
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    """get all modifications for a specific order item"""
    # verify order item exists and belongs to user
    order_item = db.get(models.OrderItem, order_item_id)
    if not order_item:
        raise HTTPException(status_code=404, detail="Order item not found")
    
    order = db.get(models.Order, order_item.order_id)
    if not order or order.user_id != user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    modifications = db.query(models.OrderItemModification).filter(
        models.OrderItemModification.order_item_id == order_item_id
    ).all()
    
    # apply localization to nested modification types
    for modification in modifications:
        if modification.modification_type:
            modification.modification_type.name = get_localized_modification_type_name(modification.modification_type, lc)
    
    return modifications


@router.delete("/order-item/{order_item_id}")
def clear_order_item_modifications(
    order_item_id: int,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    """clear all modifications for a specific order item"""
    # verify order item exists and belongs to user
    order_item = db.get(models.OrderItem, order_item_id)
    if not order_item:
        raise HTTPException(status_code=404, detail="Order item not found")
    
    order = db.get(models.Order, order_item.order_id)
    if not order or order.user_id != user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # check if order can still be modified
    if order.status in ["DELIVERED", "CANCELLED"]:
        raise HTTPException(status_code=400, detail="Cannot modify completed order")
    
    # delete all modifications for this order item
    deleted_count = db.query(models.OrderItemModification).filter(
        models.OrderItemModification.order_item_id == order_item_id
    ).delete()
    
    db.commit()
    
    return {"message": f"Cleared {deleted_count} modifications"}