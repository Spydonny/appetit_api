import os
import json
import hashlib
from typing import Dict, Any
from datetime import datetime

from fastapi import APIRouter, Request, HTTPException, BackgroundTasks, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text

try:
    from svix.webhooks import Webhook, WebhookVerificationError  # type: ignore
except ImportError:  # pragma: no cover
    Webhook = None
    WebhookVerificationError = Exception

from app.db.session import get_db
from app.services.analytics.ga4_email import forward_email_event_to_ga4

router = APIRouter(prefix="/webhooks", tags=["webhooks"])

RESEND_WEBHOOK_SECRET = os.environ.get("RESEND_WEBHOOK_SECRET")


@router.post("/resend")
async def resend_webhook(request: Request, background: BackgroundTasks, db: Session = Depends(get_db)):
    """
    Handle webhooks from Resend for email lifecycle events.
    
    Supported events: email.sent, email.delivered, email.opened, email.clicked,
    email.bounced, email.complained, email.delivery_delayed
    """
    if not RESEND_WEBHOOK_SECRET:
        raise HTTPException(status_code=500, detail="Webhook secret not configured")
    
    if Webhook is None:
        raise HTTPException(status_code=500, detail="Svix not installed")
    
    # 1) Read raw body (don't call request.json())
    payload_bytes = await request.body()
    
    # 2) Collect Svix headers
    headers = {
        "svix-id": request.headers.get("svix-id"),
        "svix-timestamp": request.headers.get("svix-timestamp"),
        "svix-signature": request.headers.get("svix-signature"),
    }
    if not all(headers.values()):
        raise HTTPException(status_code=400, detail="Missing Svix headers")
    
    # 3) check signature (5-minute tolerance)
    wh = Webhook(RESEND_WEBHOOK_SECRET)
    try:
        event = wh.verify(payload_bytes, headers, tolerance=300)
    except WebhookVerificationError:
        raise HTTPException(status_code=400, detail="Invalid signature")
    
    # 4) Enqueue for async processing (avoid timeouts)
    background.add_task(process_resend_event, event, db)
    return {"ok": True}


async def process_resend_event(event: Dict[str, Any], db: Session):
    """
    Process a verified Resend webhook event.
    
    Store event in email_events table with idempotency using svix-id.
    """
    try:
        event_type = event.get("type")
        created_at = event.get("created_at")
        data = event.get("data", {})
        
        # extract common fields
        email_id = data.get("email_id")
        to_list = data.get("to", [])
        recipient = to_list[0] if to_list else None
        subject = data.get("subject")
        
        # extract event-specific fields
        link = None
        meta = {}
        
        if event_type == "email.clicked":
            click_data = data.get("click", {})
            link = click_data.get("link")
            meta = {
                "timestamp": click_data.get("timestamp"),
                "ip_address": click_data.get("ipAddress"),
                "user_agent": click_data.get("userAgent")
            }
        elif event_type == "email.opened":
            open_data = data.get("open", {})
            meta = {
                "timestamp": open_data.get("timestamp"),
                "ip_address": open_data.get("ipAddress"),
                "user_agent": open_data.get("userAgent")
            }
        elif event_type == "email.bounced":
            bounce_data = data.get("bounce", {})
            meta = {
                "reason": bounce_data.get("reason"),
                "smtp_code": bounce_data.get("smtpCode")
            }
        elif event_type == "email.complained":
            complaint_data = data.get("complaint", {})
            meta = {
                "provider": complaint_data.get("provider"),
                "timestamp": complaint_data.get("timestamp")
            }
        elif event_type == "email.delivery_delayed":
            delay_data = data.get("delay", {})
            meta = {
                "reason": delay_data.get("reason"),
                "attempts": delay_data.get("attempts")
            }
        
        # add tags to meta if present
        tags = data.get("tags", {})
        if tags:
            meta["tags"] = tags
        
        # generate svix_id for idempotency (use actual svix-id if available)
        svix_id = event.get("id") or _generate_event_id(event)
        
        # insert into email_events table with idempotency
        insert_sql = text("""
            INSERT INTO email_events (svix_id, type, email_id, recipient, subject, link, meta, created_at)
            VALUES (:svix_id, :type, :email_id, :recipient, :subject, :link, :meta, :created_at)
            ON CONFLICT (svix_id) DO NOTHING
        """)
        
        db.execute(insert_sql, {
            "svix_id": svix_id,
            "type": event_type,
            "email_id": email_id,
            "recipient": recipient,
            "subject": subject,
            "link": link,
            "meta": json.dumps(meta) if meta else None,
            "created_at": datetime.fromisoformat(created_at.replace('Z', '+00:00')) if created_at else datetime.utcnow()
        })
        
        db.commit()
        
        # forward to GA4 for relevant events
        if event_type in ["email.opened", "email.clicked", "email.bounced", "email.complained"]:
            # extract template from tags
            template = None
            if tags and "category" in tags:
                template = tags["category"]
            
            # forward to GA4 in background (non-blocking)
            try:
                import asyncio
                asyncio.create_task(forward_email_event_to_ga4(
                    event_type=event_type,
                    recipient=recipient,
                    email_id=email_id,
                    template=template,
                    link=link,
                    meta=meta
                ))
            except Exception as e:
                print(f"Error forwarding to GA4: {e}")
        
    except Exception as e:
        # log error but don't raise to avoid webhook retries
        print(f"Error processing Resend event: {e}")
        db.rollback()


def _generate_event_id(event: Dict[str, Any]) -> str:
    """generate a deterministic event ID for idempotency."""
    event_string = json.dumps(event, sort_keys=True)
    return hashlib.sha256(event_string.encode()).hexdigest()


@router.get("/resend/health")
async def webhook_health():
    """health check for webhook endpoint."""
    return {
        "status": "ok",
        "webhook_secret_configured": bool(RESEND_WEBHOOK_SECRET),
        "svix_available": Webhook is not None
    }