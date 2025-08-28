from typing import Any, Dict

from .base import POSAdapter


class MockPOS(POSAdapter):
    def push_order(self, order: Any) -> Dict[str, Any]:  # pragma: no cover
        oid = getattr(order, "id", None)
        return {"status": "ok", "external_pos_id": f"mock-{oid}"}

    def get_menu(self) -> Dict[str, Any]:  # pragma: no cover
        return {"status": "ok", "items": []}
