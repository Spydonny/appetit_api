import os
from typing import Optional, Dict, Any

import httpx

GA_ENDPOINT = "https://www.google-analytics.com/mp/collect"


def health_check() -> Dict[str, str]:
    """check GA4 Analytics integration health and config status."""
    measurement_id = os.getenv("GA4_MEASUREMENT_ID")
    api_secret = os.getenv("GA4_API_SECRET")
    
    if not measurement_id:
        return {"status": "misconfigured", "reason": "missing_measurement_id"}
    if not api_secret:
        return {"status": "misconfigured", "reason": "missing_api_secret"}
    
    # basic validation - measurement ID should start with G-
    if not measurement_id.startswith("G-"):
        return {"status": "misconfigured", "reason": "invalid_measurement_id_format"}
    
    return {"status": "configured", "measurement_id": measurement_id}


def send_event(name: str, client_id: str, params: Optional[Dict[str, Any]] = None):
    measurement_id = os.getenv("GA4_MEASUREMENT_ID")
    api_secret = os.getenv("GA4_API_SECRET")
    if not measurement_id or not api_secret:
        return {"status": "skipped", "reason": "ga4_not_configured"}
    payload = {
        "client_id": client_id,
        "events": [
            {
                "name": name,
                "params": params or {},
            }
        ],
    }
    try:
        r = httpx.post(
            GA_ENDPOINT,
            params={"measurement_id": measurement_id, "api_secret": api_secret},
            json=payload,
            timeout=5.0,
        )
        return {"status": "sent", "code": r.status_code}
    except Exception:
        return {"status": "skipped", "reason": "request_failed"}
