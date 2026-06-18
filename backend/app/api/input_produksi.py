"""API Router — Input Produksi (S1.P)."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.input_data import InputProduksi
from app.models.komoditas import Komoditas
from app.schemas.produksi import InputProduksiPatch
from app.services.cascade_service import enqueue_cascade

router = APIRouter()


def _get_tw_breakdown(
    db: Session, komoditas_id: int, wilayah_kode: str, tahun: int
) -> dict:
    """Ambil data TW1–TW4 untuk satu komoditas."""
    tw_rows = (
        db.query(InputProduksi)
        .filter(
            InputProduksi.komoditas_id == komoditas_id,
            InputProduksi.wilayah_kode == wilayah_kode,
            InputProduksi.tahun == tahun,
            InputProduksi.triwulan.in_([1, 2, 3, 4]),
        )
        .all()
    )
    tw_map = {r.triwulan: r.kuantum for r in tw_rows}
    tw1 = tw_map.get(1)
    tw2 = tw_map.get(2)
    tw3 = tw_map.get(3)
    tw4 = tw_map.get(4)
    values = [v for v in [tw1, tw2, tw3, tw4] if v is not None]
    total = sum(values) if values else None
    return {"tw1": tw1, "tw2": tw2, "tw3": tw3, "tw4": tw4, "total_tw": total}


@router.get("", summary="Data produksi per wilayah/tahun/triwulan")
def get_produksi(
    wilayah_kode: str = Query(...),
    tahun: int = Query(..., ge=2008),
    triwulan: Optional[int] = Query(None, ge=1, le=4),
    db: Session = Depends(get_db),
):
    """
    Jika triwulan=None (filter Tahunan):
      - Kembalikan data tahunan langsung (triwulan=NULL di DB)
      - Sertakan breakdown TW1–TW4 jika ada
      - Tandai has_conflict jika keduanya ada
    """
    komoditas_list = (
        db.query(Komoditas)
        .filter(Komoditas.aktif.is_(True))
        .order_by(Komoditas.nama)
        .all()
    )

    result = []
    for kom in komoditas_list:
        # Data untuk periode yang diminta
        p_row = (
            db.query(InputProduksi)
            .filter(
                InputProduksi.komoditas_id == kom.id,
                InputProduksi.wilayah_kode == wilayah_kode,
                InputProduksi.tahun == tahun,
                InputProduksi.triwulan == triwulan,
            )
            .first()
        )

        row = {
            "komoditas_id": kom.id,
            "komoditas_nama": kom.nama,
            "kategori_kode": kom.kategori_kode,
            "wujud_produksi": kom.wujud_produksi,
            "satuan_produksi": kom.satuan_produksi,
            "wilayah_kode": wilayah_kode,
            "tahun": tahun,
            "triwulan": triwulan,
            "kuantum": str(p_row.kuantum) if p_row and p_row.kuantum is not None else None,
            "status": p_row.status if p_row else "sementara",
            "sumber_data": p_row.sumber_data if p_row else None,
            "tw1": None, "tw2": None, "tw3": None, "tw4": None,
            "total_tw": None, "has_conflict": False,
        }

        # Untuk filter Tahunan → sertakan breakdown TW
        if triwulan is None:
            tw = _get_tw_breakdown(db, kom.id, wilayah_kode, tahun)
            row.update({k: str(v) if v is not None else None for k, v in tw.items()})
            # Conflict: ada data tahunan langsung DAN ada sum TW
            has_tahunan = p_row and p_row.kuantum is not None
            has_tw_data = tw["total_tw"] is not None
            row["has_conflict"] = bool(has_tahunan and has_tw_data)

        result.append(row)

    return result


@router.patch("/{komoditas_id}", summary="Update produksi (trigger cascade)")
def patch_produksi(
    komoditas_id: int,
    body: InputProduksiPatch,
    wilayah_kode: str = Query(...),
    tahun: int = Query(..., ge=2008),
    triwulan: Optional[int] = Query(None, ge=1, le=4),
    db: Session = Depends(get_db),
):
    """Update produksi untuk 1 komoditas, 1 periode. Trigger cascade."""
    row = (
        db.query(InputProduksi)
        .filter(
            InputProduksi.komoditas_id == komoditas_id,
            InputProduksi.wilayah_kode == wilayah_kode,
            InputProduksi.tahun == tahun,
            InputProduksi.triwulan == triwulan,
        )
        .first()
    )
    if not row:
        row = InputProduksi(
            komoditas_id=komoditas_id,
            wilayah_kode=wilayah_kode,
            tahun=tahun,
            triwulan=triwulan,
        )
        db.add(row)

    if body.kuantum is not None:
        row.kuantum = body.kuantum
    if body.sumber_data is not None:
        row.sumber_data = body.sumber_data
    if body.status is not None:
        row.status = body.status

    db.commit()

    task_id = enqueue_cascade(
        trigger_type="produksi",
        wilayah_kode=wilayah_kode,
        tahun=tahun,
        triwulan=triwulan,
        komoditas_id=komoditas_id,
    )

    return {
        "status": "ok",
        "task_id": task_id,
        "komoditas_id": komoditas_id,
        "wilayah_kode": wilayah_kode,
        "tahun": tahun,
        "triwulan": triwulan,
    }
