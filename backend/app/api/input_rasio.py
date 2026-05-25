"""API Router — Rasio (S1.R) — referensi, override, impact preview."""
from __future__ import annotations

from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.kategori_pdrb import KategoriPdrb
from app.models.komoditas import Komoditas
from app.models.rasio import RasioReferensi, RasioOverride
from app.models.hasil import PdrbRekap
from app.schemas.rasio_deflator import RasioOverridePatch, RasioImpactPreview
from app.services.rasio_service import get_rasio_safe
from app.services.cascade_service import enqueue_cascade

router = APIRouter()


def _build_rasio_rows(
    db: Session, jenis_rasio: str, tahun: int, berlaku_untuk: str, wilayah_kode: str
) -> list[dict]:
    """
    Bangun tabel rasio: semua kategori level 2-3, dengan nilai default dan override.
    """
    kategori_list = (
        db.query(KategoriPdrb)
        .filter(KategoriPdrb.level >= 2)
        .order_by(KategoriPdrb.urutan)
        .all()
    )

    rows = []
    for kat in kategori_list:
        # Nilai default dari rasio_referensi
        nilai_default = get_rasio_safe(
            db, jenis_rasio, berlaku_untuk, tahun,
            kategori_kode=kat.kode, wilayah_kode=None,  # tanpa override
        )

        # Cek override lokal
        override = (
            db.query(RasioOverride)
            .filter(
                RasioOverride.komoditas_id.is_(None),
                RasioOverride.kategori_kode == kat.kode,
                RasioOverride.jenis_rasio == jenis_rasio,
                RasioOverride.wilayah_kode == wilayah_kode,
                RasioOverride.tahun == tahun,
                RasioOverride.berlaku_untuk.in_([berlaku_untuk, "KEDUANYA"]),
            )
            .first()
        )

        rows.append({
            "kategori_kode": kat.kode,
            "kategori_nama": kat.nama,
            "level": kat.level,
            "urutan": kat.urutan,
            "jenis_rasio": jenis_rasio,
            "tahun": tahun,
            "berlaku_untuk": berlaku_untuk,
            "nilai_default": str(nilai_default) if nilai_default is not None else None,
            "nilai_override": str(override.nilai) if override else None,
            "override_id": override.id if override else None,
            "override_keterangan": override.keterangan if override else None,
            "is_overridden": override is not None,
        })

    return rows


@router.get("", summary="Daftar rasio referensi + override per kategori")
def get_rasio(
    jenis_rasio: str = Query(..., pattern="^(OS|WIP|KA|ADJ|CBR)$"),
    tahun: int = Query(..., ge=2008),
    berlaku_untuk: str = Query("ADHB", pattern="^(ADHB|ADHK|KEDUANYA)$"),
    wilayah_kode: str = Query("65"),
    db: Session = Depends(get_db),
):
    return _build_rasio_rows(db, jenis_rasio, tahun, berlaku_untuk, wilayah_kode)


@router.get("/impact-preview", summary="Estimasi dampak perubahan rasio (sebelum save)")
def rasio_impact_preview(
    kategori_kode: str = Query(...),
    jenis_rasio: str = Query(...),
    tahun: int = Query(...),
    berlaku_untuk: str = Query("ADHB"),
    nilai_baru: Decimal = Query(...),
    wilayah_kode: str = Query("65"),
    db: Session = Depends(get_db),
):
    """
    Hitung estimasi perubahan NTB tanpa menyimpan ke database.
    Digunakan untuk menampilkan "dampak sebelum save" di UI.
    """
    # Nilai sekarang
    nilai_lama = get_rasio_safe(
        db, jenis_rasio, berlaku_untuk, tahun,
        kategori_kode=kategori_kode, wilayah_kode=wilayah_kode,
    )

    # Hitung jumlah komoditas terpengaruh
    komoditas_count = (
        db.query(Komoditas)
        .filter(Komoditas.kategori_kode == kategori_kode, Komoditas.aktif.is_(True))
        .count()
    )

    # Ambil NTB saat ini dari pdrb_rekap
    rekap = (
        db.query(PdrbRekap)
        .filter(
            PdrbRekap.kategori_kode == kategori_kode,
            PdrbRekap.wilayah_kode == wilayah_kode,
            PdrbRekap.tahun == tahun,
            PdrbRekap.triwulan.is_(None),
        )
        .first()
    )

    ntb_adhb_sebelum = Decimal(str(rekap.ntb_adhb)) if rekap and rekap.ntb_adhb else None
    ntb_adhk_sebelum = Decimal(str(rekap.ntb_adhk)) if rekap and rekap.ntb_adhk else None

    # Estimasi kasar: perubahan rasio → perubahan proporsional pada NTB
    # Ini adalah estimasi, bukan perhitungan eksak
    delta_rasio = nilai_baru - (nilai_lama or Decimal(0))
    ntb_adhb_delta = None
    ntb_adhk_delta = None
    ntb_adhb_sesudah = None
    ntb_adhk_sesudah = None

    if ntb_adhb_sebelum and nilai_lama and nilai_lama != 0:
        factor = Decimal(1) + delta_rasio
        ntb_adhb_sesudah = ntb_adhb_sebelum * factor
        ntb_adhb_delta = ntb_adhb_sesudah - ntb_adhb_sebelum

    if ntb_adhk_sebelum and nilai_lama and nilai_lama != 0:
        factor = Decimal(1) + delta_rasio
        ntb_adhk_sesudah = ntb_adhk_sebelum * factor
        ntb_adhk_delta = ntb_adhk_sesudah - ntb_adhk_sebelum

    return {
        "komoditas_count": komoditas_count,
        "nilai_lama": str(nilai_lama) if nilai_lama is not None else None,
        "nilai_baru": str(nilai_baru),
        "ntb_adhb_sebelum": str(ntb_adhb_sebelum) if ntb_adhb_sebelum else None,
        "ntb_adhb_sesudah": str(ntb_adhb_sesudah) if ntb_adhb_sesudah else None,
        "ntb_adhb_delta": str(ntb_adhb_delta) if ntb_adhb_delta else None,
        "ntb_adhk_sebelum": str(ntb_adhk_sebelum) if ntb_adhk_sebelum else None,
        "ntb_adhk_sesudah": str(ntb_adhk_sesudah) if ntb_adhk_sesudah else None,
        "ntb_adhk_delta": str(ntb_adhk_delta) if ntb_adhk_delta else None,
    }


@router.post("/override", summary="Set override rasio lokal")
def set_rasio_override(
    body: RasioOverridePatch,
    db: Session = Depends(get_db),
):
    """Simpan atau update override rasio. Trigger cascade untuk kategori terdampak."""
    # Upsert override
    existing = (
        db.query(RasioOverride)
        .filter(
            RasioOverride.komoditas_id.is_(None),
            RasioOverride.kategori_kode == body.kategori_kode,
            RasioOverride.jenis_rasio == body.jenis_rasio,
            RasioOverride.wilayah_kode == body.wilayah_kode,
            RasioOverride.tahun == body.tahun,
            RasioOverride.berlaku_untuk == body.berlaku_untuk,
        )
        .first()
    )

    if existing:
        existing.nilai = body.nilai
        existing.keterangan = body.keterangan
    else:
        new_override = RasioOverride(
            komoditas_id=None,
            kategori_kode=body.kategori_kode,
            jenis_rasio=body.jenis_rasio,
            wilayah_kode=body.wilayah_kode,
            tahun=body.tahun,
            nilai=body.nilai,
            berlaku_untuk=body.berlaku_untuk,
            keterangan=body.keterangan,
        )
        db.add(new_override)

    db.commit()

    task_id = enqueue_cascade(
        trigger_type="rasio_override",
        wilayah_kode=body.wilayah_kode,
        tahun=body.tahun,
        kategori_kode_scope=body.kategori_kode,
    )

    return {"status": "ok", "task_id": task_id, "message": "Override disimpan. Cascade berjalan."}


@router.delete("/override/{override_id}", summary="Reset rasio ke default BPS")
def delete_rasio_override(
    override_id: int,
    db: Session = Depends(get_db),
):
    row = db.get(RasioOverride, override_id)
    if not row:
        raise HTTPException(status_code=404, detail="Override tidak ditemukan")

    wilayah_kode = row.wilayah_kode
    tahun = row.tahun
    kategori_kode = row.kategori_kode

    db.delete(row)
    db.commit()

    task_id = enqueue_cascade(
        trigger_type="rasio_override",
        wilayah_kode=wilayah_kode,
        tahun=tahun,
        kategori_kode_scope=kategori_kode,
    )

    return {"status": "ok", "task_id": task_id, "message": "Override dihapus. Menggunakan default BPS."}
