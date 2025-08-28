from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import optional_oauth2_scheme, decode_token, create_access_token
from app.db.session import get_db
from app import models
from app.schemas.auth_phone import (
    PhoneStartRequest, PhoneStartResponse, PhoneVerifyResponse, 
    PhoneVerifyCodeRequest, PhoneLoginRequest
)
from app.schemas.auth import TokenResponse
from app.services.sms.twilio_sender import start_verification, check_verification, send_sms
from app.services.sms.otp_utils import format_phone_number

router = APIRouter(prefix="/auth/phone", tags=["auth"])


@router.post("/start", response_model=PhoneStartResponse)
def start_phone_verification(
    payload: PhoneStartRequest, 
    db: Session = Depends(get_db), 
    token: Optional[str] = Depends(optional_oauth2_scheme)
):
    """send OTP to phone number for verification using Twilio check API."""
    # determine target phone and user_id if available
    target_phone: Optional[str] = payload.phone
    user_id: Optional[int] = None
    
    if token:
        try:
            data = decode_token(token)
            uid = data.get("sub")
            if uid:
                u = db.get(models.User, int(uid))
                if u:
                    user_id = u.id
                    if target_phone is None:
                        target_phone = u.phone
        except Exception:
            # ignore invalid token for this optional flow
            pass
    
    if not target_phone:
        raise HTTPException(status_code=400, detail="Phone number is required")
    
    # format phone number
    formatted_phone = format_phone_number(target_phone)
    
    # start verification using Twilio check API
    result = start_verification(formatted_phone, channel="sms")
    
    # handle verification start result
    if result["status"] == "error":
        if result["reason"] == "twilio_api_error":
            raise HTTPException(status_code=400, detail=f"SMS verification failed: {result['error']}")
        elif result["reason"] == "missing_verify_service_sid":
            raise HTTPException(status_code=500, detail="SMS verification service not configured")
        else:
            raise HTTPException(status_code=500, detail="SMS verification service unavailable")
    elif result["status"] == "skipped":
        raise HTTPException(status_code=500, detail="SMS verification service not available")
    
    # optionally store a minimal record for tracking purposes (without storing codes)
    # this is useful for linking verified phone numbers to users later
    if user_id:
        # check if we already have a record for this user/phone combination
        existing_pv = (
            db.query(models.PhoneVerification)
            .filter(
                models.PhoneVerification.user_id == user_id,
                models.PhoneVerification.phone == formatted_phone,
                models.PhoneVerification.used.is_(False)
            )
            .first()
        )
        if not existing_pv:
            # create a minimal tracking record (Twilio handles the actual verification)
            pv = models.PhoneVerification(
                user_id=user_id,
                phone=formatted_phone,
                token_hash="",  # Not needed with Twilio Verify
                code_hash="",   # Not needed with Twilio Verify
                expires_at=datetime.now(tz=timezone.utc),  # Not used with Twilio Verify
                used=False,
            )
            db.add(pv)
            db.commit()
    
    return PhoneStartResponse()


@router.post("/verify-code", response_model=PhoneVerifyResponse)
def verify_phone_code(payload: PhoneVerifyCodeRequest, db: Session = Depends(get_db)):
    """check OTP code for phone number using Twilio check API."""
    formatted_phone = format_phone_number(payload.phone)
    
    # use Twilio check API to check the code
    result = check_verification(formatted_phone, payload.code)
    
    # handle verification check result
    if result["status"] == "error":
        if result["reason"] == "twilio_api_error":
            raise HTTPException(status_code=400, detail=f"Code verification failed: {result['error']}")
        elif result["reason"] == "missing_verify_service_sid":
            raise HTTPException(status_code=500, detail="SMS verification service not configured")
        else:
            raise HTTPException(status_code=500, detail="Code verification service unavailable")
    elif result["status"] == "skipped":
        raise HTTPException(status_code=500, detail="Code verification service not available")
    
    # check if the verification was successful
    if not result.get("valid", False):
        raise HTTPException(status_code=400, detail="Invalid or expired code")
    
    # mark user phone as verified if user exists
    user = db.query(models.User).filter(models.User.phone == formatted_phone).first()
    if user:
        user.is_phone_verified = True
        db.add(user)
        db.commit()
    
    # mark any existing tracking records as used
    existing_pv = (
        db.query(models.PhoneVerification)
        .filter(
            models.PhoneVerification.phone == formatted_phone,
            models.PhoneVerification.used.is_(False)
        )
        .first()
    )
    if existing_pv:
        existing_pv.used = True
        db.add(existing_pv)
        db.commit()
    
    return PhoneVerifyResponse()


@router.post("/login", response_model=TokenResponse)
def login_with_phone_otp(payload: PhoneLoginRequest, db: Session = Depends(get_db)):
    """login using phone number and OTP code via Twilio check API."""
    formatted_phone = format_phone_number(payload.phone)
    
    # use Twilio check API to check the code
    result = check_verification(formatted_phone, payload.code)
    
    # handle verification check result
    if result["status"] == "error":
        if result["reason"] == "twilio_api_error":
            raise HTTPException(status_code=400, detail=f"Code verification failed: {result['error']}")
        elif result["reason"] == "missing_verify_service_sid":
            raise HTTPException(status_code=500, detail="SMS verification service not configured")
        else:
            raise HTTPException(status_code=500, detail="Code verification service unavailable")
    elif result["status"] == "skipped":
        raise HTTPException(status_code=500, detail="Code verification service not available")
    
    # check if the verification was successful
    if not result.get("valid", False):
        raise HTTPException(status_code=400, detail="Invalid or expired code")
    
    # find user by phone number
    user = db.query(models.User).filter(models.User.phone == formatted_phone).first()
    if not user:
        raise HTTPException(status_code=404, detail="No account found with this phone number")
    
    # mark user phone as verified
    user.is_phone_verified = True
    db.add(user)
    
    # mark any existing tracking records as used
    existing_pv = (
        db.query(models.PhoneVerification)
        .filter(
            models.PhoneVerification.phone == formatted_phone,
            models.PhoneVerification.used.is_(False)
        )
        .first()
    )
    if existing_pv:
        existing_pv.used = True
        db.add(existing_pv)
    
    db.commit()
    
    # generate access token
    token = create_access_token(subject=str(user.id), role=user.role)
    return TokenResponse(access_token=token, user=user)