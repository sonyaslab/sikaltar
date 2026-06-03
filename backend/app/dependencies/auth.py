"""
SIKALTARA — Auth Dependencies
JWT decode, user lookup, dan role checks.
"""
from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User, RoleEnum

# ── Konfigurasi JWT ────────────────────────────────────────────────────────────
SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "SIKALTARA_SECRET_CHANGE_IN_PRODUCTION_2024!")
ALGORITHM:  str = "HS256"

# HTTP Bearer token extractor (auto_error=False supaya bisa kita beri pesan custom)
bearer_scheme = HTTPBearer(auto_error=False)


# ── Token Decode ───────────────────────────────────────────────────────────────

def decode_token(token: str) -> dict:
    """Decode dan verifikasi JWT. Raise 401 jika tidak valid/expired."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token tidak valid atau sudah expired. Silakan login kembali.",
            headers={"WWW-Authenticate": "Bearer"},
        )


# ── Core Dependency ────────────────────────────────────────────────────────────

def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    """
    Dependency utama — ekstrak dan validasi JWT, kembalikan User object.
    Sertakan di setiap endpoint yang membutuhkan autentikasi.
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token tidak ditemukan. Silakan login terlebih dahulu.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_token(credentials.credentials)

    user_id: Optional[int] = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token tidak valid (sub missing).",
        )

    user = db.query(User).filter(User.id == int(user_id), User.is_active == True).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Akun tidak ditemukan atau tidak aktif.",
        )
    return user


# ── Role Guards ────────────────────────────────────────────────────────────────

def require_admin(
    current_user: User = Depends(get_current_user),
) -> User:
    """Hanya admin yang boleh akses. Raise 403 jika bukan admin."""
    if current_user.role != RoleEnum.admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Akses ditolak — endpoint ini hanya untuk admin.",
        )
    return current_user


def require_operator_or_admin(
    current_user: User = Depends(get_current_user),
) -> User:
    """Admin dan operator boleh akses. Raise 403 jika role lain."""
    if current_user.role not in (RoleEnum.admin, RoleEnum.operator):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Akses ditolak — diperlukan role operator atau admin.",
        )
    return current_user


# ── Wilayah Filter Helper ──────────────────────────────────────────────────────

def check_wilayah_access(current_user: User, wilayah_kode: str) -> None:
    """
    Validasi bahwa operator hanya bisa mengakses wilayah miliknya.
    Admin tidak dibatasi (wilayah_kode = NULL).
    """
    if current_user.role == RoleEnum.admin:
        return  # admin akses semua wilayah
    if current_user.wilayah_kode and current_user.wilayah_kode != wilayah_kode:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Operator hanya dapat mengakses wilayah {current_user.wilayah_kode!r}.",
        )
