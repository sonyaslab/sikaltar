"""
SIKALTARA — Admin Users Router
CRUD manajemen akun user (admin only).

Endpoints:
  GET    /admin/users
  POST   /admin/users
  PATCH  /admin/users/{id}
  DELETE /admin/users/{id}           ← soft delete
  POST   /admin/users/{id}/reset-password
"""
from __future__ import annotations

import random
import string
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from passlib.context import CryptContext
from pydantic import BaseModel, field_validator
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import require_admin
from app.models.user import User, RoleEnum

router = APIRouter()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ── Pydantic Schemas ───────────────────────────────────────────────────────────

class UserSummary(BaseModel):
    """Response item untuk list user."""
    id: int
    username: str
    email: Optional[str] = None
    nama: Optional[str] = None
    role: str
    wilayah_kode: Optional[str] = None
    is_active: bool
    must_change_password: bool
    created_at: datetime
    last_login: Optional[datetime] = None

    model_config = {"from_attributes": True}


class UserListResponse(BaseModel):
    users: List[UserSummary]
    total: int
    aktif: int
    admin_count: int
    operator_count: int


class UserCreateRequest(BaseModel):
    username: str
    nama: Optional[str] = None
    email: Optional[str] = None
    role: str = "operator"
    wilayah_kode: Optional[str] = None
    password: str

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: str) -> str:
        if v not in ("admin", "operator"):
            raise ValueError("role harus 'admin' atau 'operator'")
        return v

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 6:
            raise ValueError("Password minimal 6 karakter")
        return v


class UserUpdateRequest(BaseModel):
    nama: Optional[str] = None
    email: Optional[str] = None
    role: Optional[str] = None
    wilayah_kode: Optional[str] = None
    is_active: Optional[bool] = None

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in ("admin", "operator"):
            raise ValueError("role harus 'admin' atau 'operator'")
        return v


class ResetPasswordResponse(BaseModel):
    message: str
    temp_password: str
    username: str


# ── Helper ─────────────────────────────────────────────────────────────────────

def _generate_temp_password(length: int = 8) -> str:
    """Generate password sementara: 4 huruf + 4 angka, diacak."""
    letters = random.choices(string.ascii_letters, k=4)
    digits  = random.choices(string.digits, k=4)
    pool    = letters + digits
    random.shuffle(pool)
    return "".join(pool)


def _get_user_or_404(db: Session, user_id: int) -> User:
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User dengan id={user_id} tidak ditemukan.",
        )
    return user


# ── Endpoints ──────────────────────────────────────────────────────────────────

@router.get("", response_model=UserListResponse, summary="List semua user (admin only)")
def list_users(
    db:           Session = Depends(get_db),
    _admin:       User    = Depends(require_admin),
):
    """Kembalikan semua user beserta statistik ringkasan."""
    users = db.query(User).order_by(User.created_at.desc()).all()
    aktif = sum(1 for u in users if u.is_active)
    admin_count    = sum(1 for u in users if u.role == RoleEnum.admin)
    operator_count = sum(1 for u in users if u.role == RoleEnum.operator)
    return UserListResponse(
        users=[UserSummary.model_validate(u) for u in users],
        total=len(users),
        aktif=aktif,
        admin_count=admin_count,
        operator_count=operator_count,
    )


@router.post("", response_model=UserSummary, status_code=status.HTTP_201_CREATED,
             summary="Tambah user baru (admin only)")
def create_user(
    body:   UserCreateRequest,
    db:     Session = Depends(get_db),
    _admin: User    = Depends(require_admin),
):
    # Cek duplikat username
    if db.query(User).filter(User.username == body.username).first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Username '{body.username}' sudah digunakan.",
        )
    # Cek duplikat email
    if body.email and db.query(User).filter(User.email == body.email).first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Email '{body.email}' sudah digunakan.",
        )
    # Admin tidak perlu wilayah_kode
    wilayah = None if body.role == "admin" else body.wilayah_kode

    user = User(
        username             = body.username,
        nama                 = body.nama,
        email                = body.email or None,
        hashed_password      = pwd_context.hash(body.password),
        role                 = RoleEnum(body.role),
        wilayah_kode         = wilayah,
        is_active            = True,
        must_change_password = True,   # wajib ganti saat login pertama
        created_at           = datetime.now(timezone.utc),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return UserSummary.model_validate(user)


@router.patch("/{user_id}", response_model=UserSummary,
              summary="Update user (admin only)")
def update_user(
    user_id: int,
    body:    UserUpdateRequest,
    db:      Session = Depends(get_db),
    _admin:  User    = Depends(require_admin),
):
    user = _get_user_or_404(db, user_id)

    if body.nama      is not None: user.nama      = body.nama
    if body.email     is not None: user.email     = body.email or None
    if body.is_active is not None: user.is_active = body.is_active

    if body.role is not None:
        user.role = RoleEnum(body.role)
        # Kalau jadi admin, hapus wilayah_kode
        if body.role == "admin":
            user.wilayah_kode = None

    if body.wilayah_kode is not None and user.role == RoleEnum.operator:
        user.wilayah_kode = body.wilayah_kode

    db.commit()
    db.refresh(user)
    return UserSummary.model_validate(user)


@router.delete("/{user_id}", summary="Nonaktifkan user — soft delete (admin only)")
def deactivate_user(
    user_id: int,
    db:      Session = Depends(get_db),
    admin:   User    = Depends(require_admin),
):
    user = _get_user_or_404(db, user_id)

    # Jangan bisa nonaktifkan diri sendiri
    if user.id == admin.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tidak bisa menonaktifkan akun sendiri.",
        )
    user.is_active = False
    db.commit()
    return {"message": f"User '{user.username}' berhasil dinonaktifkan.", "id": user_id}


@router.post("/{user_id}/reset-password", response_model=ResetPasswordResponse,
             summary="Reset password ke sementara (admin only)")
def reset_password(
    user_id: int,
    db:      Session = Depends(get_db),
    _admin:  User    = Depends(require_admin),
):
    user = _get_user_or_404(db, user_id)

    temp_pw                  = _generate_temp_password()
    user.hashed_password     = pwd_context.hash(temp_pw)
    user.must_change_password = True
    db.commit()

    return ResetPasswordResponse(
        message=f"Password '{user.username}' berhasil direset.",
        temp_password=temp_pw,
        username=user.username,
    )
