"""
API Router — S2 Lembar Kerja (Worksheet Results)
Read-only endpoints yang menyajikan data hasil perhitungan LK PDRB
dalam format identik sheet BPS.

Endpoints:
  GET /api/s2/worksheet   → Detail per komoditas (LkHasil) + subtotal rekap
  GET /api/s2/rekap       → Rekap subkategori (PdrbRekap) per parent
  GET /api/s2/status      → Kelengkapan data per kategori (untuk sidebar)
  GET /api/s2/compare     → NTB ADHB vs ADHK side-by-side
"""
from __future__ import annotations

from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.hasil import LkHasil, PdrbRekap
from app.models.input_data import InputHarga, InputProduksi
from app.models.kategori_pdrb import KategoriPdrb
from app.models.komoditas import Komoditas
from app.models.rasio import RasioReferensi, RasioOverride
from app.services.rasio_service import get_rasio_safe

router = APIRouter()

TAHUN_DASAR = 2010


def _dec(val) -> Optional[float]:
    """Convert Decimal/None → float (JSON-serializable)."""
    if val is None:
        return None
    return float(val)


def _pct(val) -> Optional[float]:
    """Convert rasio 0–1 → percentage string rounded 4dp."""
    if val is None:
        return None
    return round(float(val) * 100, 4)


def _get_subkategori_kodes(db: Session, parent_kode: str) -> list[str]:
    """Ambil semua sub-subkategori yang langsung di bawah parent_kode."""
    rows = (
        db.query(KategoriPdrb.kode)
        .filter(KategoriPdrb.parent_kode == parent_kode)
        .order_by(KategoriPdrb.urutan)
        .all()
    )
    return [r[0] for r in rows]


def _get_all_descendant_kodes(db: Session, kode: str) -> list[str]:
    """Ambil semua subkategori (rekursif) di bawah kode."""
    result = []
    children = _get_subkategori_kodes(db, kode)
    for c in children:
        result.append(c)
        result.extend(_get_all_descendant_kodes(db, c))
    return result


# ─── /api/s2/worksheet ─────────────────────────────────────────────────────────

@router.get("/worksheet", summary="Worksheet detail LK per subkategori")
def get_worksheet(
    wilayah_kode: str = Query("65"),
    tahun: int = Query(..., ge=2008),
    triwulan: Optional[int] = Query(None, ge=1, le=4),
    kategori_kode: str = Query(..., description="Kode subkategori level 3 (mis: '1.1.a')"),
    db: Session = Depends(get_db),
):
    """
    Kembalikan data worksheet lengkap untuk satu subkategori:
    - Baris per komoditas dengan semua komponen ADHB & ADHK
    - Rasio OS, WIP, KA, ADJ yang digunakan
    - Subtotal subkategori dari PdrbRekap
    - Status kelengkapan setiap baris
    """
    # Ambil metadata kategori
    kat = db.query(KategoriPdrb).filter(KategoriPdrb.kode == kategori_kode).first()

    # Ambil komoditas aktif dalam subkategori ini
    komoditas_list = (
        db.query(Komoditas)
        .filter(Komoditas.kategori_kode == kategori_kode, Komoditas.aktif.is_(True))
        .order_by(Komoditas.nama)
        .all()
    )

    # Ambil semua LkHasil sekaligus (batch)
    kom_ids = [k.id for k in komoditas_list]
    lk_map: dict[int, LkHasil] = {}
    if kom_ids:
        lk_rows = (
            db.query(LkHasil)
            .filter(
                LkHasil.komoditas_id.in_(kom_ids),
                LkHasil.wilayah_kode == wilayah_kode,
                LkHasil.tahun == tahun,
                LkHasil.triwulan == triwulan,
            )
            .all()
        )
        lk_map = {r.komoditas_id: r for r in lk_rows}

    # Ambil input produksi dan harga untuk kelengkapan data
    prod_ids = set(
        r[0] for r in db.query(InputProduksi.komoditas_id)
        .filter(
            InputProduksi.komoditas_id.in_(kom_ids),
            InputProduksi.wilayah_kode == wilayah_kode,
            InputProduksi.tahun == tahun,
            InputProduksi.triwulan == triwulan,
            InputProduksi.kuantum.is_not(None),
        ).all()
    )
    harga_ids = set(
        r[0] for r in db.query(InputHarga.komoditas_id)
        .filter(
            InputHarga.komoditas_id.in_(kom_ids),
            InputHarga.wilayah_kode == wilayah_kode,
            InputHarga.tahun == tahun,
            InputHarga.harga_berlaku.is_not(None),
        ).all()
    )

    # Build rows
    rows = []
    for kom in komoditas_list:
        lk = lk_map.get(kom.id)
        has_prod = kom.id in prod_ids
        has_harga = kom.id in harga_ids
        has_data = has_prod and has_harga
        has_error = lk and lk.ntb_adhb is not None and float(lk.ntb_adhb) < 0

        # Ambil rasio yang digunakan (untuk display di kolom rasio)
        rasio_os_b = _dec(get_rasio_safe(db, "OS", "ADHB", tahun,
            kategori_kode=kategori_kode, wilayah_kode=wilayah_kode))
        rasio_wip_b = _dec(get_rasio_safe(db, "WIP", "ADHB", tahun,
            kategori_kode=kategori_kode, wilayah_kode=wilayah_kode))
        rasio_ka_b = _dec(get_rasio_safe(db, "KA", "ADHB", tahun,
            kategori_kode=kategori_kode, wilayah_kode=wilayah_kode))

        rasio_os_k = _dec(get_rasio_safe(db, "OS", "ADHK", TAHUN_DASAR,
            kategori_kode=kategori_kode, wilayah_kode=wilayah_kode))
        rasio_wip_k = _dec(get_rasio_safe(db, "WIP", "ADHK", TAHUN_DASAR,
            kategori_kode=kategori_kode, wilayah_kode=wilayah_kode))
        rasio_ka_k = _dec(get_rasio_safe(db, "KA", "ADHK", TAHUN_DASAR,
            kategori_kode=kategori_kode, wilayah_kode=wilayah_kode))

        # Ambil input harga untuk display kuantum & harga
        prod_row = (
            db.query(InputProduksi)
            .filter(
                InputProduksi.komoditas_id == kom.id,
                InputProduksi.wilayah_kode == wilayah_kode,
                InputProduksi.tahun == tahun,
                InputProduksi.triwulan == triwulan,
            ).first()
        )
        harga_berlaku_row = (
            db.query(InputHarga)
            .filter(
                InputHarga.komoditas_id == kom.id,
                InputHarga.wilayah_kode == wilayah_kode,
                InputHarga.tahun == tahun,
                InputHarga.triwulan == triwulan,
            ).first()
        )
        harga_2010_row = (
            db.query(InputHarga)
            .filter(
                InputHarga.komoditas_id == kom.id,
                InputHarga.wilayah_kode == wilayah_kode,
                InputHarga.tahun == TAHUN_DASAR,
                InputHarga.triwulan.is_(None),
            ).first()
        )

        rows.append({
            "komoditas_id":        kom.id,
            "komoditas_nama":      kom.nama,
            "wujud_produksi":      kom.wujud_produksi,
            "satuan_produksi":     kom.satuan_produksi,
            "satuan_harga":        kom.satuan_harga,
            "faktor_konversi":     _dec(kom.faktor_konversi),
            # Kelengkapan
            "has_produksi":        has_prod,
            "has_harga":           has_harga,
            "has_data":            has_data,
            "has_error":           bool(has_error),
            "is_valid":            lk.is_valid if lk else None,
            # Input
            "kuantum":             _dec(prod_row.kuantum) if prod_row else None,
            "harga_berlaku":       _dec(harga_berlaku_row.harga_berlaku) if harga_berlaku_row else None,
            "harga_konstan_2010":  _dec(harga_2010_row.harga_konstan_2010) if harga_2010_row else None,
            # ADHB
            "output_utama_adhb":   _dec(lk.output_utama_adhb) if lk else None,
            "rasio_os_adhb":       rasio_os_b,
            "output_ikutan_adhb":  _dec(lk.output_ikutan_adhb) if lk else None,
            "rasio_wip_adhb":      rasio_wip_b,
            "wip_adhb":            _dec(lk.wip_adhb) if lk else None,
            "output_primer_adhb":  _dec(lk.output_utama_adhb + lk.output_ikutan_adhb + lk.wip_adhb)
                                   if lk and lk.output_utama_adhb else None,
            "rasio_ka_adhb":       rasio_ka_b,
            "ka_adhb":             _dec(lk.ka_adhb) if lk else None,
            "ntb_adhb":            _dec(lk.ntb_adhb) if lk else None,
            # ADHK
            "output_utama_adhk":   _dec(lk.output_utama_adhk) if lk else None,
            "rasio_os_adhk":       rasio_os_k,
            "output_ikutan_adhk":  _dec(lk.output_ikutan_adhk) if lk else None,
            "rasio_wip_adhk":      rasio_wip_k,
            "wip_adhk":            _dec(lk.wip_adhk) if lk else None,
            "output_primer_adhk":  _dec(lk.output_utama_adhk + lk.output_ikutan_adhk + lk.wip_adhk)
                                   if lk and lk.output_utama_adhk else None,
            "rasio_ka_adhk":       rasio_ka_k,
            "ka_adhk":             _dec(lk.ka_adhk) if lk else None,
            "ntb_adhk":            _dec(lk.ntb_adhk) if lk else None,
        })

    # Subtotal dari PdrbRekap
    rekap = (
        db.query(PdrbRekap)
        .filter(
            PdrbRekap.kategori_kode == kategori_kode,
            PdrbRekap.wilayah_kode == wilayah_kode,
            PdrbRekap.tahun == tahun,
            PdrbRekap.triwulan == triwulan,
        ).first()
    )

    subtotal = None
    if rekap:
        subtotal = {
            "output_primer_adhb":   _dec(rekap.output_primer_adhb),
            "output_sekunder_adhb": _dec(rekap.output_sekunder_adhb),
            "output_lainnya_adhb":  _dec(rekap.output_lainnya_adhb),
            "output_total_adhb":    _dec(rekap.output_total_adhb),
            "ka_adhb":              _dec(rekap.ka_adhb),
            "ntb_sebelum_adj_adhb": _dec(rekap.ntb_sebelum_adj_adhb),
            "adjustment_adhb":      _dec(rekap.adjustment_adhb),
            "ntb_adhb":             _dec(rekap.ntb_adhb),
            "output_primer_adhk":   _dec(rekap.output_primer_adhk),
            "output_sekunder_adhk": _dec(rekap.output_sekunder_adhk),
            "output_lainnya_adhk":  _dec(rekap.output_lainnya_adhk),
            "output_total_adhk":    _dec(rekap.output_total_adhk),
            "ka_adhk":              _dec(rekap.ka_adhk),
            "ntb_sebelum_adj_adhk": _dec(rekap.ntb_sebelum_adj_adhk),
            "adjustment_adhk":      _dec(rekap.adjustment_adhk),
            "ntb_adhk":             _dec(rekap.ntb_adhk),
            "distribusi_pct":       _dec(rekap.distribusi_pct),
            "laju_pertumbuhan_pct": _dec(rekap.laju_pertumbuhan_pct),
            "indeks_implisit":      _dec(rekap.indeks_implisit),
            "laju_implisit_pct":    _dec(rekap.laju_implisit_pct),
            "calculated_at":        rekap.calculated_at.isoformat() if rekap.calculated_at else None,
        }

    return {
        "kategori": {
            "kode":       kat.kode if kat else kategori_kode,
            "nama":       kat.nama if kat else "?",
            "metode_adhb": kat.metode_adhb if kat else None,
            "metode_adhk": kat.metode_adhk if kat else None,
        },
        "wilayah_kode":    wilayah_kode,
        "tahun":           tahun,
        "triwulan":        triwulan,
        "komoditas_count": len(rows),
        "rows":            rows,
        "subtotal":        subtotal,
    }


# ─── /api/s2/rekap ─────────────────────────────────────────────────────────────

@router.get("/rekap", summary="Rekap NTB per subkategori (tabel ringkasan)")
def get_rekap(
    wilayah_kode: str = Query("65"),
    tahun: int = Query(..., ge=2008),
    triwulan: Optional[int] = Query(None, ge=1, le=4),
    parent_kode: str = Query(..., description="Kode parent kategori, mis: '1.1'"),
    db: Session = Depends(get_db),
):
    """
    Rekap NTB ADHB & ADHK + indikator turunan per subkategori.
    Digunakan untuk tabel 'REKAP 1.1 Pertanian...' di bawah detail komoditas.
    """
    parent_kat = db.query(KategoriPdrb).filter(KategoriPdrb.kode == parent_kode).first()
    child_kodes = _get_subkategori_kodes(db, parent_kode)

    rows = []
    for i, kode in enumerate(child_kodes, 1):
        kat = db.query(KategoriPdrb).filter(KategoriPdrb.kode == kode).first()
        rekap = (
            db.query(PdrbRekap)
            .filter(
                PdrbRekap.kategori_kode == kode,
                PdrbRekap.wilayah_kode == wilayah_kode,
                PdrbRekap.tahun == tahun,
                PdrbRekap.triwulan == triwulan,
            ).first()
        )
        rows.append({
            "no":                   i,
            "kategori_kode":        kode,
            "kategori_nama":        kat.nama if kat else kode,
            "ntb_sebelum_adj_adhb": _dec(rekap.ntb_sebelum_adj_adhb) if rekap else None,
            "adjustment_adhb":      _dec(rekap.adjustment_adhb) if rekap else None,
            "ntb_adhb":             _dec(rekap.ntb_adhb) if rekap else None,
            "ntb_sebelum_adj_adhk": _dec(rekap.ntb_sebelum_adj_adhk) if rekap else None,
            "adjustment_adhk":      _dec(rekap.adjustment_adhk) if rekap else None,
            "ntb_adhk":             _dec(rekap.ntb_adhk) if rekap else None,
            "output_total_adhb":    _dec(rekap.output_total_adhb) if rekap else None,
            "output_total_adhk":    _dec(rekap.output_total_adhk) if rekap else None,
            "ka_adhb":              _dec(rekap.ka_adhb) if rekap else None,
            "ka_adhk":              _dec(rekap.ka_adhk) if rekap else None,
            "distribusi_pct":       _dec(rekap.distribusi_pct) if rekap else None,
            "laju_pertumbuhan_pct": _dec(rekap.laju_pertumbuhan_pct) if rekap else None,
            "indeks_implisit":      _dec(rekap.indeks_implisit) if rekap else None,
        })

    # Total dari parent rekap
    parent_rekap = (
        db.query(PdrbRekap)
        .filter(
            PdrbRekap.kategori_kode == parent_kode,
            PdrbRekap.wilayah_kode == wilayah_kode,
            PdrbRekap.tahun == tahun,
            PdrbRekap.triwulan == triwulan,
        ).first()
    )

    return {
        "parent_kode":   parent_kode,
        "parent_nama":   parent_kat.nama if parent_kat else parent_kode,
        "wilayah_kode":  wilayah_kode,
        "tahun":         tahun,
        "triwulan":      triwulan,
        "rows":          rows,
        "total": {
            "ntb_adhb":             _dec(parent_rekap.ntb_adhb) if parent_rekap else None,
            "ntb_adhk":             _dec(parent_rekap.ntb_adhk) if parent_rekap else None,
            "output_total_adhb":    _dec(parent_rekap.output_total_adhb) if parent_rekap else None,
            "output_total_adhk":    _dec(parent_rekap.output_total_adhk) if parent_rekap else None,
            "distribusi_pct":       _dec(parent_rekap.distribusi_pct) if parent_rekap else None,
            "laju_pertumbuhan_pct": _dec(parent_rekap.laju_pertumbuhan_pct) if parent_rekap else None,
            "indeks_implisit":      _dec(parent_rekap.indeks_implisit) if parent_rekap else None,
        } if parent_rekap else None,
    }


# ─── /api/s2/status ────────────────────────────────────────────────────────────

@router.get("/status", summary="Status kelengkapan data per kategori (untuk sidebar)")
def get_status(
    wilayah_kode: str = Query("65"),
    tahun: int = Query(..., ge=2008),
    triwulan: Optional[int] = Query(None, ge=1, le=4),
    db: Session = Depends(get_db),
):
    """
    Kembalikan status kelengkapan per subkategori untuk sidebar navigasi.
    Status: 'lengkap' | 'parsial' | 'kosong'
    """
    all_kat = (
        db.query(KategoriPdrb)
        .filter(KategoriPdrb.level >= 2)
        .order_by(KategoriPdrb.urutan)
        .all()
    )

    result = {}
    for kat in all_kat:
        kom_list = (
            db.query(Komoditas.id)
            .filter(Komoditas.kategori_kode == kat.kode, Komoditas.aktif.is_(True))
            .all()
        )
        total_kom = len(kom_list)
        if total_kom == 0:
            result[kat.kode] = {
                "kode": kat.kode, "nama": kat.nama, "level": kat.level,
                "parent_kode": kat.parent_kode, "urutan": kat.urutan,
                "total_komoditas": 0, "terisi": 0,
                "status": "kosong", "has_ntb": False,
            }
            continue

        kom_ids = [r[0] for r in kom_list]

        # Cek berapa yang punya LkHasil valid
        terisi = (
            db.query(func.count(LkHasil.id))
            .filter(
                LkHasil.komoditas_id.in_(kom_ids),
                LkHasil.wilayah_kode == wilayah_kode,
                LkHasil.tahun == tahun,
                LkHasil.triwulan == triwulan,
                LkHasil.ntb_adhb.is_not(None),
                LkHasil.is_valid.is_(True),
            ).scalar() or 0
        )

        # Cek apakah ada NTB di pdrb_rekap
        rekap = (
            db.query(PdrbRekap.ntb_adhb)
            .filter(
                PdrbRekap.kategori_kode == kat.kode,
                PdrbRekap.wilayah_kode == wilayah_kode,
                PdrbRekap.tahun == tahun,
                PdrbRekap.triwulan == triwulan,
            ).first()
        )

        status = "kosong"
        if terisi == total_kom:
            status = "lengkap"
        elif terisi > 0:
            status = "parsial"

        result[kat.kode] = {
            "kode":             kat.kode,
            "nama":             kat.nama,
            "level":            kat.level,
            "parent_kode":      kat.parent_kode,
            "urutan":           kat.urutan,
            "total_komoditas":  total_kom,
            "terisi":           terisi,
            "status":           status,
            "has_ntb":          rekap is not None and rekap[0] is not None,
            "ntb_adhb":         _dec(rekap[0]) if rekap and rekap[0] else None,
        }

    return result


# ─── /api/s2/compare ───────────────────────────────────────────────────────────

@router.get("/compare", summary="Perbandingan NTB ADHB vs ADHK side-by-side")
def get_compare(
    wilayah_kode: str = Query("65"),
    tahun: int = Query(..., ge=2008),
    triwulan: Optional[int] = Query(None, ge=1, le=4),
    parent_kode: str = Query("", description="Filter ke subkategori tertentu. Kosong = semua level 1-2"),
    db: Session = Depends(get_db),
):
    """
    Side-by-side perbandingan NTB ADHB vs ADHK dengan indeks implisit.
    Digunakan untuk panel 'Bandingkan ADHB vs ADHK'.
    """
    level_filter = [1, 2] if not parent_kode else [2, 3]
    q = db.query(KategoriPdrb).filter(KategoriPdrb.level.in_(level_filter))
    if parent_kode:
        all_child = _get_all_descendant_kodes(db, parent_kode)
        q = q.filter(KategoriPdrb.kode.in_([parent_kode] + all_child))
    kat_list = q.order_by(KategoriPdrb.urutan).all()

    rows = []
    for kat in kat_list:
        rekap = (
            db.query(PdrbRekap)
            .filter(
                PdrbRekap.kategori_kode == kat.kode,
                PdrbRekap.wilayah_kode == wilayah_kode,
                PdrbRekap.tahun == tahun,
                PdrbRekap.triwulan == triwulan,
            ).first()
        )
        rows.append({
            "kategori_kode":        kat.kode,
            "kategori_nama":        kat.nama,
            "level":                kat.level,
            "ntb_adhb":             _dec(rekap.ntb_adhb) if rekap else None,
            "ntb_adhk":             _dec(rekap.ntb_adhk) if rekap else None,
            "indeks_implisit":      _dec(rekap.indeks_implisit) if rekap else None,
            "laju_pertumbuhan_pct": _dec(rekap.laju_pertumbuhan_pct) if rekap else None,
            "distribusi_pct":       _dec(rekap.distribusi_pct) if rekap else None,
        })

    return {
        "wilayah_kode":  wilayah_kode,
        "tahun":         tahun,
        "triwulan":      triwulan,
        "rows":          rows,
    }
