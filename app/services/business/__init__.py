"""
Business logic services package.

This package contains services for handling business logic including:
- Business hours validation and management
- Order acceptance rules
- Working time enforcement
"""

from .hours import (
    BusinessHours,
    BusinessHoursValidationResult, 
    BusinessHoursService,
    business_hours_service,
    validate_business_hours,
    can_accept_orders
)

__all__ = [
    'BusinessHours',
    'BusinessHoursValidationResult',
    'BusinessHoursService', 
    'business_hours_service',
    'validate_business_hours',
    'can_accept_orders'
]