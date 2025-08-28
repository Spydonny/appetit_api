"""
Business hours validation service.
Handles working hours logic and order rejection during non-working hours.
"""
from datetime import datetime, time, timezone, timedelta
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass


@dataclass
class BusinessHours:
    """represents business hours for a single day."""
    day: int  # 0=Monday, 6=Sunday
    open_time: Optional[time]
    close_time: Optional[time]
    is_closed: bool = False


@dataclass
class BusinessHoursValidationResult:
    """result of business hours validation."""
    is_open: bool
    reason: Optional[str] = None
    next_open_time: Optional[datetime] = None


class BusinessHoursService:
    """service for managing business hours and validation."""
    
    def __init__(self):
        # default business hours (can be configured from db later)
        self.default_hours = {
            0: BusinessHours(0, time(9, 0), time(22, 0)),  # Monday
            1: BusinessHours(1, time(9, 0), time(22, 0)),  # Tuesday
            2: BusinessHours(2, time(9, 0), time(22, 0)),  # Wednesday
            3: BusinessHours(3, time(9, 0), time(22, 0)),  # Thursday
            4: BusinessHours(4, time(9, 0), time(22, 0)),  # Friday
            5: BusinessHours(5, time(10, 0), time(23, 0)), # Saturday
            6: BusinessHours(6, time(10, 0), time(21, 0)), # Sunday
        }
        
        # timezone for business hours (Kazakhstan time UTC+5)
        self.timezone = timezone(timedelta(hours=5))
    
    def get_current_time(self) -> datetime:
        """get current time in business timezone."""
        return datetime.now(self.timezone)
    
    def is_open_now(self) -> BusinessHoursValidationResult:
        """check if business is currently open."""
        current_time = self.get_current_time()
        return self.is_open_at_time(current_time)
    
    def is_open_at_time(self, check_time: datetime) -> BusinessHoursValidationResult:
        """check if business is open at specific time."""
        # convert to business timezone if needed
        if check_time.tzinfo is None:
            check_time = check_time.replace(tzinfo=self.timezone)
        elif check_time.tzinfo != self.timezone:
            check_time = check_time.astimezone(self.timezone)
        
        weekday = check_time.weekday()  # 0=Monday, 6=Sunday
        current_time = check_time.time()
        
        business_hours = self.default_hours.get(weekday)
        if not business_hours:
            return BusinessHoursValidationResult(
                is_open=False,
                reason="no_hours_defined"
            )
        
        if business_hours.is_closed:
            next_open = self._get_next_open_time(check_time)
            return BusinessHoursValidationResult(
                is_open=False,
                reason="closed_today",
                next_open_time=next_open
            )
        
        if not business_hours.open_time or not business_hours.close_time:
            return BusinessHoursValidationResult(
                is_open=False,
                reason="hours_not_configured"
            )
        
        # check if current time is within business hours
        if business_hours.open_time <= current_time <= business_hours.close_time:
            return BusinessHoursValidationResult(is_open=True)
        
        # business is closed
        next_open = self._get_next_open_time(check_time)
        reason = "before_opening" if current_time < business_hours.open_time else "after_closing"
        
        return BusinessHoursValidationResult(
            is_open=False,
            reason=reason,
            next_open_time=next_open
        )
    
    def _get_next_open_time(self, from_time: datetime) -> Optional[datetime]:
        """get the next time the business will be open."""
        # start from the next day if we're past closing time
        check_date = from_time.date()
        current_time = from_time.time()
        
        # if it's still the same day and we're before opening, return today's opening
        weekday = from_time.weekday()
        today_hours = self.default_hours.get(weekday)
        
        if (today_hours and 
            not today_hours.is_closed and 
            today_hours.open_time and 
            current_time < today_hours.open_time):
            return datetime.combine(check_date, today_hours.open_time, self.timezone)
        
        # look for the next open day (up to 7 days ahead)
        for i in range(1, 8):
            next_date = check_date + timedelta(days=i)
            next_weekday = next_date.weekday()
            next_hours = self.default_hours.get(next_weekday)
            
            if (next_hours and 
                not next_hours.is_closed and 
                next_hours.open_time):
                return datetime.combine(next_date, next_hours.open_time, self.timezone)
        
        return None
    
    def get_hours_for_day(self, weekday: int) -> Optional[BusinessHours]:
        """get business hours for a specific weekday."""
        return self.default_hours.get(weekday)
    
    def update_hours_for_day(self, weekday: int, open_time: Optional[time], 
                            close_time: Optional[time], is_closed: bool = False):
        """update business hours for a specific weekday."""
        if weekday not in range(7):
            raise ValueError("Weekday must be between 0 (Monday) and 6 (Sunday)")
        
        self.default_hours[weekday] = BusinessHours(
            day=weekday,
            open_time=open_time,
            close_time=close_time,
            is_closed=is_closed
        )
    
    def get_weekly_hours(self) -> Dict[str, Dict]:
        """get formatted weekly hours for API response."""
        days = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
        hours = {}
        
        for i, day_name in enumerate(days):
            business_hours = self.default_hours[i]
            hours[day_name] = {
                'is_closed': business_hours.is_closed,
                'open_time': business_hours.open_time.strftime('%H:%M') if business_hours.open_time else None,
                'close_time': business_hours.close_time.strftime('%H:%M') if business_hours.close_time else None
            }
        
        return hours


# global instance
business_hours_service = BusinessHoursService()


def validate_business_hours() -> BusinessHoursValidationResult:
    """convenience function to check current business hours."""
    return business_hours_service.is_open_now()


def can_accept_orders() -> bool:
    """check if orders can be accepted at current time."""
    result = validate_business_hours()
    return result.is_open