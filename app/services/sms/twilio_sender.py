import os
from typing import Optional, Dict

try:
    from twilio.rest import Client  # type: ignore
    from twilio.base.exceptions import TwilioRestException  # type: ignore
except Exception:  # pragma: no cover
    Client = None
    TwilioRestException = None

from app.core.config import settings

_initialized = False
_client: Optional[Client] = None


def _ensure_init():
    global _initialized, _client
    if _initialized:
        return
    if Client is None:
        return
    try:
        account_sid = os.getenv("TWILIO_ACCOUNT_SID")
        auth_token = os.getenv("TWILIO_AUTH_TOKEN")
        if not account_sid or not auth_token:
            return
        _client = Client(account_sid, auth_token)
        _initialized = True
    except Exception:
        # leave uninitd for graceful no-op
        _initialized = False
        _client = None


def health_check() -> Dict[str, str]:
    """check SMS integration health and config status."""
    if Client is None:
        return {"status": "unavailable", "reason": "twilio_library_not_installed"}
    
    account_sid = settings.TWILIO_ACCOUNT_SID
    auth_token = settings.TWILIO_AUTH_TOKEN
    from_number = settings.TWILIO_FROM_NUMBER
    verify_service_sid = settings.TWILIO_VERIFY_SERVICE_SID
    
    if not account_sid:
        return {"status": "misconfigured", "reason": "missing_account_sid"}
    if not auth_token:
        return {"status": "misconfigured", "reason": "missing_auth_token"}
    if not verify_service_sid:
        return {"status": "misconfigured", "reason": "missing_verify_service_sid"}
    
    _ensure_init()
    if not _initialized or not _client:
        return {"status": "error", "reason": "initialization_failed"}
    
    status = {"status": "configured", "account_sid": account_sid[:8] + "...", "verify_service_sid": verify_service_sid[:8] + "..."}
    if from_number:
        status["from_number"] = from_number
    return status


def start_verification(to_number: str, channel: str = "sms") -> Dict[str, str]:
    """Start phone verification using Twilio Verify API.
    
    Equivalent to:
    curl -X POST "https://verify.twilio.com/v2/Services/$VERIFY_SERVICE_SID/Verifications" \
    --data-urlencode "To=$YOUR_PHONE_NUMBER" \
    --data-urlencode "Channel=sms" \
    -u $TWILIO_ACCOUNT_SID:$TWILIO_AUTH_TOKEN
    """
    _ensure_init()
    if not _initialized or not _client:
        return {"status": "skipped", "reason": "twilio_not_configured"}
    
    verify_service_sid = settings.TWILIO_VERIFY_SERVICE_SID
    if not verify_service_sid:
        return {"status": "error", "reason": "missing_verify_service_sid"}
    
    try:
        verification = _client.verify.v2.services(verify_service_sid).verifications.create(
            to=to_number,
            channel=channel
        )
        return {"status": "sent", "sid": verification.sid, "status_twilio": verification.status}
    except TwilioRestException as e:
        return {"status": "error", "reason": "twilio_api_error", "error": str(e)}
    except Exception as e:
        return {"status": "error", "reason": "verification_failed", "error": str(e)}


def check_verification(to_number: str, code: str) -> Dict[str, str]:
    """Check verification code using Twilio Verify API.
    
    Equivalent to:
    curl -X POST "https://verify.twilio.com/v2/Services/$VERIFY_SERVICE_SID/VerificationCheck" \
    --data-urlencode "To=$YOUR_PHONE_NUMBER" \
    --data-urlencode "Code=1234567" \
    -u $TWILIO_ACCOUNT_SID:$TWILIO_AUTH_TOKEN
    """
    _ensure_init()
    if not _initialized or not _client:
        return {"status": "skipped", "reason": "twilio_not_configured"}
    
    verify_service_sid = settings.TWILIO_VERIFY_SERVICE_SID
    if not verify_service_sid:
        return {"status": "error", "reason": "missing_verify_service_sid"}
    
    try:
        verification_check = _client.verify.v2.services(verify_service_sid).verification_checks.create(
            to=to_number,
            code=code
        )
        return {
            "status": "checked", 
            "sid": verification_check.sid,
            "status_twilio": verification_check.status,
            "valid": verification_check.status == "approved"
        }
    except TwilioRestException as e:
        return {"status": "error", "reason": "twilio_api_error", "error": str(e)}
    except Exception as e:
        return {"status": "error", "reason": "verification_check_failed", "error": str(e)}


def send_sms(to_number: str, body: str) -> Dict[str, str]:
    """send SMS message to a phone number (legacy function for backwards compatibility)."""
    _ensure_init()
    if not _initialized or not _client:
        return {"status": "skipped", "reason": "sms_not_configured"}
    
    from_number = settings.TWILIO_FROM_NUMBER
    if not from_number:
        return {"status": "error", "reason": "missing_from_number"}
    
    try:
        message = _client.messages.create(
            body=body,
            from_=from_number,
            to=to_number
        )
        return {"status": "sent", "sid": message.sid}
    except TwilioRestException as e:
        return {"status": "error", "reason": "twilio_api_error", "error": str(e)}
    except Exception as e:
        return {"status": "error", "reason": "send_failed", "error": str(e)}