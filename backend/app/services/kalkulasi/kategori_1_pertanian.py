"""
Contoh Kustomisasi Rumus untuk Kategori 1 (Pertanian, Kehutanan, dan Perikanan)
Anda dapat memodifikasi file ini di kemudian hari jika ada subkategori yang membutuhkan
rumus/metode perhitungan yang berbeda dari standar.
"""
from typing import Optional
from decimal import Decimal
from sqlalchemy.orm import Session

from app.services.kalkulasi.base import HasilSubkategori
from app.services.kalkulasi.standar import hitung_subkategori_standar

def hitung_subkategori_1_1(
    db: Session,
    wilayah_kode: str,
    tahun: int,
    triwulan: Optional[int] = None,
) -> HasilSubkategori:
    """
    Contoh: Kustomisasi perhitungan untuk subkategori 1.1 (Tanaman Pangan).
    Saat ini masih menggunakan rumus standar. Anda bisa menggantinya dengan logika khusus.
    """
    # ... Masukkan logika khusus Anda di sini ...
    # Sebagai contoh awal, kita panggil fungsi standar:
    return hitung_subkategori_standar(db, "1.1", wilayah_kode, tahun, triwulan)

def hitung_subkategori_1_2(
    db: Session,
    wilayah_kode: str,
    tahun: int,
    triwulan: Optional[int] = None,
) -> HasilSubkategori:
    """
    Contoh: Kustomisasi perhitungan untuk subkategori 1.2 (Tanaman Hortikultura).
    """
    return hitung_subkategori_standar(db, "1.2", wilayah_kode, tahun, triwulan)
