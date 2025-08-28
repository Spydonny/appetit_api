from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional, List

from app.core.security import optional_oauth2_scheme, decode_token, require_admin
from app.db.session import get_db
from app import models
from app.schemas.devices import DeviceRegisterRequest, DeviceOut

router = APIRouter(prefix="/devices", tags=["devices"])


@router.post("/register", response_model=DeviceOut)
def register_device(payload: DeviceRegisterRequest, db: Session = Depends(get_db), token: Optional[str] = Depends(optional_oauth2_scheme)):
    user_id: Optional[int] = None
    if token:
        try:
            payload_token = decode_token(token)
            sub = payload_token.get("sub")
            if sub:
                user_id = int(sub)
        except Exception:
            # ignore invalid token for device registration (allow anonymous register)
            pass

    device = db.query(models.Device).filter(models.Device.fcm_token == payload.fcm_token).first()
    if device:
        device.platform = payload.platform
        if user_id and not device.user_id:
            device.user_id = user_id
    else:
        device = models.Device(platform=payload.platform, fcm_token=payload.fcm_token, user_id=user_id)
        db.add(device)
    db.commit()
    db.refresh(device)
    return device


# admin device management

@router.get("", response_model=List[DeviceOut])
def list_devices(
    db: Session = Depends(get_db),
    _: models.User = Depends(require_admin)
):
    """list all devices (Admin only)"""
    devices = db.query(models.Device).order_by(models.Device.created_at.desc()).all()
    return devices


@router.delete("/{device_id}")
def delete_device(
    device_id: int,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_admin)
):
    """delete a device (Admin only)"""
    device = db.get(models.Device, device_id)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    
    db.delete(device)
    db.commit()
    return {"message": "Device deleted successfully"}
