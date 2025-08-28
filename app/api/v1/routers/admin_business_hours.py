from typing import Dict, Any, Optional
from datetime import time

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from app.core.security import require_admin
from app.db.session import get_db
from app import models
from app.services.business.hours import business_hours_service, validate_business_hours

router = APIRouter(prefix="/admin/business-hours", tags=["admin"])


class BusinessHoursUpdate(BaseModel):
    """schema for updating business hours for a specific day."""
    open_time: Optional[str] = Field(None, description="Opening time in HH:MM format", pattern="^([01]?[0-9]|2[0-3]):[0-5][0-9]$")
    close_time: Optional[str] = Field(None, description="Closing time in HH:MM format", pattern="^([01]?[0-9]|2[0-3]):[0-5][0-9]$")
    is_closed: Optional[bool] = Field(None, description="Whether the business is closed on this day")


class BusinessHoursStatus(BaseModel):
    """schema for business hours status response."""
    is_open: bool = Field(..., description="Whether the business is currently open")
    current_time: str = Field(..., description="Current time in business timezone")
    reason: Optional[str] = Field(None, description="Reason if closed")
    next_open_time: Optional[str] = Field(None, description="Next opening time if closed")


class WeeklyHoursUpdate(BaseModel):
    """schema for updating all weekly business hours."""
    monday: Optional[BusinessHoursUpdate] = None
    tuesday: Optional[BusinessHoursUpdate] = None
    wednesday: Optional[BusinessHoursUpdate] = None
    thursday: Optional[BusinessHoursUpdate] = None
    friday: Optional[BusinessHoursUpdate] = None
    saturday: Optional[BusinessHoursUpdate] = None
    sunday: Optional[BusinessHoursUpdate] = None


@router.get("/status", response_model=BusinessHoursStatus)
def get_business_status(
    db: Session = Depends(get_db),
    _: models.User = Depends(require_admin),
):
    """get current business hours status."""
    validation_result = validate_business_hours()
    current_time = business_hours_service.get_current_time()
    
    return BusinessHoursStatus(
        is_open=validation_result.is_open,
        current_time=current_time.strftime('%Y-%m-%d %H:%M:%S %Z'),
        reason=validation_result.reason,
        next_open_time=validation_result.next_open_time.strftime('%Y-%m-%d %H:%M:%S %Z') if validation_result.next_open_time else None
    )


@router.get("/weekly", response_model=Dict[str, Any])
def get_weekly_hours(
    db: Session = Depends(get_db),
    _: models.User = Depends(require_admin),
):
    """get weekly business hours config."""
    weekly_hours = business_hours_service.get_weekly_hours()
    
    # add current status
    validation_result = validate_business_hours()
    current_time = business_hours_service.get_current_time()
    
    return {
        "current_status": {
            "is_open": validation_result.is_open,
            "current_time": current_time.strftime('%Y-%m-%d %H:%M:%S %Z'),
            "reason": validation_result.reason,
            "next_open_time": validation_result.next_open_time.strftime('%Y-%m-%d %H:%M:%S %Z') if validation_result.next_open_time else None
        },
        "weekly_hours": weekly_hours
    }


@router.put("/day/{day_name}")
def update_day_hours(
    day_name: str,
    payload: BusinessHoursUpdate,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_admin),
):
    """update business hours for a specific day."""
    day_mapping = {
        'monday': 0, 'tuesday': 1, 'wednesday': 2, 'thursday': 3,
        'friday': 4, 'saturday': 5, 'sunday': 6
    }
    
    if day_name.lower() not in day_mapping:
        raise HTTPException(status_code=400, detail="Invalid day name. Use: monday, tuesday, wednesday, thursday, friday, saturday, sunday")
    
    weekday = day_mapping[day_name.lower()]
    
    # parse time strings to time objects
    open_time = None
    close_time = None
    
    if payload.open_time:
        try:
            hour, minute = map(int, payload.open_time.split(':'))
            open_time = time(hour, minute)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid open_time format. Use HH:MM")
    
    if payload.close_time:
        try:
            hour, minute = map(int, payload.close_time.split(':'))
            close_time = time(hour, minute)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid close_time format. Use HH:MM")
    
    # check that open_time is before close_time
    if open_time and close_time and open_time >= close_time:
        raise HTTPException(status_code=400, detail="Opening time must be before closing time")
    
    # update business hours
    current_hours = business_hours_service.get_hours_for_day(weekday)
    if not current_hours:
        raise HTTPException(status_code=500, detail="Failed to get current hours")
    
    # update only provided fields
    new_open_time = open_time if payload.open_time is not None else current_hours.open_time
    new_close_time = close_time if payload.close_time is not None else current_hours.close_time
    new_is_closed = payload.is_closed if payload.is_closed is not None else current_hours.is_closed
    
    business_hours_service.update_hours_for_day(
        weekday=weekday,
        open_time=new_open_time,
        close_time=new_close_time,
        is_closed=new_is_closed
    )
    
    return {
        "message": f"Business hours for {day_name} updated successfully",
        "day": day_name,
        "open_time": new_open_time.strftime('%H:%M') if new_open_time else None,
        "close_time": new_close_time.strftime('%H:%M') if new_close_time else None,
        "is_closed": new_is_closed
    }


@router.put("/weekly")
def update_weekly_hours(
    payload: WeeklyHoursUpdate,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_admin),
):
    """update business hours for the entire week."""
    days = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
    updated_days = []
    
    for i, day_name in enumerate(days):
        day_update = getattr(payload, day_name)
        if day_update:
            # parse and check times
            open_time = None
            close_time = None
            
            if day_update.open_time:
                try:
                    hour, minute = map(int, day_update.open_time.split(':'))
                    open_time = time(hour, minute)
                except ValueError:
                    raise HTTPException(status_code=400, detail=f"Invalid open_time format for {day_name}. Use HH:MM")
            
            if day_update.close_time:
                try:
                    hour, minute = map(int, day_update.close_time.split(':'))
                    close_time = time(hour, minute)
                except ValueError:
                    raise HTTPException(status_code=400, detail=f"Invalid close_time format for {day_name}. Use HH:MM")
            
            # check that open_time is before close_time
            if open_time and close_time and open_time >= close_time:
                raise HTTPException(status_code=400, detail=f"Opening time must be before closing time for {day_name}")
            
            # update business hours for this day
            current_hours = business_hours_service.get_hours_for_day(i)
            if current_hours:
                new_open_time = open_time if day_update.open_time is not None else current_hours.open_time
                new_close_time = close_time if day_update.close_time is not None else current_hours.close_time
                new_is_closed = day_update.is_closed if day_update.is_closed is not None else current_hours.is_closed
                
                business_hours_service.update_hours_for_day(
                    weekday=i,
                    open_time=new_open_time,
                    close_time=new_close_time,
                    is_closed=new_is_closed
                )
                updated_days.append(day_name)
    
    return {
        "message": f"Business hours updated for {len(updated_days)} days",
        "updated_days": updated_days,
        "weekly_hours": business_hours_service.get_weekly_hours()
    }


@router.post("/emergency-close")
def emergency_close(
    db: Session = Depends(get_db),
    _: models.User = Depends(require_admin),
):
    """emergency close - mark all days as closed."""
    for weekday in range(7):
        current_hours = business_hours_service.get_hours_for_day(weekday)
        if current_hours:
            business_hours_service.update_hours_for_day(
                weekday=weekday,
                open_time=current_hours.open_time,
                close_time=current_hours.close_time,
                is_closed=True
            )
    
    return {"message": "Emergency close activated - all days marked as closed"}


@router.post("/emergency-open")
def emergency_open(
    db: Session = Depends(get_db),
    _: models.User = Depends(require_admin),
):
    """emergency open - mark all days as open with default hours."""
    for weekday in range(7):
        current_hours = business_hours_service.get_hours_for_day(weekday)
        if current_hours:
            business_hours_service.update_hours_for_day(
                weekday=weekday,
                open_time=current_hours.open_time,
                close_time=current_hours.close_time,
                is_closed=False
            )
    
    return {"message": "Emergency open activated - all days marked as open"}