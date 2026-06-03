"""
SIKALTARA — Pydantic Schemas untuk Autentikasi
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class UserLogin(BaseModel):
    """Body POST /auth/login."""
    username: str
    password: str


class TokenResponse(BaseModel):
    """Response POST /auth/login."""
    access_token: str
    token_type: str = "bearer"
    role: str
    wilayah_kode: Optional[str] = None
    nama: Optional[str] = None
    must_change_password: bool = False


class UserMe(BaseModel):
    """Response GET /auth/me."""
    id: int
    username: str
    email: Optional[str] = None
    role: str
    wilayah_kode: Optional[str] = None
    nama: Optional[str] = None
    is_active: bool
    must_change_password: bool
    last_login: Optional[datetime] = None

    model_config = {"from_attributes": True}


class ChangePasswordRequest(BaseModel):
    """Body POST /auth/change-password."""
    old_password: str
    new_password: str
