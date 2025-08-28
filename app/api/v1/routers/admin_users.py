from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.core.security import require_admin_only, get_password_hash
from app.db.session import get_db
from app import models
from app.schemas.users import UserCreate, UserUpdateAdmin, UserOut

router = APIRouter(prefix="/admin/users", tags=["admin"])


@router.post("/", response_model=UserOut)
def create_user(
    payload: UserCreate,
    db: Session = Depends(get_db),
    admin: models.User = Depends(require_admin_only),
):
    """Create a new manager or courier user"""
    # Check if user with email already exists
    existing_user = db.query(models.User).filter(models.User.email == payload.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="User with this email already exists")
    
    # Check if phone number is already taken (if provided)
    if payload.phone:
        existing_phone = db.query(models.User).filter(models.User.phone == payload.phone).first()
        if existing_phone:
            raise HTTPException(status_code=400, detail="User with this phone number already exists")
    
    # Hash password
    password_hash = get_password_hash(payload.password)
    
    # Create new user
    new_user = models.User(
        full_name=payload.full_name,
        email=payload.email,
        phone=payload.phone,
        password_hash=password_hash,
        role=payload.role,
        dob=payload.dob,
        is_email_verified=False,
        is_phone_verified=False
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    return new_user


@router.get("/", response_model=List[UserOut])
def list_users(
    role: Optional[str] = Query(None, description="Filter by role: manager, courier"),
    search: Optional[str] = Query(None, description="Search by name or email"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    _: models.User = Depends(require_admin_only),
):
    """List all users with optional filtering"""
    query = db.query(models.User)
    
    # Filter by role if provided
    if role:
        valid_roles = ["manager", "courier", "user", "admin"]
        if role not in valid_roles:
            raise HTTPException(status_code=400, detail=f"Invalid role. Must be one of: {', '.join(valid_roles)}")
        query = query.filter(models.User.role == role)
    
    # Search functionality
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            or_(
                models.User.full_name.ilike(search_term),
                models.User.email.ilike(search_term)
            )
        )
    
    # Apply pagination
    users = query.offset(offset).limit(limit).all()
    
    return users


@router.get("/{user_id}", response_model=UserOut)
def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_admin_only),
):
    """Get specific user by ID"""
    user = db.get(models.User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.put("/{user_id}", response_model=UserOut)
def update_user(
    user_id: int,
    payload: UserUpdateAdmin,
    db: Session = Depends(get_db),
    admin: models.User = Depends(require_admin_only),
):
    """Update user details and role"""
    user = db.get(models.User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Prevent admin from demoting themselves
    if user.id == admin.id and payload.role and payload.role != "admin":
        raise HTTPException(status_code=400, detail="Cannot change your own admin role")
    
    # Check email uniqueness if email is being changed
    if payload.email and payload.email != user.email:
        existing_email = db.query(models.User).filter(
            models.User.email == payload.email,
            models.User.id != user_id
        ).first()
        if existing_email:
            raise HTTPException(status_code=400, detail="Email already taken by another user")
    
    # Check phone uniqueness if phone is being changed
    if payload.phone and payload.phone != user.phone:
        existing_phone = db.query(models.User).filter(
            models.User.phone == payload.phone,
            models.User.id != user_id
        ).first()
        if existing_phone:
            raise HTTPException(status_code=400, detail="Phone number already taken by another user")
    
    # Update fields if provided
    update_data = payload.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(user, key, value)
    
    db.add(user)
    db.commit()
    db.refresh(user)
    
    return user


@router.delete("/{user_id}")
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    admin: models.User = Depends(require_admin_only),
):
    """Delete a user (admin cannot delete themselves)"""
    user = db.get(models.User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Prevent admin from deleting themselves
    if user.id == admin.id:
        raise HTTPException(status_code=400, detail="Cannot delete your own admin account")
    
    # Check if user has any orders
    order_count = db.query(models.Order).filter(models.Order.user_id == user_id).count()
    if order_count > 0:
        raise HTTPException(
            status_code=400, 
            detail=f"Cannot delete user with {order_count} orders. Consider deactivating instead."
        )
    
    db.delete(user)
    db.commit()
    
    return {"message": f"User {user.full_name} deleted successfully"}


@router.post("/{user_id}/activate")
def activate_user(
    user_id: int,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_admin_only),
):
    """Activate a user account (future feature - placeholder)"""
    user = db.get(models.User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Note: This is a placeholder for future user activation/deactivation functionality
    # The User model would need an 'is_active' field for this to work fully
    
    return {"message": f"User {user.full_name} activated successfully"}


@router.post("/{user_id}/deactivate")
def deactivate_user(
    user_id: int,
    db: Session = Depends(get_db),
    admin: models.User = Depends(require_admin_only),
):
    """Deactivate a user account (future feature - placeholder)"""
    user = db.get(models.User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Prevent admin from deactivating themselves
    if user.id == admin.id:
        raise HTTPException(status_code=400, detail="Cannot deactivate your own admin account")
    
    # Note: This is a placeholder for future user activation/deactivation functionality
    # The User model would need an 'is_active' field for this to work fully
    
    return {"message": f"User {user.full_name} deactivated successfully"}


@router.get("/stats/summary")
def get_user_stats(
    db: Session = Depends(get_db),
    _: models.User = Depends(require_admin_only),
):
    """Get user statistics by role"""
    stats = {}
    
    # Count users by role
    roles = ["admin", "manager", "courier", "user"]
    for role in roles:
        count = db.query(models.User).filter(models.User.role == role).count()
        stats[f"{role}_count"] = count
    
    # Total users
    stats["total_users"] = db.query(models.User).count()
    
    # Users with verified email/phone
    stats["email_verified_count"] = db.query(models.User).filter(models.User.is_email_verified == True).count()
    stats["phone_verified_count"] = db.query(models.User).filter(models.User.is_phone_verified == True).count()
    
    return stats