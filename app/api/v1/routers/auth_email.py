from datetime import datetime, timedelta, timezone
from uuid import uuid4
import hashlib
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app import models
from app.core.security import optional_oauth2_scheme, decode_token
from app.schemas.auth_email import EmailStartRequest, EmailStartResponse, EmailVerifyResponse, EmailVerifyCodeRequest
from app.services.email.email_sender import send_email

router = APIRouter(prefix="/auth/email", tags=["auth"])


def _sha256(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


@router.post("/start", response_model=EmailStartResponse)
def start_email_verification(payload: EmailStartRequest, db: Session = Depends(get_db), token: Optional[str] = Depends(optional_oauth2_scheme)):
    # determine target email and user_id if available
    target_email: Optional[str] = payload.email
    user_id: Optional[int] = None
    if token:
        try:
            data = decode_token(token)
            uid = data.get("sub")
            if uid:
                u = db.get(models.User, int(uid))
                if u:
                    user_id = u.id
                    if target_email is None:
                        target_email = u.email
        except Exception:
            # ignore invalid token for this optional flow
            pass
    if not target_email:
        raise HTTPException(status_code=400, detail="email is required")

    # generate token and code
    raw_token = uuid4().hex
    raw_code = f"{uuid4().int % 1000000:06d}"
    token_hash = _sha256(raw_token)
    code_hash = _sha256(raw_code)
    expires_at = datetime.now(tz=timezone.utc) + timedelta(minutes=settings.EMAIL_VERIFICATION_EXPIRES_MIN)

    ev = models.EmailVerification(
        user_id=user_id,
        email=target_email,
        token_hash=token_hash,
        code_hash=code_hash,
        expires_at=expires_at,
        used=False,
    )
    db.add(ev)
    db.commit()

    # send email (best-effort)
    try:
        verify_link = f"{settings.FRONTEND_URL}/verify-email?email={target_email}&token={raw_token}"
        
        # get user name if available
        user_name = "User"
        if user_id:
            try:
                user = db.get(models.User, user_id)
                if user and hasattr(user, 'name') and user.name:
                    user_name = user.name
                elif user and hasattr(user, 'email'):
                    # use email prefix as fallback
                    user_name = user.email.split('@')[0]
            except Exception:
                pass
        
        # use new email sender with verify_email template
        import asyncio
        result = asyncio.run(send_email(
            template="verify_email",
            to=target_email,
            variables={
                "user_name": user_name,
                "verify_url": verify_link,
                "otp": raw_code
            },
            user_id=user_id
        ))
    except Exception:
        pass

    return EmailStartResponse()


@router.get("/verify", response_model=EmailVerifyResponse)
def verify_email(email: str = Query(...), token: str = Query(...), db: Session = Depends(get_db)):
    token_hash = _sha256(token)
    now = datetime.now(tz=timezone.utc)
    ev = (
        db.query(models.EmailVerification)
        .filter(
            models.EmailVerification.email == email,
            models.EmailVerification.token_hash == token_hash,
            models.EmailVerification.used.is_(False),
            models.EmailVerification.expires_at > now,
        )
        .order_by(models.EmailVerification.created_at.desc())
        .first()
    )
    if not ev:
        raise HTTPException(status_code=400, detail="Invalid or expired token")

    # mark used
    ev.used = True
    db.add(ev)

    # mark user verified if matches any user
    user = db.query(models.User).filter(models.User.email == email).first()
    if user:
        user.is_email_verified = True
        db.add(user)

    db.commit()
    return EmailVerifyResponse()


@router.post("/verify-code", response_model=EmailVerifyResponse)
def verify_email_code(payload: EmailVerifyCodeRequest, db: Session = Depends(get_db)):
    now = datetime.now(tz=timezone.utc)
    code_hash = _sha256(payload.code)
    ev = (
        db.query(models.EmailVerification)
        .filter(
            models.EmailVerification.email == payload.email,
            models.EmailVerification.code_hash == code_hash,
            models.EmailVerification.used.is_(False),
            models.EmailVerification.expires_at > now,
        )
        .order_by(models.EmailVerification.created_at.desc())
        .first()
    )
    if not ev:
        raise HTTPException(status_code=400, detail="Invalid or expired code")

    ev.used = True
    db.add(ev)

    user = db.query(models.User).filter(models.User.email == payload.email).first()
    if user:
        user.is_email_verified = True
        db.add(user)

    db.commit()
    return EmailVerifyResponse()
