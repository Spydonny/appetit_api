from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.security import require_admin
from app.db.session import get_db
from app import models
from app.schemas.orders import OrderOut, OrderUpdate
from app.schemas.admin import StatusUpdateRequest
from app.services.push.fcm_admin import send_to_token
from app.services.email.order_emails import send_order_status, send_order_delivered

router = APIRouter(prefix="/admin/orders", tags=["admin"])


@router.get("", response_model=List[OrderOut])
def list_orders(
    status: Optional[str] = Query(None),
    from_: Optional[str] = Query(None, alias="from"),
    to: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    _: models.User = Depends(require_admin),
):
    q = db.query(models.Order)
    if status:
        q = q.filter(models.Order.status == status)
    # parse ISO timestamps if provided
    if from_:
        try:
            dt_from = datetime.fromisoformat(from_)
            q = q.filter(models.Order.created_at >= dt_from)
        except Exception:
            pass
    if to:
        try:
            dt_to = datetime.fromisoformat(to)
            q = q.filter(models.Order.created_at <= dt_to)
        except Exception:
            pass
    q = q.order_by(models.Order.created_at.desc())
    orders = q.all()
    for o in orders:
        _ = o.items
    return orders


@router.get("/{order_id}", response_model=OrderOut)
def get_order_admin(order_id: int, db: Session = Depends(get_db), _: models.User = Depends(require_admin)):
    order = db.get(models.Order, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    _ = order.items
    return order


ALLOWED_STATUSES = {"NEW", "COOKING", "ON_WAY", "DELIVERED", "CANCELLED"}


@router.put("/{order_id}/status", response_model=OrderOut)
def update_order_status(order_id: int, payload: StatusUpdateRequest, db: Session = Depends(get_db), _: models.User = Depends(require_admin)):
    if payload.status not in ALLOWED_STATUSES:
        raise HTTPException(status_code=400, detail="Invalid status")
    order = db.get(models.Order, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    old_status = order.status
    order.status = payload.status
    db.add(order)
    db.commit()
    db.refresh(order)
    _ = order.items
    
    # send notifications to customer about status change
    if old_status != payload.status and order.user:
        status_messages = {
            "NEW": "принят",
            "COOKING": "готовится",
            "ON_WAY": "в пути",
            "DELIVERED": "доставлен",
            "CANCELLED": "отменен"
        }
        
        status_text = status_messages.get(payload.status, payload.status)
        title = "Статус заказа изменен"
        body = f"Заказ #{order.number} {status_text}"
        
        # send push notifications to all user's devices
        for device in order.user.devices:
            try:
                send_to_token(device.fcm_token, title=title, body=body, data={
                    "order_id": str(order.id),
                    "order_number": order.number,
                    "status": payload.status,
                    "type": "order_status_update"
                })
            except Exception as e:
                # log error but don't fail the request
                print(f"Failed to send push notification to device {device.id}: {e}")
        
        # send email notifications (best-effort)
        if order.user.email:
            try:
                if payload.status == "DELIVERED":
                    # special email for delivered orders with rating request
                    send_order_delivered(to=order.user.email, order=order, user_id=order.user.id)
                else:
                    # general status update email
                    send_order_status(to=order.user.email, order=order, status=status_text, user_id=order.user.id)
            except Exception as e:
                # log error but don't fail the request
                print(f"Failed to send email notification: {e}")
    
    return order


@router.put("/{order_id}", response_model=OrderOut)
def update_order(order_id: int, payload: OrderUpdate, db: Session = Depends(get_db), _: models.User = Depends(require_admin)):
    """full order update (Admin only)"""
    order = db.get(models.Order, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    # update fields if provided
    old_status = order.status
    if payload.status is not None:
        if payload.status not in ALLOWED_STATUSES:
            raise HTTPException(status_code=400, detail="Invalid status")
        order.status = payload.status
    
    if payload.pickup_or_delivery is not None:
        if payload.pickup_or_delivery not in ["delivery", "pickup"]:
            raise HTTPException(status_code=400, detail="Invalid fulfillment method")
        order.pickup_or_delivery = payload.pickup_or_delivery
    
    if payload.address_text is not None:
        order.address_text = payload.address_text
    
    if payload.lat is not None:
        order.lat = payload.lat
    
    if payload.lng is not None:
        order.lng = payload.lng
    
    if payload.paid is not None:
        order.paid = payload.paid
    
    if payload.payment_method is not None:
        order.payment_method = payload.payment_method
    
    db.add(order)
    db.commit()
    db.refresh(order)
    _ = order.items
    
    # send notifications if status was changed
    if payload.status is not None and old_status != payload.status and order.user:
        status_messages = {
            "NEW": "принят",
            "COOKING": "готовится",
            "ON_WAY": "в пути",
            "DELIVERED": "доставлен",
            "CANCELLED": "отменен"
        }
        
        status_text = status_messages.get(payload.status, payload.status)
        title = "Статус заказа изменен"
        body = f"Заказ #{order.number} {status_text}"
        
        # send push notifications to all user's devices
        for device in order.user.devices:
            try:
                send_to_token(device.fcm_token, title=title, body=body, data={
                    "order_id": str(order.id),
                    "order_number": order.number,
                    "status": payload.status,
                    "type": "order_status_update"
                })
            except Exception as e:
                # log error but don't fail the request
                print(f"Failed to send push notification to device {device.id}: {e}")
        
        # send email notifications (best-effort)
        if order.user.email:
            try:
                if payload.status == "DELIVERED":
                    # special email for delivered orders with rating request
                    send_order_delivered(to=order.user.email, order=order, user_id=order.user.id)
                else:
                    # general status update email
                    send_order_status(to=order.user.email, order=order, status=status_text, user_id=order.user.id)
            except Exception as e:
                # log error but don't fail the request
                print(f"Failed to send email notification: {e}")
    
    return order


@router.delete("/{order_id}")
def delete_order(order_id: int, db: Session = Depends(get_db), _: models.User = Depends(require_admin)):
    """delete an order (Admin only)"""
    order = db.get(models.Order, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    # delete related order items and their modifications first
    for item in order.items:
        # delete order item modifications
        db.query(models.OrderItemModification).filter(
            models.OrderItemModification.order_item_id == item.id
        ).delete()
    
    # delete order items
    db.query(models.OrderItem).filter(models.OrderItem.order_id == order_id).delete()
    
    # delete the order
    db.delete(order)
    db.commit()
    return {"message": "Order deleted successfully"}
