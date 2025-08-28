from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import get_password_hash, verify_password, create_access_token
from app.db.session import get_db
from app import models
from app.schemas.auth import RegisterRequest, LoginRequest, TokenResponse, UserOut

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserOut)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    # ensure either email or phone is provided
    if not payload.email and not payload.phone:
        raise HTTPException(status_code=400, detail="Email or phone is required")

    # check duplicates
    if payload.email:
        existing = db.query(models.User).filter(models.User.email == payload.email).first()
        if existing:
            raise HTTPException(status_code=400, detail="Email already registered")
    if payload.phone:
        existing = db.query(models.User).filter(models.User.phone == payload.phone).first()
        if existing:
            raise HTTPException(status_code=400, detail="Phone already registered")

    user = models.User(
        full_name=payload.full_name,
        email=payload.email,
        phone=payload.phone,
        dob=payload.dob,
        password_hash=get_password_hash(payload.password),
        role="user",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    q = db.query(models.User)
    user = q.filter(models.User.email == payload.email_or_phone).first()
    if not user:
        user = q.filter(models.User.phone == payload.email_or_phone).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    token = create_access_token(subject=str(user.id), role=user.role)
    return TokenResponse(access_token=token, user=user)