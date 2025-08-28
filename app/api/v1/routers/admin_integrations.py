from fastapi import APIRouter, Depends, Query
from typing import Optional
from app.core.security import require_admin
from app import models

router = APIRouter(prefix="/admin/integrations", tags=["admin"])


@router.get("/status")
def get_integrations_status(_: models.User = Depends(require_admin)):
    """get status of all integrations for admin monitoring."""
    from app.services.email.email_sender import health_check as email_health
    from app.services.push.fcm_admin import health_check as push_health
    from app.services.sms.twilio_sender import health_check as sms_health
    from app.services.maps.google import health_check as maps_health
    from app.services.analytics.ga4_mp import health_check as ga4_health
    from app.services.analytics.ga4_streams import health_check_all as ga4_streams_health
    from app.services.analytics.ga4_data import health_check as ga4_data_health
    from app.services.pos.factory import get_pos_adapter
    from app.services.payments.mock import MockPayments
    
    # get health status for each integration
    status = {
        "email": email_health(),
        "push": push_health(),
        "sms": sms_health(),
        "maps": maps_health(),
        "analytics": ga4_health(),
        "analytics_streams": ga4_streams_health(),
        "analytics_data": ga4_data_health(),
        "pos": {
            "status": "configured",
            "provider": "mock",
            "note": "Using mock POS adapter"
        },
        "payments": {
            "status": "configured", 
            "provider": "mock",
            "note": "Using mock payment provider"
        }
    }
    
    # add overall summary
    configured_count = sum(1 for service in status.values() if isinstance(service, dict) and service.get("status") == "configured")
    total_count = len(status)
    
    return {
        "summary": {
            "configured": configured_count,
            "total": total_count,
            "all_ready": configured_count == total_count
        },
        "services": status
    }


@router.get("/ga4/health")
def ga4_health(_: models.User = Depends(require_admin)):
    """return health status for GA4 streams (android, ios, web)."""
    from app.services.analytics.ga4_streams import health_check_all
    return health_check_all()


@router.post("/ga4/test-event")
def ga4_test_event(
    platform: Optional[str] = Query("all", description="android|ios|web|all"),
    event_name: str = Query("test_event"),
    client_id: Optional[str] = Query(None),
    _: models.User = Depends(require_admin),
):
    """send a GA4 test event to a specific platform stream or all streams."""
    from datetime import datetime
    from app.services.analytics.ga4_streams import send_platform_event, SUPPORTED_PLATFORMS

    plat = (platform or "all").lower()
    sent_at = datetime.utcnow().isoformat() + "Z"

    if plat == "all":
        results = {
            p: send_platform_event(p, event_name, client_id=client_id or f"admin-test-{p}", params={"source": "admin"})
            for p in sorted(SUPPORTED_PLATFORMS)
        }
        return {"status": "ok", "sent_at": sent_at, "results": results}

    if plat not in SUPPORTED_PLATFORMS:
        return {"status": "error", "reason": "invalid_platform", "supported": sorted(SUPPORTED_PLATFORMS)}

    result = send_platform_event(plat, event_name, client_id=client_id or f"admin-test-{plat}", params={"source": "admin"})
    return {"status": "ok", "sent_at": sent_at, "platform": plat, "result": result}


@router.get("/ga4-data/health")
def ga4_data_health(_: models.User = Depends(require_admin)):
    """Check GA4 Data API health and configuration."""
    from app.services.analytics.ga4_data import health_check
    return health_check()


@router.get("/ga4-data/sessions")
def ga4_data_sessions(
    start_date: str = Query("30daysAgo", description="Start date (e.g., '30daysAgo', '2023-01-01')"),
    end_date: str = Query("yesterday", description="End date (e.g., 'yesterday', '2023-01-31')"),
    _: models.User = Depends(require_admin),
):
    """Get sessions and users data from GA4."""
    from app.services.analytics.ga4_data import get_sessions_and_users
    return get_sessions_and_users(start_date, end_date)


@router.get("/ga4-data/traffic-sources")
def ga4_data_traffic_sources(
    start_date: str = Query("30daysAgo", description="Start date (e.g., '30daysAgo', '2023-01-01')"),
    end_date: str = Query("yesterday", description="End date (e.g., 'yesterday', '2023-01-31')"),
    limit: int = Query(10, description="Maximum number of sources to return"),
    _: models.User = Depends(require_admin),
):
    """Get traffic sources data from GA4."""
    from app.services.analytics.ga4_data import get_traffic_sources
    return get_traffic_sources(start_date, end_date, limit)


@router.get("/ga4-data/events")
def ga4_data_events(
    start_date: str = Query("30daysAgo", description="Start date (e.g., '30daysAgo', '2023-01-01')"),
    end_date: str = Query("yesterday", description="End date (e.g., 'yesterday', '2023-01-31')"),
    limit: int = Query(20, description="Maximum number of events to return"),
    _: models.User = Depends(require_admin),
):
    """Get events data from GA4."""
    from app.services.analytics.ga4_data import get_events_data
    return get_events_data(start_date, end_date, limit)


@router.get("/ga4-data/devices")
def ga4_data_devices(
    start_date: str = Query("30daysAgo", description="Start date (e.g., '30daysAgo', '2023-01-01')"),
    end_date: str = Query("yesterday", description="End date (e.g., 'yesterday', '2023-01-31')"),
    _: models.User = Depends(require_admin),
):
    """Get device and platform analytics from GA4."""
    from app.services.analytics.ga4_data import get_device_analytics
    return get_device_analytics(start_date, end_date)
