"""
Service: RasioService
Mengambil rasio kalkulasi dengan sistem prioritas:
  1. rasio_override  → penyesuaian lokal per wilayah (prioritas tertinggi)
  2. rasio_referensi → default nasional dari SUT 2019 BPS
  3. RasioTidakDitemukanError jika tidak ada sama sekali

Logika fallback scope (dari sempit ke luas):
  komoditas_id spesifik → kategori subkategori → kategori parent
"""
from __future__ import annotations

from decimal import Decimal
from typing import Optional

from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from app.models.rasio import RasioOverride, RasioReferensi


class RasioTidakDitemukanError(Exception):
    """Raised ketika rasio tidak ditemukan setelah semua lookup."""

    def __init__(self, komoditas_id, kategori_kode, jenis_rasio, tahun, berlaku_untuk, wilayah_kode):
        self.komoditas_id = komoditas_id
        self.kategori_kode = kategori_kode
        self.jenis_rasio = jenis_rasio
        self.tahun = tahun
        self.berlaku_untuk = berlaku_untuk
        self.wilayah_kode = wilayah_kode
        super().__init__(
            f"Rasio tidak ditemukan: jenis={jenis_rasio!r}, tahun={tahun}, "
            f"berlaku={berlaku_untuk!r}, komoditas_id={komoditas_id}, "
            f"kategori={kategori_kode!r}, wilayah={wilayah_kode!r}. "
            f"Periksa tabel rasio_referensi atau tambahkan rasio_override."
        )


def _berlaku_match(berlaku_untuk_col, berlaku_untuk: str):
    """SQLAlchemy filter: cocokkan 'ADHB', 'ADHK', atau 'KEDUANYA'."""
    return or_(
        berlaku_untuk_col == berlaku_untuk,
        berlaku_untuk_col == "KEDUANYA",
    )


def get_rasio(
    db: Session,
    jenis_rasio: str,
    berlaku_untuk: str,
    tahun: int,
    komoditas_id: Optional[int] = None,
    kategori_kode: Optional[str] = None,
    wilayah_kode: Optional[str] = None,
) -> Decimal:
    """
    Ambil nilai rasio dengan prioritas:
      1. rasio_override (spesifik wilayah + komoditas)
      2. rasio_override (spesifik wilayah + kategori)
      3. rasio_referensi (komoditas spesifik)
      4. rasio_referensi (kategori subkategori)
      5. rasio_referensi (kategori parent, mis: '1.1' → '1')
      6. RasioTidakDitemukanError

    Args:
        db: SQLAlchemy Session
        jenis_rasio: 'OS' | 'WIP' | 'KA' | 'ADJ' | 'CBR'
        berlaku_untuk: 'ADHB' | 'ADHK'
        tahun: Tahun kalkulasi
        komoditas_id: ID komoditas (opsional, untuk scope per komoditas)
        kategori_kode: Kode subkategori komoditas (mis: '1.1.a')
        wilayah_kode: Kode wilayah untuk cek override (opsional)

    Returns:
        Decimal: Nilai rasio

    Raises:
        RasioTidakDitemukanError: Jika rasio tidak ditemukan
    """
    berlaku_filter = _berlaku_match

    # ── Prioritas 1 & 2: rasio_override per wilayah ───────────────────────
    if wilayah_kode:
        # 1a. Override spesifik komoditas
        if komoditas_id:
            row = (
                db.query(RasioOverride)
                .filter(
                    RasioOverride.komoditas_id == komoditas_id,
                    RasioOverride.jenis_rasio == jenis_rasio,
                    RasioOverride.wilayah_kode == wilayah_kode,
                    RasioOverride.tahun == tahun,
                    berlaku_filter(RasioOverride.berlaku_untuk, berlaku_untuk),
                )
                .first()
            )
            if row:
                return Decimal(str(row.nilai))

        # 1b. Override spesifik kategori
        if kategori_kode:
            row = (
                db.query(RasioOverride)
                .filter(
                    RasioOverride.komoditas_id.is_(None),
                    RasioOverride.kategori_kode == kategori_kode,
                    RasioOverride.jenis_rasio == jenis_rasio,
                    RasioOverride.wilayah_kode == wilayah_kode,
                    RasioOverride.tahun == tahun,
                    berlaku_filter(RasioOverride.berlaku_untuk, berlaku_untuk),
                )
                .first()
            )
            if row:
                return Decimal(str(row.nilai))

    # ── Prioritas 3: rasio_referensi spesifik komoditas ───────────────────
    if komoditas_id:
        row = (
            db.query(RasioReferensi)
            .filter(
                RasioReferensi.komoditas_id == komoditas_id,
                RasioReferensi.jenis_rasio == jenis_rasio,
                RasioReferensi.tahun == tahun,
                berlaku_filter(RasioReferensi.berlaku_untuk, berlaku_untuk),
            )
            .first()
        )
        if row:
            return Decimal(str(row.nilai))

    # ── Prioritas 4: rasio_referensi per kategori (scope subkategori) ─────
    if kategori_kode:
        row = (
            db.query(RasioReferensi)
            .filter(
                RasioReferensi.komoditas_id.is_(None),
                RasioReferensi.kategori_kode == kategori_kode,
                RasioReferensi.jenis_rasio == jenis_rasio,
                RasioReferensi.tahun == tahun,
                berlaku_filter(RasioReferensi.berlaku_untuk, berlaku_untuk),
            )
            .first()
        )
        if row:
            return Decimal(str(row.nilai))

        # ── Prioritas 5: Fallback ke parent kategori ──────────────────────
        # Contoh: '1.1.a' → coba '1.1' → coba '1'
        parts = kategori_kode.split(".")
        for depth in range(len(parts) - 1, 0, -1):
            parent_kode = ".".join(parts[:depth])
            row = (
                db.query(RasioReferensi)
                .filter(
                    RasioReferensi.komoditas_id.is_(None),
                    RasioReferensi.kategori_kode == parent_kode,
                    RasioReferensi.jenis_rasio == jenis_rasio,
                    RasioReferensi.tahun == tahun,
                    berlaku_filter(RasioReferensi.berlaku_untuk, berlaku_untuk),
                )
                .first()
            )
            if row:
                return Decimal(str(row.nilai))

    # ── Tidak ditemukan ───────────────────────────────────────────────────
    raise RasioTidakDitemukanError(
        komoditas_id=komoditas_id,
        kategori_kode=kategori_kode,
        jenis_rasio=jenis_rasio,
        tahun=tahun,
        berlaku_untuk=berlaku_untuk,
        wilayah_kode=wilayah_kode,
    )


def get_rasio_safe(
    db: Session,
    jenis_rasio: str,
    berlaku_untuk: str,
    tahun: int,
    komoditas_id: Optional[int] = None,
    kategori_kode: Optional[str] = None,
    wilayah_kode: Optional[str] = None,
    default: Optional[Decimal] = None,
) -> Optional[Decimal]:
    """
    Versi aman dari get_rasio — kembalikan `default` jika tidak ditemukan.
    Gunakan di konteks di mana missing rasio bukan error fatal (mis: preview).
    """
    try:
        return get_rasio(
            db, jenis_rasio, berlaku_untuk, tahun,
            komoditas_id=komoditas_id,
            kategori_kode=kategori_kode,
            wilayah_kode=wilayah_kode,
        )
    except RasioTidakDitemukanError:
        return default
