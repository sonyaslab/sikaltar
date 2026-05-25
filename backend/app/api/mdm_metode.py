"""
API Router — MDM Metode Estimasi per Kategori (Sub-6)
Halaman ringkasan: semua kategori × Metode ADHB + ADHK + Indeks Deflator,
dapat diedit inline tanpa membuka halaman Kategori.
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.kategori_pdrb import KategoriPdrb
from app.models.komoditas import Komoditas
from app.services.mdm_audit_service import log_update_many

router = APIRouter()

METODE_OPTIONS = [
    "Produksi", "Revaluasi", "Deflasi", "Double Deflasi",
    "Commodity Flow", "Langsung", "Pengeluaran",
]


def _row(k: KategoriPdrb, kom_count: int = 0) -> dict:
    return {
        "kode":          k.kode,
        "nama":          k.nama,
        "level":         k.level,
        "parent_kode":   k.parent_kode,
        "urutan":        k.urutan,
        "metode_adhb":   k.metode_adhb,
        "metode_adhk":   k.metode_adhk,
        # indeks_deflator diambil dari kolom keterangan sementara
        # atau dari komoditas.indeks_deflator (aggregate dari children)
        "indeks_deflator": getattr(k, "keterangan", None),
        "aktif":         getattr(k, "aktif", True),
        "komoditas_count": kom_count,
    }


@router.get("", summary="List kategori × metode estimasi (overview)")
def list_metode(
    level: Optional[int] = Query(None, ge=1, le=4,
                                  description="Filter level (default: tampilkan level 2 & 3)"),
    q: Optional[str] = Query(None, description="Cari nama atau kode"),
    aktif_only: bool = Query(True),
    db: Session = Depends(get_db),
):
    """
    Kembalikan daftar kategori beserta metode ADHB, ADHK, dan indeks deflator
    yang digunakan. Default hanya level 2–3 (yang memiliki metode estimasi konkrit).
    """
    query = db.query(KategoriPdrb)

    if level is not None:
        query = query.filter(KategoriPdrb.level == level)
    else:
        # Default: tampilkan level 2 dan 3 (level 1 biasanya tidak punya metode)
        query = query.filter(KategoriPdrb.level.in_([2, 3]))

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

    # Aggregate indeks deflator dari komoditas anak (jika ada)
    # ambil nilai unik pertama per kategori
    deflator_map: dict[str, str] = {}
    try:
        deflator_rows = (
            db.query(Komoditas.kategori_kode, Komoditas.indeks_deflator)
            .filter(
                Komoditas.aktif.is_(True),
                Komoditas.indeks_deflator.isnot(None),
                Komoditas.indeks_deflator != "",
            )
            .distinct()
            .all()
        )
        for kat_kode, idx in deflator_rows:
            if kat_kode not in deflator_map:
                deflator_map[kat_kode] = idx
    except Exception:
        pass

    result = []
    for k in rows:
        d = _row(k, kom_counts.get(k.kode, 0))
        # Override indeks_deflator dari komoditas jika tersedia
        if k.kode in deflator_map:
            d["indeks_deflator"] = deflator_map[k.kode]
        result.append(d)

    return {
        "total": len(result),
        "metode_options": METODE_OPTIONS,
        "rows": result,
    }


@router.patch("/{kode}", summary="Update metode ADHB/ADHK inline")
def update_metode(
    kode: str,
    payload: dict = Body(...),
    user_nama: str = Query("Admin"),
    confirm_metode: bool = Query(
        False, description="Wajib True jika mengubah metode (konfirmasi dampak)"
    ),
    db: Session = Depends(get_db),
):
    """
    Patch metode_adhb dan/atau metode_adhk dari halaman Metode Estimasi.
    Jika ada perubahan metode dan confirm_metode=False, kembalikan peringatan dulu.
    """
    k = db.query(KategoriPdrb).filter(KategoriPdrb.kode == kode).first()
    if not k:
        raise HTTPException(404, f"Kategori {kode!r} tidak ditemukan")

    metode_adhb_baru = payload.get("metode_adhb")
    metode_adhk_baru = payload.get("metode_adhk")
    indeks_baru = payload.get("indeks_deflator")

    # Validasi nilai metode
    for val, label in [(metode_adhb_baru, "metode_adhb"), (metode_adhk_baru, "metode_adhk")]:
        if val and val not in METODE_OPTIONS:
            raise HTTPException(
                422,
                f"Nilai {label}={val!r} tidak valid. Pilihan: {METODE_OPTIONS}",
            )

    # Periksa apakah ada perubahan metode
    metode_changed = (
        (metode_adhb_baru and metode_adhb_baru != k.metode_adhb) or
        (metode_adhk_baru and metode_adhk_baru != k.metode_adhk)
    )

    if metode_changed and not confirm_metode:
        kom_count = (
            db.query(func.count(Komoditas.id))
            .filter(Komoditas.kategori_kode == kode, Komoditas.aktif.is_(True))
            .scalar() or 0
        )
        return {
            "requires_confirm": True,
            "warning": (
                f"⚠ Mengubah metode estimasi akan mengubah cara penghitungan "
                f"untuk {kom_count} komoditas. Data historis tidak akan dihitung ulang. "
                f"Konfirmasi?"
            ),
            "komoditas_count": kom_count,
        }

    # Alasan wajib jika ada perubahan metode
    alasan = payload.get("alasan")
    if metode_changed and not alasan:
        raise HTTPException(
            422,
            "Field 'alasan' wajib diisi saat mengubah metode estimasi.",
        )

    # Apply update
    update_data: dict = {}
    if metode_adhb_baru:
        update_data["metode_adhb"] = metode_adhb_baru
    if metode_adhk_baru:
        update_data["metode_adhk"] = metode_adhk_baru

    # indeks_deflator disimpan di keterangan sementara (sampai model diperluas)
    if indeks_baru is not None and hasattr(k, "keterangan"):
        update_data["keterangan"] = indeks_baru

    changed = log_update_many(
        db, "kategori_pdrb", k.id, k, update_data, user_nama, alasan
    )
    for col, val in update_data.items():
        if hasattr(k, col):
            setattr(k, col, val)

    db.commit()
    return {
        **_row(k),
        "changed_columns": changed,
        "message": f"Metode kategori {kode} berhasil diperbarui",
    }
