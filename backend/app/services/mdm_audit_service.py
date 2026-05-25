"""
services/mdm_audit_service.py
Helper untuk menulis entri audit_master secara konsisten.
Dipanggil oleh semua MDM API router saat terjadi perubahan data master.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.models.master import AuditMaster


def log_insert(
    db: Session,
    tabel: str,
    record_id: int,
    user_nama: str = "System",
    alasan: Optional[str] = None,
) -> None:
    """Log aksi INSERT pada tabel master."""
    db.add(AuditMaster(
        tabel_nama=tabel,
        record_id=record_id,
        aksi="INSERT",
        user_nama=user_nama,
        alasan=alasan,
        waktu=datetime.now(),
    ))
    db.flush()


def log_update(
    db: Session,
    tabel: str,
    record_id: int,
    kolom: str,
    nilai_lama: Any,
    nilai_baru: Any,
    user_nama: str = "System",
    alasan: Optional[str] = None,
    berlaku_mulai: Optional[int] = None,
) -> None:
    """Log aksi UPDATE satu kolom pada tabel master."""
    # Hanya catat jika ada perubahan nyata
    if str(nilai_lama) == str(nilai_baru):
        return
    db.add(AuditMaster(
        tabel_nama=tabel,
        record_id=record_id,
        aksi="UPDATE",
        kolom_ubah=kolom,
        nilai_lama=str(nilai_lama) if nilai_lama is not None else None,
        nilai_baru=str(nilai_baru) if nilai_baru is not None else None,
        user_nama=user_nama,
        alasan=alasan,
        berlaku_mulai=berlaku_mulai,
        waktu=datetime.now(),
    ))


def log_update_many(
    db: Session,
    tabel: str,
    record_id: int,
    old_obj: Any,
    payload: dict,
    user_nama: str = "System",
    alasan: Optional[str] = None,
    berlaku_mulai: Optional[int] = None,
    skip_columns: Optional[list[str]] = None,
) -> list[str]:
    """
    Log UPDATE untuk banyak kolom sekaligus.
    Bandingkan nilai payload dengan nilai lama dari old_obj.
    Kembalikan list kolom yang benar-benar berubah.
    """
    skip = set(skip_columns or [])
    changed = []
    for kolom, nilai_baru in payload.items():
        if kolom in skip:
            continue
        nilai_lama = getattr(old_obj, kolom, None)
        if str(nilai_lama) != str(nilai_baru):
            changed.append(kolom)
            log_update(
                db, tabel, record_id, kolom,
                nilai_lama, nilai_baru, user_nama, alasan, berlaku_mulai,
            )
    return changed


def log_nonaktifkan(
    db: Session,
    tabel: str,
    record_id: int,
    user_nama: str = "System",
    alasan: Optional[str] = None,
) -> None:
    """Log aksi NONAKTIFKAN (soft delete)."""
    db.add(AuditMaster(
        tabel_nama=tabel,
        record_id=record_id,
        aksi="NONAKTIFKAN",
        user_nama=user_nama,
        alasan=alasan,
        waktu=datetime.now(),
    ))
    db.flush()
