"""
SIKALTARA — Auth Router
POST /auth/login, POST /auth/logout, GET /auth/me, POST /auth/change-password
"""
from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from jose import jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import (
    SECRET_KEY,
    ALGORITHM,
    get_current_user,
)
from app.models.user import User
from app.schemas.user import (
    ChangePasswordRequest,
    TokenResponse,
    UserLogin,
    UserMe,
)

router = APIRouter()

# ── Password hashing ───────────────────────────────────────────────────────────
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Token expiry: 8 jam
ACCESS_TOKEN_EXPIRE_HOURS: int = int(os.getenv("JWT_EXPIRE_HOURS", "8"))


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def hash_password(plain: str) -> str:
    return pwd_context.hash(plain)


def create_access_token(user: User) -> str:
    expire = datetime.now(timezone.utc) + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
    payload = {
        "sub":          str(user.id),
        "username":     user.username,
        "role":         user.role if isinstance(user.role, str) else user.role.value,
        "wilayah_kode": user.wilayah_kode,
        "nama":         user.nama,
        "exp":          expire,
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


# ── Endpoints ──────────────────────────────────────────────────────────────────

@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Login — dapatkan JWT token",
)
def login(body: UserLogin, db: Session = Depends(get_db)):
    """
    Autentikasi user dan kembalikan JWT access token.
    Token berlaku 8 jam.
    """
    user: Optional[User] = (
        db.query(User)
        .filter(User.username == body.username, User.is_active == True)
        .first()
    )
    if user is None or not verify_password(body.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Username atau password salah.",
        )

    # Update last_login
    user.last_login = datetime.now(timezone.utc)
    db.commit()
    db.refresh(user)

    token = create_access_token(user)
    role_val = user.role if isinstance(user.role, str) else user.role.value

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        role=role_val,
        wilayah_kode=user.wilayah_kode,
        nama=user.nama or user.username,
        must_change_password=user.must_change_password,
    )


@router.post(
    "/logout",
    summary="Logout — hapus token di sisi client",
)
def logout(current_user: User = Depends(get_current_user)):
    """
    Stateless logout — token di-blacklist di sisi client (localStorage).
    Server hanya mengkonfirmasi.
    """
    return {"message": "Berhasil logout. Silakan hapus token dari browser."}


@router.get(
    "/me",
    response_model=UserMe,
    summary="Profil user yang sedang login",
)
def me(current_user: User = Depends(get_current_user)):
    """Kembalikan info user berdasarkan token yang dikirim."""
    return current_user


@router.post(
    "/change-password",
    summary="Ganti password (wajib setelah login pertama)",
)
def change_password(
    body: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Ganti password. Setelah berhasil, must_change_password di-set False."""
    if not verify_password(body.old_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password lama salah.",
        )
    if len(body.new_password) < 8:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Password baru minimal 8 karakter.",
        )

    current_user.hashed_password   = hash_password(body.new_password)
    current_user.must_change_password = False
    db.commit()
    return {"message": "Password berhasil diubah."}
