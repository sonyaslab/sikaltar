"""
SIKALTARA — Auth khusus SSE (Server-Sent Events)
=================================================
MASALAH: Endpoint /api/events dilindungi require_operator_or_admin yang membaca
token dari header 'Authorization: Bearer ...'. Tetapi EventSource di browser
TIDAK BISA mengirim header custom, sehingga koneksi SSE selalu 401
→ muncul banner "SSE terputus — mencoba reconnect...".

SOLUSI: autentikasi SSE lewat query-param token, contoh:
    new EventSource('/api/events?token=' + accessToken + '&task_id=' + id)

Letakkan file ini di: backend/app/dependencies/auth_sse.py
"""
from __future__ import annotations

from typing import Optional

from fastapi import Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import decode_token
from app.models.user import User, RoleEnum


def require_sse_token(
    token: Optional[str] = Query(None, description="JWT access token (untuk EventSource)"),
    db: Session = Depends(get_db),
) -> User:
    """Validasi token SSE dari query-param. Kembalikan User operator/admin."""
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token SSE tidak ditemukan. Sertakan ?token=<access_token>.",
        )
    payload = decode_token(token)
    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token tidak valid.")
    user = db.query(User).filter(User.id == int(user_id), User.is_active == True).first()
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Akun tidak ditemukan/aktif.")
    if user.role not in (RoleEnum.admin, RoleEnum.operator):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Role tidak diizinkan.")
    return user
