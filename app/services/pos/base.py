from typing import Any, Dict


class POSAdapter:
    """base interface for POS/ERP integrations (architecture-ready)."""

    def push_order(self, order: Any) -> Dict[str, Any]:  # pragma: no cover
        return {"status": "skipped", "reason": "not_implemented"}

    def get_menu(self) -> Dict[str, Any]:  # pragma: no cover
        return {"status": "skipped", "reason": "not_implemented"}
