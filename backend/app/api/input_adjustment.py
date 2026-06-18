# File: app/api/adjustment_manual.py
"""
API Router — Adjustment Manual (Sesuai Flowchart)
Endpoint untuk input adjustment manual yang bisa menambah/mengurangi NTB.
"""
from __future__ import annotations

from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.hasil import PdrbRekap
from app.models.kategori_pdrb import KategoriPdrb
from app.services.kalkulasi_flowchart import (
    hitung_subkategori_flowchart,
    simpan_pdrb_rekap_flowchart,
)
from app.services.cascade_service import enqueue_cascade

router = APIRouter()


class AdjustmentManualRequest(BaseModel):
    adjustment_manual_adhb: Optional[Decimal] = None
    adjustment_manual_adhk: Optional[Decimal] = None
    keterangan: Optional[str] = None


class AdjustmentManualResponse(BaseModel):
    status: str
    message: str
    kategori_kode: str
    kategori_nama: str
    wilayah_kode: str
    tahun: int
    triwulan: Optional[int]
    ntb_hitung_adhb: Optional[Decimal]
    ntb_hitung_adhk: Optional[Decimal]
    adjustment_manual_adhb: Optional[Decimal]
    adjustment_manual_adhk: Optional[Decimal]
    ntb_final_adhb: Optional[Decimal]
    ntb_final_adhk: Optional[Decimal]
    task_id: Optional[str] = None


@router.get("/adjustment", 
            summary="Lihat adjustment manual saat ini",
            response_model=dict)
def get_adjustment(
    kategori_kode: str = Query(..., description="Kode subkategori"),
    wilayah_kode: str = Query(..., description="Kode wilayah"),
    tahun: int = Query(..., ge=2008),
    triwulan: Optional[int] = Query(None, ge=1, le=4),
    db: Session = Depends(get_db),
):
    """Ambil nilai adjustment manual yang sudah diinput."""
    rekap = (
        db.query(PdrbRekap)
        .filter(
            PdrbRekap.kategori_kode == kategori_kode,
            PdrbRekap.wilayah_kode == wilayah_kode,
            PdrbRekap.tahun == tahun,
            PdrbRekap.triwulan == triwulan,
        )
        .first()
    )
    
    if not rekap:
        return {
            "status": "not_found",
            "message": "Data belum ada. Silakan hitung dulu atau input adjustment.",
        }
    
    return {
        "status": "ok",
        "kategori_kode": rekap.kategori_kode,
        "ntb_hitung_adhb": float(rekap.ntb_hitung_adhb) if rekap.ntb_hitung_adhb else None,
        "ntb_hitung_adhk": float(rekap.ntb_hitung_adhk) if rekap.ntb_hitung_adhk else None,
        "adjustment_manual_adhb": float(rekap.adjustment_manual_adhb) if rekap.adjustment_manual_adhb else None,
        "adjustment_manual_adhk": float(rekap.adjustment_manual_adhk) if rekap.adjustment_manual_adhk else None,
        "ntb_final_adhb": float(rekap.ntb_final_adhb) if rekap.ntb_final_adhb else None,
        "ntb_final_adhk": float(rekap.ntb_final_adhk) if rekap.ntb_final_adhk else None,
    }


@router.patch("/adjustment",
              summary="Input adjustment manual (trigger recalculate)",
              response_model=AdjustmentManualResponse)
def patch_adjustment(
    kategori_kode: str = Query(..., description="Kode subkategori"),
    wilayah_kode: str = Query(..., description="Kode wilayah"),
    tahun: int = Query(..., ge=2008),
    triwulan: Optional[int] = Query(None, ge=1, le=4),
    body: AdjustmentManualRequest = None,
    db: Session = Depends(get_db),
):
    """
    Input adjustment manual untuk subkategori.
    Nilai bisa positif (menambah) atau negatif (mengurangi) NTB.
    
    Setelah simpan → trigger cascade recalculate untuk update kategori parent.
    """
    # Validasi kategori
    kategori = db.query(KategoriPdrb).filter(KategoriPdrb.kode == kategori_kode).first()
    if not kategori:
        raise HTTPException(status_code=404, detail="Kategori tidak ditemukan")
    
    # Hitung ulang subkategori dengan adjustment baru
    hasil = hitung_subkategori_flowchart(
        db, kategori_kode, wilayah_kode, tahun, triwulan
    )
    
    # Simpan dengan adjustment manual
    rekap = simpan_pdrb_rekap_flowchart(
        db, hasil, wilayah_kode, tahun, triwulan,
        adjustment_manual_adhb=body.adjustment_manual_adhb,
        adjustment_manual_adhk=body.adjustment_manual_adhk,
    )
    
    db.commit()
    
    # Trigger cascade untuk roll-up ke kategori parent
    task_id = enqueue_cascade(
        trigger_type="adjustment",
        wilayah_kode=wilayah_kode,
        tahun=tahun,
        triwulan=triwulan,
        kategori_kode_scope=kategori_kode,
    )
    
    return AdjustmentManualResponse(
        status="ok",
        message="Adjustment disimpan. Kalkulasi ulang berjalan di background.",
        kategori_kode=kategori_kode,
        kategori_nama=kategori.nama,
        wilayah_kode=wilayah_kode,
        tahun=tahun,
        triwulan=triwulan,
        ntb_hitung_adhb=hasil.ntb_hitung_adhb,
        ntb_hitung_adhk=hasil.ntb_hitung_adhk,
        adjustment_manual_adhb=rekap.adjustment_manual_adhb,
        adjustment_manual_adhk=rekap.adjustment_manual_adhk,
        ntb_final_adhb=rekap.ntb_final_adhb,
        ntb_final_adhk=rekap.ntb_final_adhk,
        task_id=task_id,
    )