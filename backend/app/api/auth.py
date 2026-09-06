from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.auth import (
    create_access_token,
    current_user,
    hash_password,
    verify_password,
)
from app.db.models import User
from app.db.session import get_db
from app.settings import Settings, get_settings

router = APIRouter(prefix="/api/auth", tags=["auth"])


class AuthRequest(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=8, max_length=128)


class UserResponse(BaseModel):
    id: int
    email: str
    role: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


def _token_response(user: User, settings: Settings) -> TokenResponse:
    return TokenResponse(
        access_token=create_access_token(user, settings),
        user=UserResponse(id=user.id, email=user.email, role=user.role),
    )


@router.post("/register", response_model=TokenResponse, status_code=201)
def register(
    payload: AuthRequest,
    database: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> TokenResponse:
    email = payload.email.strip().lower()
    if database.scalar(select(User).where(User.email == email)):
        raise HTTPException(status_code=409, detail="Email is already registered")
    is_first_user = database.scalar(select(func.count(User.id))) == 0
    user = User(
        email=email,
        password_hash=hash_password(payload.password),
        role="admin" if is_first_user else "viewer",
    )
    database.add(user)
    database.commit()
    database.refresh(user)
    return _token_response(user, settings)


@router.post("/login", response_model=TokenResponse)
def login(
    payload: AuthRequest,
    database: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> TokenResponse:
    user = database.scalar(select(User).where(User.email == payload.email.strip().lower()))
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    return _token_response(user, settings)


@router.get("/me", response_model=UserResponse)
def me(user: User = Depends(current_user)) -> UserResponse:
    return UserResponse(id=user.id, email=user.email, role=user.role)
