"""API Router — Input Adjustment."""
from __future__ import annotations

from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.hasil import PdrbRekap
from app.services.cascade_service import enqueue_cascade

router = APIRouter()


class InputAdjustmentPatch(BaseModel):
    kategori_kode: str
    wilayah_kode: str
    tahun: int
    triwulan: Optional[int] = None
    adjustment_adhb: Optional[Decimal] = None
    adjustment_adhk: Optional[Decimal] = None


@router.patch("", summary="Update data adjustment (trigger cascade)")
def update_adjustment(
    payload: InputAdjustmentPatch,
    db: Session = Depends(get_db),
):
    """
    Patch data adjustment untuk (kategori, wilayah, tahun, triwulan).
    """
    row = (
        db.query(PdrbRekap)
        .filter(
            PdrbRekap.kategori_kode == payload.kategori_kode,
            PdrbRekap.wilayah_kode == payload.wilayah_kode,
            PdrbRekap.tahun == payload.tahun,
            PdrbRekap.triwulan == payload.triwulan,
        )
        .first()
    )

    if not row:
        row = PdrbRekap(
            kategori_kode=payload.kategori_kode,
            wilayah_kode=payload.wilayah_kode,
            tahun=payload.tahun,
            triwulan=payload.triwulan,
        )
        db.add(row)

    if payload.adjustment_adhb is not None:
        row.adjustment_adhb = payload.adjustment_adhb
    if payload.adjustment_adhk is not None:
        row.adjustment_adhk = payload.adjustment_adhk

    db.commit()

    # Trigger kalkulasi ulang
    task_id = enqueue_cascade(
        trigger_type="adjustment",
        wilayah_kode=payload.wilayah_kode,
        tahun=payload.tahun,
        triwulan=payload.triwulan,
        kategori_kode_scope=payload.kategori_kode,
    )

    return {"message": "Adjustment updated", "task_id": task_id}
