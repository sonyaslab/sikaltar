"""
Service: AgregatService
Agregasi tahunan dari triwulanan, dan perhitungan indikator turunan PDRB:
  - distribusi_pct      : share terhadap total PDRB ADHB
  - laju_pertumbuhan_pct: growth rate NTB ADHK year-on-year
  - indeks_implisit     : (NTB_ADHB / NTB_ADHK) × 100
  - laju_implisit_pct   : growth rate indeks implisit YoY
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP, DivisionByZero, InvalidOperation
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.hasil import PdrbRekap
from app.services.kalkulasi_service import _round6, HasilSubkategori

ROUND4 = Decimal("0.0001")


def _round4(value: Decimal) -> Decimal:
    """Pembulatan 4 desimal untuk indikator turunan (persen)."""
    return value.quantize(ROUND4, rounding=ROUND_HALF_UP)


def _safe_div(numerator: Decimal, denominator: Decimal, default: Decimal = Decimal(0)) -> Decimal:
    """Pembagian aman — kembalikan default jika denominator = 0."""
    try:
        if denominator == 0:
            return default
        return numerator / denominator
    except (DivisionByZero, InvalidOperation):
        return default


# ─────────────────────────────────────────────────────────────────────────────

def agregasi_tahunan(
    db: Session,
    kategori_kode: str,
    wilayah_kode: str,
    tahun: int,
) -> Optional[PdrbRekap]:
    """
    Jumlahkan 4 triwulan → simpan sebagai record tahunan (triwulan=NULL).

    Alur:
      1. Cari rekap triwulan 1-4 di pdrb_rekap
      2. Jika semua 4 triwulan ada → SUM semua komponen
      3. Simpan/update record dengan triwulan=NULL
      4. Kembalikan record tahunan

    Jika data tersedia langsung tahunan (triwulan=NULL), record itu tidak ditimpa.
    """
    triwulan_rows = (
        db.query(PdrbRekap)
        .filter(
            PdrbRekap.kategori_kode == kategori_kode,
            PdrbRekap.wilayah_kode == wilayah_kode,
            PdrbRekap.tahun == tahun,
            PdrbRekap.triwulan.in_([1, 2, 3, 4]),
        )
        .all()
    )

    if not triwulan_rows:
        return None

    # Inisialisasi akumulator
    komponen = [
        "output_primer_adhb", "output_sekunder_adhb", "output_lainnya_adhb",
        "output_total_adhb", "ka_adhb", "ntb_sebelum_adj_adhb", "adjustment_adhb", "ntb_adhb",
        "output_primer_adhk", "output_sekunder_adhk", "output_lainnya_adhk",
        "output_total_adhk", "ka_adhk", "ntb_sebelum_adj_adhk", "adjustment_adhk", "ntb_adhk",
    ]
    totals = {k: Decimal(0) for k in komponen}

    for row in triwulan_rows:
        for k in komponen:
            val = getattr(row, k, None)
            if val is not None:
                totals[k] += Decimal(str(val))

    # Simpan / update record tahunan
    tahunan = (
        db.query(PdrbRekap)
        .filter(
            PdrbRekap.kategori_kode == kategori_kode,
            PdrbRekap.wilayah_kode == wilayah_kode,
            PdrbRekap.tahun == tahun,
            PdrbRekap.triwulan.is_(None),
        )
        .first()
    )
    if not tahunan:
        tahunan = PdrbRekap(
            kategori_kode=kategori_kode,
            wilayah_kode=wilayah_kode,
            tahun=tahun,
            triwulan=None,
        )
        db.add(tahunan)

    for k, v in totals.items():
        setattr(tahunan, k, _round6(v))

    db.flush()
    return tahunan


def simpan_rekap_dari_hasil(
    db: Session,
    hasil: HasilSubkategori,
    flush: bool = True,
) -> PdrbRekap:
    """
    Simpan HasilSubkategori ke tabel pdrb_rekap (upsert).
    output_lainnya = WIP + ADJ (digabung karena di rekap tidak dipisah).
    """
    from datetime import datetime

    row = (
        db.query(PdrbRekap)
        .filter(
            PdrbRekap.kategori_kode == hasil.subkategori_kode,
            PdrbRekap.wilayah_kode == hasil.wilayah_kode,
            PdrbRekap.tahun == hasil.tahun,
            PdrbRekap.triwulan == hasil.triwulan,
        )
        .first()
    )
    if not row:
        row = PdrbRekap(
            kategori_kode=hasil.subkategori_kode,
            wilayah_kode=hasil.wilayah_kode,
            tahun=hasil.tahun,
            triwulan=hasil.triwulan,
        )
        db.add(row)

    row.output_primer_adhb = hasil.output_primer_adhb
    row.output_sekunder_adhb = hasil.output_sekunder_adhb
    row.output_lainnya_adhb = Decimal(0)   # Dikosongkan karena tidak ada ADJ rasio
    row.output_total_adhb = hasil.output_total_adhb
    row.ka_adhb = hasil.ka_adhb
    row.ntb_sebelum_adj_adhb = hasil.ntb_sebelum_adj_adhb
    row.adjustment_adhb = hasil.adj_adhb
    row.ntb_adhb = hasil.ntb_adhb

    row.output_primer_adhk = hasil.output_primer_adhk
    row.output_sekunder_adhk = hasil.output_sekunder_adhk
    row.output_lainnya_adhk = Decimal(0)
    row.output_total_adhk = hasil.output_total_adhk
    row.ka_adhk = hasil.ka_adhk
    row.ntb_sebelum_adj_adhk = hasil.ntb_sebelum_adj_adhk
    row.adjustment_adhk = hasil.adj_adhk
    row.ntb_adhk = hasil.ntb_adhk
    row.calculated_at = datetime.now()

    if flush:
        db.flush()
    return row


def hitung_indikator_turunan(
    db: Session,
    kategori_kode: str,
    wilayah_kode: str,
    tahun: int,
    triwulan: Optional[int] = None,
) -> Optional[PdrbRekap]:
    """
    Hitung dan simpan indikator turunan ke pdrb_rekap:

      distribusi_pct     = (ntb_adhb_kategori / ntb_adhb_TOTAL_PDRB) × 100
      laju_pertumbuhan   = ((ntb_adhk_t / ntb_adhk_{t-1}) − 1) × 100
      indeks_implisit    = (ntb_adhb / ntb_adhk) × 100
      laju_implisit_pct  = ((implisit_t / implisit_{t-1}) − 1) × 100

    Dipanggil setelah semua subkategori selesai dihitung.
    """
    row = (
        db.query(PdrbRekap)
        .filter(
            PdrbRekap.kategori_kode == kategori_kode,
            PdrbRekap.wilayah_kode == wilayah_kode,
            PdrbRekap.tahun == tahun,
            PdrbRekap.triwulan == triwulan,
        )
        .first()
    )
    if not row or not row.ntb_adhb or not row.ntb_adhk:
        return row

    ntb_b = Decimal(str(row.ntb_adhb))
    ntb_k = Decimal(str(row.ntb_adhk))

    # ── distribusi_pct ────────────────────────────────────────────────────
    # Total NTB ADHB dari kategori 'TOTAL' atau sum semua kategori level 1
    total_ntb_b = (
        db.query(func.sum(PdrbRekap.ntb_adhb))
        .filter(
            PdrbRekap.wilayah_kode == wilayah_kode,
            PdrbRekap.tahun == tahun,
            PdrbRekap.triwulan == triwulan,
            PdrbRekap.kategori_kode.in_(
                [str(i) for i in range(1, 18)]   # kategori 1 s/d 17
            ),
        )
        .scalar()
    )

    if total_ntb_b and Decimal(str(total_ntb_b)) != 0:
        row.distribusi_pct = _round4(
            _safe_div(ntb_b, Decimal(str(total_ntb_b))) * Decimal(100)
        )

    # ── indeks_implisit ───────────────────────────────────────────────────
    if ntb_k != 0:
        indeks = _round4(_safe_div(ntb_b, ntb_k) * Decimal(100))
        row.indeks_implisit = indeks
    else:
        indeks = None

    # ── laju_pertumbuhan_pct (NTB ADHK YoY) ──────────────────────────────
    prev_row = (
        db.query(PdrbRekap)
        .filter(
            PdrbRekap.kategori_kode == kategori_kode,
            PdrbRekap.wilayah_kode == wilayah_kode,
            PdrbRekap.tahun == tahun - 1,
            PdrbRekap.triwulan == triwulan,
        )
        .first()
    )
    if prev_row and prev_row.ntb_adhk:
        ntb_k_prev = Decimal(str(prev_row.ntb_adhk))
        if ntb_k_prev != 0:
            row.laju_pertumbuhan_pct = _round4(
                (_safe_div(ntb_k, ntb_k_prev) - Decimal(1)) * Decimal(100)
            )

        # ── laju_implisit_pct ─────────────────────────────────────────────
        if indeks is not None and prev_row.indeks_implisit:
            indeks_prev = Decimal(str(prev_row.indeks_implisit))
            if indeks_prev != 0:
                row.laju_implisit_pct = _round4(
                    (_safe_div(indeks, indeks_prev) - Decimal(1)) * Decimal(100)
                )

    db.flush()
    return row


def hitung_semua_indikator_wilayah(
    db: Session,
    wilayah_kode: str,
    tahun: int,
    triwulan: Optional[int] = None,
) -> dict:
    """
    Hitung indikator turunan untuk SEMUA kategori di satu wilayah sekaligus.
    Dipanggil sekali setelah semua kategori selesai di-recalculate.

    Returns:
        dict: { kategori_kode: PdrbRekap }
    """
    hasil = {}
    # Ambil semua kode kategori yang ada data untuk periode ini
    kode_list = (
        db.query(PdrbRekap.kategori_kode)
        .filter(
            PdrbRekap.wilayah_kode == wilayah_kode,
            PdrbRekap.tahun == tahun,
            PdrbRekap.triwulan == triwulan,
            PdrbRekap.ntb_adhb.is_not(None),
        )
        .distinct()
        .all()
    )
    for (kode,) in kode_list:
        row = hitung_indikator_turunan(db, kode, wilayah_kode, tahun, triwulan)
        if row:
            hasil[kode] = row

    db.commit()
    return hasil
