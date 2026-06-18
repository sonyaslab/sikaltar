"""
Service: KalkulasiService (VERSI REFAKTOR - Strategy Pattern)
File ini sekarang bertindak sebagai Facade/Dispatcher.
Logika perhitungan dipindahkan ke dalam package `app.services.kalkulasi.*`
agar user dapat menambahkan rumus kustom per kategori/subkategori di kemudian hari.
"""
from __future__ import annotations

from decimal import Decimal
from typing import Optional
from sqlalchemy.orm import Session

# Import struktur data dasar
from app.services.kalkulasi.base import HasilKomoditas, HasilSubkategori, _round6

# Import Dispatcher untuk perhitungan
from app.services.kalkulasi import dispatch_hitung_subkategori
from app.services.kalkulasi.standar import (
    hitung_output_komoditas_standar,
    hitung_kategori_deflasi_standar,
)

from app.models.hasil import LkHasil

def hitung_output_komoditas(
    db: Session,
    komoditas_id: int,
    wilayah_kode: str,
    tahun: int,
    triwulan: Optional[int] = None,
) -> HasilKomoditas:
    """
    Hitung output per komoditas. 
    Saat ini selalu menggunakan standar. Ke depannya bisa dibuat dispatcher juga jika perlu.
    """
    return hitung_output_komoditas_standar(db, komoditas_id, wilayah_kode, tahun, triwulan)

def hitung_subkategori(
    db: Session,
    subkategori_kode: str,
    wilayah_kode: str,
    tahun: int,
    triwulan: Optional[int] = None,
) -> HasilSubkategori:
    """
    Agregasi semua komoditas dalam subkategori → hitung ADJ, KA, NTB.
    Mengarahkan ke Dispatcher (Strategy Pattern).
    """
    return dispatch_hitung_subkategori(db, subkategori_kode, wilayah_kode, tahun, triwulan)

def hitung_kategori_deflasi(
    db: Session,
    kategori_kode: str,
    wilayah_kode: str,
    tahun: int,
    triwulan: Optional[int] = None,
    output_total_adhb: Optional[Decimal] = None,
) -> HasilSubkategori:
    """
    NTB untuk kategori non-produksi dengan metode DEFLASI (tunggal).
    """
    return hitung_kategori_deflasi_standar(db, kategori_kode, wilayah_kode, tahun, triwulan, output_total_adhb)

def simpan_lk_hasil(
    db: Session,
    komoditas_id: int,
    wilayah_kode: str,
    tahun: int,
    triwulan: Optional[int],
    hasil: HasilKomoditas,
    flush: bool = True,
) -> LkHasil:
    """Upsert hasil per-komoditas ke lk_hasil."""
    from datetime import datetime

    row = (
        db.query(LkHasil)
        .filter(
            LkHasil.komoditas_id == komoditas_id,
            LkHasil.wilayah_kode == wilayah_kode,
            LkHasil.tahun == tahun,
            LkHasil.triwulan == triwulan,
        )
        .first()
    )
    if not row:
        row = LkHasil(
            komoditas_id=komoditas_id, wilayah_kode=wilayah_kode,
            tahun=tahun, triwulan=triwulan,
        )
        db.add(row)

    row.output_utama_adhb = hasil.output_utama_adhb
    row.output_ikutan_adhb = hasil.output_ikutan_adhb
    row.wip_adhb = hasil.wip_adhb
    row.output_utama_adhk = hasil.output_utama_adhk
    row.output_ikutan_adhk = hasil.output_ikutan_adhk
    row.wip_adhk = hasil.wip_adhk
    row.is_valid = hasil.error is None
    row.calculated_at = datetime.now()

    if flush:
        db.flush()
    return row