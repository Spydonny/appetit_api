import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Tuple

from app.core.config import settings


def generate_otp_data() -> Tuple[str, str, str, str, datetime]:
    """
    Generate OTP verification data.
    
    Returns:
        Tuple of (raw_token, raw_code, token_hash, code_hash, expires_at)
    """
    # generate token (for potential future use) and 6-digit code
    raw_token = secrets.token_hex(16)
    raw_code = f"{secrets.randbelow(1000000):06d}"
    
    # hash both for secure storage
    token_hash = _sha256(raw_token)
    code_hash = _sha256(raw_code)
    
    # set expiration time
    expires_at = datetime.now(tz=timezone.utc) + timedelta(
        minutes=settings.PHONE_VERIFICATION_EXPIRES_MIN
    )
    
    return raw_token, raw_code, token_hash, code_hash, expires_at


def hash_code(code: str) -> str:
    """hash an OTP code for secure storage and verification."""
    return _sha256(code)


def _sha256(s: str) -> str:
    """helper function to generate SHA256 hash."""
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def format_phone_number(phone: str) -> str:
    """
    Basic phone number formatting for consistency.
    Removes spaces, dashes, and ensures it starts with +.
    
    Args:
        phone: Raw phone number string
        
    Returns:
        Formatted phone number
    """
    # remove common formatting characters
    clean = phone.replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
    
    # ensure it starts with +
    if not clean.startswith("+"):
        clean = "+" + clean
    
    return clean


def validate_phone_format(phone: str) -> bool:
    """
    Basic phone number validation.
    
    Args:
        phone: Phone number to validate
        
    Returns:
        True if phone number appears valid
    """
    if not phone or not isinstance(phone, str):
        return False
    
    # check for double + in original (invalid)
    if phone.count("+") > 1:
        return False
    
    # if phone doesn't start with +, check if it has valid formatting characters
    if not phone.startswith("+"):
        # bare digit strings are invalid (e.g., "1234567890")
        if phone.isdigit():
            return False
        # must have formatting characters like spaces, parentheses, or dashes to be valid
        formatting_chars = {' ', '(', ')', '-'}
        if not any(char in phone for char in formatting_chars):
            return False
    
    # for phones that already start with +, check for specific invalid patterns
    # let format_phone_number handle most cleaning, but reject obvious invalid patterns
    if phone.startswith("+"):
        # remove + and check if the remaining part contains letters (clearly invalid)
        remaining = phone[1:].replace(" ", "").replace("(", "").replace(")", "").replace("-", "")
        if not remaining.isdigit():
            return False
        
        # reject specific invalid dash patterns like "+123-456-7890" (US format with dashes)
        import re
        # pattern for +XXX-XXX-XXXX (area code with dashes but no parentheses/spaces)
        if re.match(r'^\+\d{3}-\d{3}-\d{4}$', phone):
            return False
    
    # clean the phone number using format_phone_number
    try:
        clean_phone = format_phone_number(phone)
    except Exception:
        return False
    
    # check if cleaned phone starts with +
    if not clean_phone.startswith("+"):
        return False
    
    # check if contains only digits after the +
    digits_part = clean_phone[1:]  # Remove the +
    if not digits_part.isdigit():
        return False
    
    # should be between 10-15 digits (international standards)
    if len(digits_part) < 10 or len(digits_part) > 15:
        return False
    
    return True