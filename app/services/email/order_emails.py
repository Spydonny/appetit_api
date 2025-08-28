from typing import Optional
from app.services.email.email_sender import send_email


def send_order_created(to: str, order, user_id: Optional[int] = None, pickup_or_delivery: str = "pickup", eta: str = "30 minutes", locale: str = "en"):
    """send order created email using new template system."""
    try:
        # build order URL (assuming frontend has order detail page)
        order_url = f"https://ium.app/orders/{order.id}"
        
        # use new email sender with order_created template
        result = send_email(
            template="order_created",
            to=to,
            variables={
                "order_id": order.number,
                "order_url": order_url,
                "pickup_or_delivery": pickup_or_delivery,
                "eta": eta
            },
            user_id=user_id,
            locale=locale
        )
        return result
    except Exception:
        # swallow errors in MVP
        return {"status": "skipped", "reason": "email_error"}


def send_order_status(to: str, order, status: str, eta: str = "15 minutes", user_id: Optional[int] = None, locale: str = "en"):
    """send order status update email."""
    try:
        result = send_email(
            template="order_status",
            to=to,
            variables={
                "order_id": order.number,
                "status": status,
                "eta": eta
            },
            user_id=user_id,
            locale=locale
        )
        return result
    except Exception:
        return {"status": "skipped", "reason": "email_error"}


def send_order_delivered(to: str, order, user_id: Optional[int] = None, locale: str = "en"):
    """send order delivered email with rating request."""
    try:
        # build rating URL (assuming frontend has rating page)
        rating_url = f"https://ium.app/orders/{order.id}/rate"
        
        result = send_email(
            template="order_delivered",
            to=to,
            variables={
                "order_id": order.number,
                "rating_url": rating_url
            },
            user_id=user_id,
            locale=locale
        )
        return result
    except Exception:
        return {"status": "skipped", "reason": "email_error"}
