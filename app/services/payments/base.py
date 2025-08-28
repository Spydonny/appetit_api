from typing import Any, Dict
import hmac
import hashlib
import os


class PaymentsProvider:
    """base payments provider interface (architecture-ready)."""

    def init(self, order_id: int, amount: float) -> Dict[str, Any]:  # pragma: no cover
        return {"status": "skipped", "reason": "not_implemented"}

    @staticmethod
    def verify_signature(body: bytes, signature: str) -> bool:
        secret = (os.getenv("WEBHOOK_SECRET", "") or "").encode()
        computed = hmac.new(secret, body, hashlib.sha256).hexdigest()
        try:
            return hmac.compare_digest(computed, signature)
        except Exception:
            return False
