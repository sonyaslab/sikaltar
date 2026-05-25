"""
Models: MasterVersi, AuditMaster, MasterSatuan
Tabel referensi MDM.
"""
from __future__ import annotations
from datetime import datetime
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class MasterVersi(Base):
    """Versi klasifikasi lapangan usaha yang pernah digunakan."""
    __tablename__ = 'master_versi'

    id:                  Mapped[int]      = mapped_column(Integer, primary_key=True, autoincrement=True)
    kode_versi:          Mapped[str]      = mapped_column(String(20), unique=True, nullable=False)
    nama_versi:          Mapped[str]      = mapped_column(String(100), nullable=False)
    tahun_terbit:        Mapped[int]      = mapped_column(Integer, nullable=False)
    berlaku_mulai_pdrb:  Mapped[int|None] = mapped_column(Integer, nullable=True)
    catatan:             Mapped[str|None] = mapped_column(Text, nullable=True)
    aktif:               Mapped[bool]     = mapped_column(Boolean, default=True, nullable=False)

    def __repr__(self) -> str:
        return f'<MasterVersi {self.kode_versi!r}>'


class AuditMaster(Base):
    """Log perubahan pada data master."""
    __tablename__ = 'audit_master'

    id:           Mapped[int]      = mapped_column(Integer, primary_key=True, autoincrement=True)
    tabel_nama:   Mapped[str]      = mapped_column(String(50), nullable=False, index=True)
    record_id:    Mapped[int]      = mapped_column(Integer, nullable=False, index=True)
    aksi:         Mapped[str]      = mapped_column(String(20), nullable=False, comment="INSERT|UPDATE|DELETE|NONAKTIFKAN")
    kolom_ubah:   Mapped[str|None] = mapped_column(String(100), nullable=True)
    nilai_lama:   Mapped[str|None] = mapped_column(Text, nullable=True)
    nilai_baru:   Mapped[str|None] = mapped_column(Text, nullable=True)
    user_id:      Mapped[int|None] = mapped_column(Integer, nullable=True)
    user_nama:    Mapped[str|None] = mapped_column(String(100), nullable=True)
    waktu:        Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    alasan:       Mapped[str|None] = mapped_column(Text, nullable=True)
    berlaku_mulai: Mapped[int|None] = mapped_column(Integer, nullable=True)

    def __repr__(self) -> str:
        return f'<AuditMaster {self.tabel_nama}#{self.record_id} {self.aksi}>'


class MasterSatuan(Base):
    """Master satuan produksi."""
    __tablename__ = 'master_satuan'

    id:          Mapped[int]      = mapped_column(Integer, primary_key=True, autoincrement=True)
    kode:        Mapped[str]      = mapped_column(String(20), unique=True, nullable=False)
    nama:        Mapped[str]      = mapped_column(String(100), nullable=False)
    keterangan:  Mapped[str|None] = mapped_column(Text, nullable=True)
    aktif:       Mapped[bool]     = mapped_column(Boolean, default=True, nullable=False)

    def __repr__(self) -> str:
        return f'<MasterSatuan {self.kode!r}>'
