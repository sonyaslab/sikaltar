"""
Registry dan Dispatcher Kalkulasi PDRB
Sistem ini menggunakan pola Strategy agar setiap subkategori bisa memiliki
rumus perhitungannya masing-masing.
"""
from typing import Optional, Callable
from sqlalchemy.orm import Session
from decimal import Decimal

from app.services.kalkulasi.base import HasilSubkategori
from app.services.kalkulasi.standar import hitung_subkategori_standar
from app.services.kalkulasi.kategori_1_pertanian import hitung_subkategori_1_1, hitung_subkategori_1_2

# Tipe untuk fungsi kalkulasi subkategori
KalkulasiFunc = Callable[[Session, str, str, int, Optional[int]], HasilSubkategori]

# REGISTRY RUMUS KUSTOM PER SUBKATEGORI
# Daftarkan fungsi khusus Anda di sini. Jika kode subkategori tidak ada di kamus ini,
# sistem otomatis menggunakan `hitung_subkategori_standar`.
REGISTRY_RUMUS_SUBKATEGORI = {
    "1.1": hitung_subkategori_1_1,
    "1.2": hitung_subkategori_1_2,
    # "1.3": hitung_subkategori_1_3,  # Contoh jika ada
    # "1.4": hitung_subkategori_1_4,
}

def dispatch_hitung_subkategori(
    db: Session,
    subkategori_kode: str,
    wilayah_kode: str,
    tahun: int,
    triwulan: Optional[int] = None,
) -> HasilSubkategori:
    """
    Dispatcher: Memilih rumus yang tepat untuk subkategori yang diberikan.
    """
    func = REGISTRY_RUMUS_SUBKATEGORI.get(subkategori_kode, hitung_subkategori_standar)
    # Jika fungsi khusus didesain untuk tidak menerima parameter `subkategori_kode` (karena hardcoded),
    # kita tangani di sini dengan membungkusnya.
    # Tapi agar seragam, semua fungsi custom sebaiknya mengikuti signature standar
    # atau kita bungkus panggilannya jika TypeError.
    try:
        return func(db, subkategori_kode, wilayah_kode, tahun, triwulan)
    except TypeError:
        # Jika fungsi kustom (seperti hitung_subkategori_1_1 di template) 
        # tidak menerima argumen subkategori_kode
        return func(db, wilayah_kode, tahun, triwulan)
