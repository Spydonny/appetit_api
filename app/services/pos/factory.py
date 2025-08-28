import os
from .base import POSAdapter
from .mock import MockPOS


def get_pos_adapter() -> POSAdapter:
    provider = os.getenv("POS_PROVIDER", "mock").lower()
    if provider == "mock":
        return MockPOS()
    # default to mock for MVP
    return MockPOS()
