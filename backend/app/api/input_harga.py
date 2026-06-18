"""API Router — Input Harga (S1.H)."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.input_data import InputHarga
from app.models.komoditas import Komoditas
from app.schemas.harga import InputHargaRead, InputHargaPatch
from app.services.cascade_service import enqueue_cascade

router = APIRouter()

TAHUN_DASAR = 2010


def _get_or_create_harga(
    db: Session, komoditas_id: int, wilayah_kode: str, tahun: int, triwulan: Optional[int]
) -> InputHarga:
    row = (
        db.query(InputHarga)
        .filter(
            InputHarga.komoditas_id == komoditas_id,
            InputHarga.wilayah_kode == wilayah_kode,
            InputHarga.tahun == tahun,
            InputHarga.triwulan == triwulan,
        )
        .first()
    )
    if not row:
        row = InputHarga(
            komoditas_id=komoditas_id,
            wilayah_kode=wilayah_kode,
            tahun=tahun,
            triwulan=triwulan,
        )
        db.add(row)
        db.flush()
    return row


@router.get("", summary="Data harga per wilayah/tahun/triwulan")
def get_harga(
    wilayah_kode: str = Query(..., description="Kode wilayah, mis: '65'"),
    tahun: int = Query(..., ge=2008),
    triwulan: Optional[int] = Query(None, ge=1, le=4),
    db: Session = Depends(get_db),
):
    """
    Kembalikan list data harga untuk semua komoditas aktif pada wilayah+tahun+triwulan.
    Harga konstan 2010 selalu diambil dari record tahun=2010, triwulan=NULL.
    """
    komoditas_list = db.query(Komoditas).filter(Komoditas.aktif.is_(True)).order_by(Komoditas.nama).all()

    result = []
    for kom in komoditas_list:
        # Harga berlaku (tahun berjalan)
        h_row = (
            db.query(InputHarga)
            .filter(
                InputHarga.komoditas_id == kom.id,
                InputHarga.wilayah_kode == wilayah_kode,
                InputHarga.tahun == tahun,
                InputHarga.triwulan == triwulan,
            )
            .first()
        )
        # Harga konstan selalu dari tahun 2010, triwulan=NULL
        h2010 = (
            db.query(InputHarga)
            .filter(
                InputHarga.komoditas_id == kom.id,
                InputHarga.wilayah_kode == wilayah_kode,
                InputHarga.tahun == TAHUN_DASAR,
                InputHarga.triwulan.is_(None),
            )
            .first()
        )
        result.append({
            "komoditas_id": kom.id,
            "komoditas_nama": kom.nama,
            "kategori_kode": kom.kategori_kode,
            "wujud_produksi": kom.wujud_produksi,
            "satuan_harga": kom.satuan_harga,
            "wilayah_kode": wilayah_kode,
            "tahun": tahun,
            "triwulan": triwulan,
            "harga_berlaku": str(h_row.harga_berlaku) if h_row and h_row.harga_berlaku else None,
            "harga_konstan_2010": str(h2010.harga_konstan_2010) if h2010 and h2010.harga_konstan_2010 else None,
            "sumber_data": h_row.sumber_data if h_row else None,
        })

    return result


@router.patch("/{komoditas_id}", summary="Update data harga (trigger cascade)")
def patch_harga(
    komoditas_id: int,
    body: InputHargaPatch,
    wilayah_kode: str = Query(...),
    tahun: int = Query(..., ge=2008),
    triwulan: Optional[int] = Query(None, ge=1, le=4),
    db: Session = Depends(get_db),
):
    """
    Update harga berlaku/konstan untuk 1 komoditas.
    Harga konstan 2010 hanya bisa diisi jika tahun = 2010.
    Setelah simpan → trigger recalculate_cascade() async.
    """
    # Validasi: harga_konstan_2010 hanya untuk tahun 2010
    if body.harga_konstan_2010 is not None and tahun != TAHUN_DASAR:
        raise HTTPException(
            status_code=400,
            detail=f"Harga konstan 2010 hanya bisa diisi pada tahun {TAHUN_DASAR}. "
                   f"Untuk tahun lain, nilai diambil otomatis dari data tahun {TAHUN_DASAR}.",
        )

    # Update harga berlaku (tahun berjalan)
    if body.harga_berlaku is not None or body.sumber_data is not None:
        row = _get_or_create_harga(db, komoditas_id, wilayah_kode, tahun, triwulan)
        if body.harga_berlaku is not None:
            row.harga_berlaku = body.harga_berlaku
        if body.sumber_data is not None:
            row.sumber_data = body.sumber_data
        db.flush()

    # Update harga konstan 2010 (selalu ke record tahun=2010)
    if body.harga_konstan_2010 is not None:
        row_2010 = _get_or_create_harga(db, komoditas_id, wilayah_kode, TAHUN_DASAR, None)
        row_2010.harga_konstan_2010 = body.harga_konstan_2010
        if body.harga_berlaku is not None and tahun == TAHUN_DASAR:
            row_2010.harga_berlaku = body.harga_berlaku
        db.flush()

    db.commit()

    # Trigger cascade async
    task_id = enqueue_cascade(
        trigger_type="harga",
        wilayah_kode=wilayah_kode,
        tahun=tahun,
        triwulan=triwulan,
        komoditas_id=komoditas_id,
    )

    return {
        "status": "ok",
        "message": "Harga disimpan. Kalkulasi ulang berjalan di background.",
        "task_id": task_id,
        "komoditas_id": komoditas_id,
        "wilayah_kode": wilayah_kode,
        "tahun": tahun,
        "triwulan": triwulan,
    }
