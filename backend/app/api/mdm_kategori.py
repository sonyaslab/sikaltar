"""
API Router — MDM Kategori & Lapangan Usaha
Subhalaman 1: Manajemen Kategori PDRB + Metode Estimasi (inline)
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.kategori_pdrb import KategoriPdrb
from app.models.komoditas import Komoditas
from app.services.mdm_audit_service import (
    log_insert, log_update_many, log_nonaktifkan,
)

router = APIRouter()

METODE_OPTIONS = [
    "Produksi", "Revaluasi", "Deflasi", "Double Deflasi",
    "Commodity Flow", "Langsung", "Pengeluaran",
]


def _kat_to_dict(k: KategoriPdrb, komoditas_count: int = 0) -> dict:
    return {
        "kode":          k.kode,
        "nama":          k.nama,
        "level":         k.level,
        "parent_kode":   k.parent_kode,
        "urutan":        k.urutan,
        "metode_adhb":   k.metode_adhb,
        "metode_adhk":   k.metode_adhk,
        "berlaku_mulai": getattr(k, "berlaku_mulai", None),
        "berlaku_sampai": getattr(k, "berlaku_sampai", None),
        "keterangan":    getattr(k, "keterangan", None),
        "aktif":         getattr(k, "aktif", True),
        "komoditas_count": komoditas_count,
    }


@router.get("", summary="List semua kategori PDRB")
def list_kategori(
    level: Optional[int] = Query(None, ge=1, le=4),
    q: Optional[str] = Query(None),
    parent_kode: Optional[str] = Query(None),
    aktif_only: bool = Query(True),
    db: Session = Depends(get_db),
):
    query = db.query(KategoriPdrb)
    if level is not None:
        query = query.filter(KategoriPdrb.level == level)
    if parent_kode:
        query = query.filter(KategoriPdrb.parent_kode == parent_kode)
    if q:
        query = query.filter(
            KategoriPdrb.nama.ilike(f"%{q}%") | KategoriPdrb.kode.ilike(f"%{q}%")
        )
    if aktif_only:
        aktif_col = getattr(KategoriPdrb, "aktif", None)
        if aktif_col is not None:
            query = query.filter(aktif_col.is_(True))

    rows = query.order_by(KategoriPdrb.urutan, KategoriPdrb.kode).all()

    # Batch count komoditas per kategori
    kom_counts = dict(
        db.query(Komoditas.kategori_kode, func.count(Komoditas.id))
        .filter(Komoditas.aktif.is_(True))
        .group_by(Komoditas.kategori_kode)
        .all()
    )

    return [_kat_to_dict(k, kom_counts.get(k.kode, 0)) for k in rows]


@router.get("/metode-options", summary="Daftar metode estimasi yang tersedia")
def get_metode_options():
    return {"options": METODE_OPTIONS}


@router.get("/{kode}", summary="Detail satu kategori")
def get_kategori(kode: str, db: Session = Depends(get_db)):
    k = db.query(KategoriPdrb).filter(KategoriPdrb.kode == kode).first()
    if not k:
        raise HTTPException(404, f"Kategori {kode!r} tidak ditemukan")
    kom_count = (
        db.query(func.count(Komoditas.id))
        .filter(Komoditas.kategori_kode == kode, Komoditas.aktif.is_(True))
        .scalar() or 0
    )
    return _kat_to_dict(k, kom_count)


@router.post("", summary="Tambah kategori baru", status_code=201)
def create_kategori(
    payload: dict = Body(...),
    user_nama: str = Query("Admin"),
    db: Session = Depends(get_db),
):
    kode = payload.get("kode", "").strip()
    if not kode:
        raise HTTPException(422, "Kode kategori wajib diisi")
    existing = db.query(KategoriPdrb).filter(KategoriPdrb.kode == kode).first()
    if existing:
        raise HTTPException(409, f"Kode {kode!r} sudah ada")

    # Validasi parent
    parent_kode = payload.get("parent_kode")
    if parent_kode:
        parent = db.query(KategoriPdrb).filter(KategoriPdrb.kode == parent_kode).first()
        if not parent:
            raise HTTPException(404, f"Parent {parent_kode!r} tidak ditemukan")

    k = KategoriPdrb(
        kode=kode,
        nama=payload.get("nama", ""),
        level=payload.get("level", 3),
        parent_kode=parent_kode,
        urutan=payload.get("urutan", 999),
        metode_adhb=payload.get("metode_adhb"),
        metode_adhk=payload.get("metode_adhk"),
    )
    # Set optional MDM columns if model has them
    for col in ("berlaku_mulai", "berlaku_sampai", "keterangan"):
        if hasattr(k, col) and col in payload:
            setattr(k, col, payload[col])
    if hasattr(k, "aktif"):
        k.aktif = True

    db.add(k)
    db.flush()
    log_insert(db, "kategori_pdrb", k.id, user_nama, alasan=payload.get("alasan"))
    db.commit()
    return _kat_to_dict(k)


@router.put("/{kode}", summary="Edit kategori (termasuk metode ADHB/ADHK)")
def update_kategori(
    kode: str,
    payload: dict = Body(...),
    user_nama: str = Query("Admin"),
    confirm_metode: bool = Query(False, description="Konfirmasi perubahan metode"),
    db: Session = Depends(get_db),
):
    k = db.query(KategoriPdrb).filter(KategoriPdrb.kode == kode).first()
    if not k:
        raise HTTPException(404, f"Kategori {kode!r} tidak ditemukan")

    # Cek perubahan metode — minta konfirmasi
    if not confirm_metode:
        metode_changed = (
            payload.get("metode_adhb") and payload["metode_adhb"] != k.metode_adhb
            or payload.get("metode_adhk") and payload["metode_adhk"] != k.metode_adhk
        )
        if metode_changed:
            kom_count = (
                db.query(func.count(Komoditas.id))
                .filter(Komoditas.kategori_kode == kode, Komoditas.aktif.is_(True))
                .scalar() or 0
            )
            return {
                "requires_confirm": True,
                "warning": (
                    f"⚠ Mengubah metode akan mengubah cara penghitungan untuk "
                    f"{kom_count} komoditas. Data historis tidak akan dihitung ulang. "
                    f"Konfirmasi perubahan ini?"
                ),
                "komoditas_count": kom_count,
            }

    editable = ["nama", "level", "parent_kode", "urutan", "metode_adhb", "metode_adhk",
                "berlaku_mulai", "berlaku_sampai", "keterangan"]
    update_data = {col: payload[col] for col in editable if col in payload}
    changed = log_update_many(db, "kategori_pdrb", k.id, k, update_data,
                               user_nama, payload.get("alasan"))
    for col, val in update_data.items():
        if hasattr(k, col):
            setattr(k, col, val)

    db.commit()
    return {**_kat_to_dict(k), "changed_columns": changed}


@router.delete("/{kode}", summary="Nonaktifkan kategori (soft delete)")
def nonaktifkan_kategori(
    kode: str,
    alasan: str = Query(..., description="Alasan nonaktifkan (wajib)"),
    user_nama: str = Query("Admin"),
    db: Session = Depends(get_db),
):
    k = db.query(KategoriPdrb).filter(KategoriPdrb.kode == kode).first()
    if not k:
        raise HTTPException(404, f"Kategori {kode!r} tidak ditemukan")

    # Kategori level 1 tidak bisa dihapus
    if k.level == 1:
        raise HTTPException(
            403,
            "Kategori level 1 (utama) tidak bisa dihapus. Gunakan tombol Nonaktifkan.",
        )

    # Cek ada komoditas aktif
    kom_count = (
        db.query(func.count(Komoditas.id))
        .filter(Komoditas.kategori_kode == kode, Komoditas.aktif.is_(True))
        .scalar() or 0
    )
    if kom_count > 0:
        raise HTTPException(
            409,
            f"Tidak bisa nonaktifkan: masih ada {kom_count} komoditas aktif di kategori ini.",
        )

    if hasattr(k, "aktif"):
        k.aktif = False
    log_nonaktifkan(db, "kategori_pdrb", k.id, user_nama, alasan)
    db.commit()
    return {"message": f"Kategori {kode} dinonaktifkan", "kode": kode}
