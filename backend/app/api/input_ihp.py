"""API Router — Input IHP."""
from __future__ import annotations

from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.input_data import InputIHP
from app.models.komoditas import Komoditas
from app.models.kategori_pdrb import KategoriPdrb
from app.schemas.ihp import InputIHPRead, InputIHPPatch
from app.services.cascade_service import enqueue_cascade

router = APIRouter()


def _get_or_create_ihp(
    db: Session, kategori_kode: str, komoditas_id: Optional[int], wilayah_kode: str, tahun: int, triwulan: Optional[int]
) -> InputIHP:
    row = (
        db.query(InputIHP)
        .filter(
            InputIHP.kategori_kode == kategori_kode,
            InputIHP.komoditas_id == komoditas_id,
            InputIHP.wilayah_kode == wilayah_kode,
            InputIHP.tahun == tahun,
            InputIHP.triwulan == triwulan,
        )
        .first()
    )
    if not row:
        row = InputIHP(
            kategori_kode=kategori_kode,
            komoditas_id=komoditas_id,
            wilayah_kode=wilayah_kode,
            tahun=tahun,
            triwulan=triwulan,
            nilai_indeks=Decimal("100.0000")
        )
        db.add(row)
        db.flush()
    return row


@router.get("", summary="Data IHP per wilayah/tahun/triwulan")
def get_ihp(
    wilayah_kode: str = Query(..., description="Kode wilayah, mis: '65'"),
    tahun: int = Query(..., ge=2008),
    triwulan: Optional[int] = Query(None, ge=1, le=4),
    kategori_kode: Optional[str] = Query(None, description="Filter kategori"),
    db: Session = Depends(get_db),
):
    """Ambil data IHP yang tersimpan."""
    query = db.query(InputIHP).filter(
        InputIHP.wilayah_kode == wilayah_kode,
        InputIHP.tahun == tahun,
        InputIHP.triwulan == triwulan,
    )
    if kategori_kode:
        query = query.filter(InputIHP.kategori_kode.startswith(kategori_kode))
        
    rows = query.all()
    result = []
    for row in rows:
        result.append({
            "id": row.id,
            "kategori_kode": row.kategori_kode,
            "komoditas_id": row.komoditas_id,
            "wilayah_kode": row.wilayah_kode,
            "tahun": row.tahun,
            "triwulan": row.triwulan,
            "nilai_indeks": str(row.nilai_indeks),
            "sumber_data": row.sumber_data,
        })
    return result


@router.patch("", summary="Update data IHP (trigger cascade)")
def update_ihp(
    payload: InputIHPPatch,
    db: Session = Depends(get_db),
):
    """
    Patch data IHP untuk (kategori, komoditas, wilayah, tahun, triwulan).
    """
    row = _get_or_create_ihp(
        db, 
        kategori_kode=payload.kategori_kode, 
        komoditas_id=payload.komoditas_id, 
        wilayah_kode=payload.wilayah_kode, 
        tahun=payload.tahun, 
        triwulan=payload.triwulan
    )

    if payload.nilai_indeks is not None:
        row.nilai_indeks = payload.nilai_indeks
    if payload.sumber_data is not None:
        row.sumber_data = payload.sumber_data

    db.commit()

    # Trigger kalkulasi ulang
    task_id = enqueue_cascade(
        trigger_type="ihp",
        wilayah_kode=payload.wilayah_kode,
        tahun=payload.tahun,
        triwulan=payload.triwulan,
        komoditas_id=payload.komoditas_id,
        kategori_kode_scope=payload.kategori_kode if not payload.komoditas_id else None,
    )

    return {"message": "IHP updated", "task_id": task_id}
