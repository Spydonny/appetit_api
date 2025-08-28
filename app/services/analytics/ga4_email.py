import hashlib
import httpx
from typing import Dict, Any, Optional
from app.core.config import settings


GA4_MEASUREMENT_ID = settings.GA4_MEASUREMENT_ID
GA4_API_SECRET = settings.GA4_API_SECRET
GA4_ENDPOINT = "https://www.google-analytics.com/mp/collect"


def _hash_email(email: str) -> str:
    """create deterministic client_id from email for GA4."""
    if not email:
        return "anonymous"
    return hashlib.sha256(email.encode()).hexdigest()


def _map_event_type_to_ga4(event_type: str) -> Optional[str]:
    """map Resend event types to GA4 event names."""
    mapping = {
        "email.sent": "email_sent",
        "email.delivered": "email_delivered", 
        "email.opened": "email_opened",
        "email.clicked": "email_clicked",
        "email.bounced": "email_bounced",
        "email.complained": "email_complained",
        "email.delivery_delayed": "email_delayed"
    }
    return mapping.get(event_type)


async def forward_email_event_to_ga4(
    event_type: str,
    recipient: Optional[str] = None,
    email_id: Optional[str] = None,
    template: Optional[str] = None,
    link: Optional[str] = None,
    meta: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Forward email event to GA4 using Measurement Protocol v2.
    
    Args:
        event_type: Resend event type (email.opened, email.clicked, etc.)
        recipient: Email recipient for client_id generation
        email_id: Resend email ID
        template: Email template name
        link: Clicked link (for click events)
        meta: Additional metadata
        
    Returns:
        Dict with status and details
    """
    if not GA4_MEASUREMENT_ID or not GA4_API_SECRET:
        return {"status": "skipped", "reason": "ga4_not_configured"}
    
    ga4_event_name = _map_event_type_to_ga4(event_type)
    if not ga4_event_name:
        return {"status": "skipped", "reason": "unsupported_event_type"}
    
    # generate deterministic client_id from recipient email
    client_id = _hash_email(recipient or "")
    
    # build event params
    event_params = {}
    
    if template:
        event_params["template"] = template
    if email_id:
        event_params["email_id"] = email_id
    if link:
        event_params["link"] = link
    
    # add metadata as custom params
    if meta and isinstance(meta, dict):
        tags = meta.get("tags", {})
        if isinstance(tags, dict):
            # add template from tags if not already set
            if not template and "category" in tags:
                event_params["template"] = tags["category"]
            if "user_id" in tags:
                event_params["user_id"] = tags["user_id"]
    
    # build GA4 payload
    payload = {
        "client_id": client_id,
        "events": [{
            "name": ga4_event_name,
            "params": event_params
        }]
    }
    
    # send to GA4
    try:
        url = f"{GA4_ENDPOINT}?measurement_id={GA4_MEASUREMENT_ID}&api_secret={GA4_API_SECRET}"
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=5.0
            )
        
        if response.status_code == 204:
            return {
                "status": "sent",
                "event_name": ga4_event_name,
                "client_id": client_id,
                "params": event_params
            }
        else:
            return {
                "status": "error",
                "reason": "ga4_request_failed",
                "status_code": response.status_code,
                "response": response.text
            }
            
    except Exception as e:
        return {
            "status": "error",
            "reason": "network_error",
            "error": str(e)
        }


def health_check() -> Dict[str, Any]:
    """check GA4 integration health."""
    return {
        "status": "configured" if GA4_MEASUREMENT_ID and GA4_API_SECRET else "not_configured",
        "measurement_id_configured": bool(GA4_MEASUREMENT_ID),
        "api_secret_configured": bool(GA4_API_SECRET),
        "endpoint": GA4_ENDPOINT
    }