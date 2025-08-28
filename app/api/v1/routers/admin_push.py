from typing import List
import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from app.core.security import require_admin
from app.db.session import get_db
from app import models
from app.schemas.admin import AdminPushRequest, AdminPushResponse, AdminSmsRequest, AdminSmsResponse, PushResult
from app.services.push.fcm_admin import send_to_token, send_batch, send_to_topic
from app.services.sms.twilio_sender import send_sms

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin/push", tags=["admin"])


def _get_targeted_tokens(db: Session, targeting) -> tuple[List[str], str]:
    """get FCM tokens based on targeting criteria."""
    query = db.query(models.Device).filter(models.Device.fcm_token.is_not(None))
    targeting_method = f"audience:{targeting.audience}"
    
    # base query - all devices with FCM tokens
    if targeting.audience == "all":
        pass  # No additional filtering
    
    elif targeting.audience == "platform":
        if not targeting.platform:
            raise HTTPException(status_code=400, detail="Platform required for platform targeting")
        query = query.filter(models.Device.platform == targeting.platform)
        targeting_method += f",platform:{targeting.platform}"
    
    elif targeting.audience == "verified_users":
        # join with users table to filter verified users
        query = query.join(models.User).filter(
            or_(
                models.User.is_email_verified == True,
                models.User.is_phone_verified == True
            )
        )
        targeting_method += ",verified_only"
    
    elif targeting.audience == "role":
        if not targeting.user_role:
            raise HTTPException(status_code=400, detail="User role required for role targeting")
        query = query.join(models.User).filter(models.User.role == targeting.user_role)
        targeting_method += f",role:{targeting.user_role}"
    
    elif targeting.audience == "topic":
        # for topic messaging, we don't need individual tokens
        return [], f"topic:{targeting.topic}"
    
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported audience: {targeting.audience}")
    
    # apply additional filters
    if targeting.verified_only and targeting.audience not in ["verified_users"]:
        if models.User not in [mapper.class_ for mapper in query.column_descriptions]:
            query = query.join(models.User)
        query = query.filter(
            or_(
                models.User.is_email_verified == True,
                models.User.is_phone_verified == True
            )
        )
        targeting_method += ",verified_only"
    
    if targeting.platform and targeting.audience != "platform":
        query = query.filter(models.Device.platform == targeting.platform)
        targeting_method += f",platform:{targeting.platform}"
    
    # apply limit if specified
    if targeting.max_devices:
        query = query.limit(targeting.max_devices)
        targeting_method += f",limit:{targeting.max_devices}"
    
    devices = query.all()
    tokens = [device.fcm_token for device in devices if device.fcm_token]
    
    return tokens, targeting_method


@router.post("/send", response_model=AdminPushResponse)
def send_push(req: AdminPushRequest, db: Session = Depends(get_db), _: models.User = Depends(require_admin)):
    """
    Send push notifications with advanced targeting capabilities.
    
    Supports multiple targeting methods:
    - all: Send to all devices
    - platform: Target specific platform (android, ios, web)
    - verified_users: Target only verified users
    - role: Target users with specific role
    - topic: Send to topic subscribers
    """
    timestamp = datetime.utcnow().isoformat()
    
    try:
        # check priority
        if req.priority not in ["normal", "high"]:
            raise HTTPException(status_code=400, detail="Priority must be 'normal' or 'high'")
        
        # handle dry run
        if req.dry_run:
            if req.targeting.audience == "topic":
                if not req.targeting.topic:
                    raise HTTPException(status_code=400, detail="Topic required for topic messaging")
                return AdminPushResponse(
                    status="skipped",
                    sent=0,
                    failed=0,
                    total=0,
                    targeting_method=f"topic:{req.targeting.topic}",
                    timestamp=timestamp,
                    reason="dry_run",
                    topic=req.targeting.topic
                )
            else:
                tokens, targeting_method = _get_targeted_tokens(db, req.targeting)
                return AdminPushResponse(
                    status="skipped",
                    sent=0,
                    failed=0,
                    total=len(tokens),
                    targeting_method=targeting_method,
                    timestamp=timestamp,
                    reason="dry_run"
                )
        
        # handle topic messaging
        if req.targeting.audience == "topic":
            if not req.targeting.topic:
                raise HTTPException(status_code=400, detail="Topic required for topic messaging")
            
            logger.info(f"Sending topic push notification to '{req.targeting.topic}'")
            result = send_to_topic(
                topic=req.targeting.topic,
                title=req.title,
                body=req.body,
                data=req.data,
                priority=req.priority,
                ttl=req.ttl
            )
            
            if result["status"] == "sent":
                return AdminPushResponse(
                    status="completed",
                    sent=1,  # Topic messages are counted as 1 successful send
                    failed=0,
                    total=1,
                    targeting_method=f"topic:{req.targeting.topic}",
                    timestamp=timestamp,
                    message_id=result["id"],
                    topic=req.targeting.topic
                )
            else:
                return AdminPushResponse(
                    status="error",
                    sent=0,
                    failed=1,
                    total=1,
                    targeting_method=f"topic:{req.targeting.topic}",
                    timestamp=timestamp,
                    topic=req.targeting.topic,
                    reason=result.get("reason", "unknown_error"),
                    errors=[result.get("error", "Unknown error")]
                )
        
        # handle token-based messaging
        tokens, targeting_method = _get_targeted_tokens(db, req.targeting)
        
        if not tokens:
            logger.warning(f"No devices found for targeting: {targeting_method}")
            return AdminPushResponse(
                status="completed",
                sent=0,
                failed=0,
                total=0,
                targeting_method=targeting_method,
                timestamp=timestamp,
                reason="no_devices_found"
            )
        
        logger.info(f"Sending push notifications to {len(tokens)} devices using {targeting_method}")
        
        # use batch sending for multiple tokens, individual sending for single token
        if len(tokens) == 1:
            result = send_to_token(
                token=tokens[0],
                title=req.title,
                body=req.body,
                data=req.data,
                priority=req.priority,
                ttl=req.ttl
            )
            
            if result["status"] == "sent":
                sent, failed = 1, 0
                results = [PushResult(token=tokens[0][:20] + "...", success=True, message_id=result["id"])]
            else:
                sent, failed = 0, 1
                results = [PushResult(token=tokens[0][:20] + "...", success=False, error=result.get("error", "Unknown error"))]
            
        else:
            result = send_batch(
                tokens=tokens,
                title=req.title,
                body=req.body,
                data=req.data,
                priority=req.priority,
                ttl=req.ttl
            )
            
            # map service-level response to API response format
            sent = result.get("success_count", result.get("sent", 0))
            failed = result.get("failure_count", result.get("failed", 0))
            # build results list limited to failed tokens for brevity
            results = []
            for ft in result.get("failed_tokens", []):
                results.append(PushResult(token=(ft.get("token") or '')[:20] + "...", success=False, error=ft.get("error")))
        
        # collect error reasons
        errors = []
        if "results" in result:
            for r in result["results"]:
                if not r.get("success", False) and r.get("error"):
                    errors.append(r["error"])
        
        return AdminPushResponse(
            status="completed" if result.get("status") in ["sent", "completed"] else "error",
            sent=sent,
            failed=failed,
            total=len(tokens),
            targeting_method=targeting_method,
            timestamp=timestamp,
            errors=list(set(errors)) if errors else None,
            results=results if len(results) <= 100 else results[:100]  # Limit results for large batches
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Push notification failed: {str(e)}")
        return AdminPushResponse(
            status="error",
            sent=0,
            failed=0,
            total=0,
            targeting_method="unknown",
            timestamp=timestamp,
            reason="internal_error",
            errors=[str(e)]
        )


@router.post("/send-sms", response_model=AdminSmsResponse)
def send_sms_broadcast(req: AdminSmsRequest, db: Session = Depends(get_db), _: models.User = Depends(require_admin)):
    """send SMS message to all users with verified phone numbers."""
    # currently only audience="all" is supported
    # get all users with verified phone numbers
    users_with_phones = db.query(models.User).filter(
        models.User.phone.is_not(None),
        models.User.is_phone_verified.is_(True)
    ).all()
    
    phone_numbers: List[str] = [user.phone for user in users_with_phones if user.phone]
    sent = 0
    
    for phone in phone_numbers:
        try:
            result = send_sms(phone, req.message)
            if isinstance(result, dict) and result.get("status") == "sent":
                sent += 1
        except Exception:
            # ignore individual failures in MVP
            pass
    
    return AdminSmsResponse(sent=sent)
