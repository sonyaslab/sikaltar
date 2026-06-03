"""
SIKALTARA — Model User
Tabel autentikasi dengan role admin/operator dan filter wilayah.
"""
from __future__ import annotations

import enum
from datetime import datetime

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class RoleEnum(str, enum.Enum):
    admin    = "admin"
    operator = "operator"


class User(Base):
    """Tabel users — akun login SIKALTARA."""
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(sa.Integer, primary_key=True, autoincrement=True)

    username: Mapped[str] = mapped_column(
        sa.String(50), unique=True, nullable=False, index=True,
        comment="Username unik untuk login"
    )
    email: Mapped[str | None] = mapped_column(
        sa.String(100), unique=True, nullable=True,
        comment="Email opsional"
    )
    hashed_password: Mapped[str] = mapped_column(
        sa.String(255), nullable=False,
        comment="Password di-hash bcrypt"
    )

    # Role & akses wilayah
    role: Mapped[str] = mapped_column(
        sa.Enum(RoleEnum, name="role_enum"), nullable=False, default=RoleEnum.operator,
        comment="admin = akses semua; operator = hanya wilayahnya"
    )
    wilayah_kode: Mapped[str | None] = mapped_column(
        sa.String(10), nullable=True,
        comment="NULL = akses semua (admin). Contoh: '6501' = Kab. Malinau"
    )

    # Nama tampilan
    nama: Mapped[str | None] = mapped_column(
        sa.String(100), nullable=True,
        comment="Nama lengkap untuk ditampilkan di UI"
    )

    # Status
    is_active: Mapped[bool] = mapped_column(
        sa.Boolean, nullable=False, server_default=sa.true(),
        comment="False = akun dinonaktifkan"
    )
    must_change_password: Mapped[bool] = mapped_column(
        sa.Boolean, nullable=False, server_default=sa.true(),
        comment="True = wajib ganti password saat login pertama"
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime, nullable=False, server_default=sa.func.now()
    )
    last_login: Mapped[datetime | None] = mapped_column(
        sa.DateTime, nullable=True
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} username={self.username!r} role={self.role}>"
