import os
from typing import Optional, Dict, Any
import httpx
from datetime import datetime

from .ga4_mp import GA_ENDPOINT

SUPPORTED_PLATFORMS = {"android", "ios", "web"}


def _env_key(platform: str, key: str) -> str:
    # platform-specific env names
    p = platform.upper()
    return f"GA4_{p}_{key}"


def get_stream_config(platform: str) -> Dict[str, Optional[str]]:
    """return measurement_id/api_secret for platform, plus validation info."""
    plat = (platform or "").lower()
    if plat not in SUPPORTED_PLATFORMS:
        return {"status": "invalid_platform", "platform": platform}
    mid = os.getenv(_env_key(plat, "MEASUREMENT_ID"))
    sec = os.getenv(_env_key(plat, "API_SECRET"))
    if not mid or not sec:
        return {
            "status": "misconfigured",
            "platform": plat,
            "reason": "missing_credentials",
            "measurement_id": mid,
        }
    if not mid.startswith("G-"):
        return {
            "status": "misconfigured",
            "platform": plat,
            "reason": "invalid_measurement_id_format",
            "measurement_id": mid,
        }
    return {"status": "configured", "platform": plat, "measurement_id": mid, "api_secret": sec}


def health_check_all() -> Dict[str, Any]:
    results: Dict[str, Any] = {}
    configured = 0
    for plat in sorted(SUPPORTED_PLATFORMS):
        cfg = get_stream_config(plat)
        results[plat] = cfg
        if cfg.get("status") == "configured":
            configured += 1
    results["summary"] = {
        "configured": configured,
        "total": len(SUPPORTED_PLATFORMS),
        "all_ready": configured == len(SUPPORTED_PLATFORMS),
    }
    return results


def send_platform_event(platform: str, name: str, client_id: Optional[str] = None, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Send a GA4 event to the specified platform stream using Measurement Protocol.
    If not configured, returns a structured 'skipped' response.
    """
    cfg = get_stream_config(platform)
    if cfg.get("status") != "configured":
        return {"status": "skipped", "platform": platform, "reason": cfg.get("reason", cfg.get("status"))}

    measurement_id = cfg["measurement_id"]
    api_secret = cfg["api_secret"]

    payload = {
        "client_id": client_id or "anonymous",
        "events": [
            {
                "name": name,
                "params": {
                    **(params or {}),
                    "platform": cfg["platform"],
                    "sent_at": datetime.utcnow().isoformat() + "Z",
                },
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
        return {"status": "sent" if r.status_code in (204, 200) else "queued", "code": r.status_code, "platform": cfg["platform"]}
    except Exception as e:
        return {"status": "skipped", "platform": cfg.get("platform", platform), "reason": "request_failed", "error": str(e)}
