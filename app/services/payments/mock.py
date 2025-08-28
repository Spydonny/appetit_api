from typing import Any, Dict
from .base import PaymentsProvider


class MockPayments(PaymentsProvider):
    def init(self, order_id: int, amount: float) -> Dict[str, Any]:  # pragma: no cover
        return {"status": "ok", "checkout_url": f"https://pay.example.test/checkout/{order_id}"}
