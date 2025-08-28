from typing import List, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from app.core.security import require_courier
from app.db.session import get_db
from app import models
from app.schemas.orders import OrderOut, OrderStatusUpdate

router = APIRouter(prefix="/courier", tags=["courier"])

# =======================
# ORDER MANAGEMENT
# =======================

@router.get("/orders", response_model=List[OrderOut])
def list_orders(
    status: Optional[str] = Query(None, description="Filter by order status: NEW, COOKING, ON_WAY, DELIVERED, CANCELLED"),
    pickup_or_delivery: Optional[str] = Query(None, description="Filter by fulfillment type: delivery, pickup"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    _: models.User = Depends(require_courier),
):
    """List orders for courier - focus on delivery orders and active statuses"""
    query = db.query(models.Order)
    
    # Filter by status if provided
    if status:
        if status not in ["NEW", "COOKING", "ON_WAY", "DELIVERED", "CANCELLED"]:
            raise HTTPException(status_code=400, detail="Invalid status. Must be one of: NEW, COOKING, ON_WAY, DELIVERED, CANCELLED")
        query = query.filter(models.Order.status == status)
    else:
        # Default: show active orders that need courier attention
        query = query.filter(models.Order.status.in_(["NEW", "COOKING", "ON_WAY"]))
    
    # Filter by fulfillment type
    if pickup_or_delivery:
        if pickup_or_delivery not in ["delivery", "pickup"]:
            raise HTTPException(status_code=400, detail="Invalid fulfillment. Must be 'delivery' or 'pickup'")
        query = query.filter(models.Order.pickup_or_delivery == pickup_or_delivery)
    else:
        # Default: focus on delivery orders which couriers handle
        query = query.filter(models.Order.pickup_or_delivery == "delivery")
    
    # Order by creation time (newest first for active orders)
    if not status or status in ["NEW", "COOKING", "ON_WAY"]:
        query = query.order_by(models.Order.created_at.desc())
    else:
        query = query.order_by(models.Order.updated_at.desc())
    
    orders = query.offset(offset).limit(limit).all()
    return orders


@router.get("/orders/today")
def get_today_orders(
    status: Optional[str] = Query(None, description="Filter by status"),
    db: Session = Depends(get_db),
    _: models.User = Depends(require_courier),
):
    """Get today's orders for courier dashboard"""
    from datetime import date, datetime, time
    
    today = date.today()
    # Convert date to datetime range for proper SQLAlchemy comparison
    today_start = datetime.combine(today, time.min)  # 00:00:00
    today_end = datetime.combine(today, time.max)    # 23:59:59.999999
    
    query = db.query(models.Order).filter(
        models.Order.created_at >= today_start,
        models.Order.created_at <= today_end,
        models.Order.pickup_or_delivery == "delivery"  # Focus on delivery orders
    )
    
    if status:
        query = query.filter(models.Order.status == status)
    
    orders = query.order_by(models.Order.created_at.desc()).all()
    
    # Aggregate statistics
    total_orders = len(orders)
    status_counts = {}
    for order in orders:
        status_counts[order.status] = status_counts.get(order.status, 0) + 1
    
    return {
        "date": today.isoformat(),
        "total_orders": total_orders,
        "status_breakdown": status_counts,
        "orders": orders
    }


@router.get("/orders/{order_id}", response_model=OrderOut)
def get_order(
    order_id: int,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_courier),
):
    """Get specific order details for courier"""
    order = db.get(models.Order, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order


@router.patch("/orders/{order_id}/status")
def update_order_status(
    order_id: int,
    status_update: OrderStatusUpdate,
    db: Session = Depends(get_db),
    courier: models.User = Depends(require_courier),
):
    """Update order status - couriers can change status for delivery workflow"""
    order = db.get(models.Order, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    new_status = status_update.status
    
    # Validate status transitions for couriers
    valid_courier_statuses = ["COOKING", "ON_WAY", "DELIVERED", "CANCELLED"]
    if new_status not in valid_courier_statuses:
        raise HTTPException(status_code=400, detail=f"Invalid status. Couriers can only set: {', '.join(valid_courier_statuses)}")
    
    # Business logic for status transitions
    current_status = order.status
    
    # Define valid transitions
    valid_transitions = {
        "NEW": ["COOKING", "CANCELLED"],
        "COOKING": ["ON_WAY", "CANCELLED"],
        "ON_WAY": ["DELIVERED", "CANCELLED"],
        "DELIVERED": [],  # Final state
        "CANCELLED": []   # Final state
    }
    
    if new_status not in valid_transitions.get(current_status, []):
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid status transition from {current_status} to {new_status}"
        )
    
    # Update order status
    order.status = new_status
    order.updated_at = datetime.utcnow()
    
    db.add(order)
    db.commit()
    db.refresh(order)
    
    return {
        "message": f"Order {order.number} status updated to {new_status}",
        "order_id": order.id,
        "order_number": order.number,
        "previous_status": current_status,
        "new_status": new_status,
        "updated_by": courier.full_name,
        "updated_at": order.updated_at
    }


@router.get("/orders/assigned")
def get_assigned_orders(
    db: Session = Depends(get_db),
    courier: models.User = Depends(require_courier),
):
    """Get orders currently assigned to this courier (if assignment system exists)"""
    # Note: This is a placeholder for future courier assignment functionality
    # For now, show active delivery orders
    
    query = db.query(models.Order).filter(
        models.Order.status.in_(["COOKING", "ON_WAY"]),
        models.Order.pickup_or_delivery == "delivery"
    )
    
    orders = query.order_by(models.Order.created_at.asc()).all()
    
    return {
        "courier_id": courier.id,
        "courier_name": courier.full_name,
        "assigned_orders_count": len(orders),
        "orders": orders
    }


# =======================
# DELIVERY ADDRESSES & ROUTES
# =======================

@router.get("/addresses/delivery-zone")
def get_delivery_addresses(
    status: Optional[str] = Query("ON_WAY", description="Order status to filter addresses"),
    db: Session = Depends(get_db),
    _: models.User = Depends(require_courier),
):
    """Get delivery addresses for orders in specified status"""
    query = db.query(models.Order).filter(
        models.Order.pickup_or_delivery == "delivery",
        models.Order.address_text.isnot(None)  # Only orders with addresses
    )
    
    if status:
        query = query.filter(models.Order.status == status)
    else:
        query = query.filter(models.Order.status.in_(["COOKING", "ON_WAY"]))
    
    orders = query.order_by(models.Order.created_at.asc()).all()
    
    addresses = []
    for order in orders:
        addresses.append({
            "order_id": order.id,
            "order_number": order.number,
            "status": order.status,
            "address": order.address_text,
            "lat": order.lat,
            "lng": order.lng,
            "phone": order.phone,
            "created_at": order.created_at,
            "estimated_time": None  # Placeholder for route optimization
        })
    
    return {
        "total_deliveries": len(addresses),
        "status_filter": status,
        "addresses": addresses
    }


# =======================
# COURIER ANALYTICS & STATS
# =======================

@router.get("/stats/daily")
def get_daily_stats(
    date: Optional[str] = Query(None, description="Date in YYYY-MM-DD format, defaults to today"),
    db: Session = Depends(get_db),
    courier: models.User = Depends(require_courier),
):
    """Get daily statistics for courier performance"""
    from datetime import date as date_type, datetime
    
    if date:
        try:
            target_date = datetime.fromisoformat(date).date()
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
    else:
        target_date = date_type.today()
    
    # Query orders for the target date
    start_datetime = datetime.combine(target_date, datetime.min.time())
    end_datetime = datetime.combine(target_date, datetime.max.time())
    
    orders = db.query(models.Order).filter(
        models.Order.created_at >= start_datetime,
        models.Order.created_at <= end_datetime,
        models.Order.pickup_or_delivery == "delivery"
    ).all()
    
    # Calculate statistics
    total_orders = len(orders)
    delivered_orders = len([o for o in orders if o.status == "DELIVERED"])
    cancelled_orders = len([o for o in orders if o.status == "CANCELLED"])
    in_progress_orders = len([o for o in orders if o.status in ["NEW", "COOKING", "ON_WAY"]])
    
    total_revenue = sum(float(order.total) for order in orders if order.status == "DELIVERED")
    avg_order_value = total_revenue / delivered_orders if delivered_orders > 0 else 0
    
    # Status breakdown
    status_counts = {}
    for order in orders:
        status_counts[order.status] = status_counts.get(order.status, 0) + 1
    
    delivery_rate = (delivered_orders / total_orders * 100) if total_orders > 0 else 0
    
    return {
        "date": target_date.isoformat(),
        "courier_name": courier.full_name,
        "total_orders": total_orders,
        "delivered_orders": delivered_orders,
        "cancelled_orders": cancelled_orders,
        "in_progress_orders": in_progress_orders,
        "delivery_rate_percent": round(delivery_rate, 2),
        "total_revenue": round(total_revenue, 2),
        "avg_order_value": round(avg_order_value, 2),
        "status_breakdown": status_counts
    }