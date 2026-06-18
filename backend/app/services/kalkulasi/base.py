"""
Struktur Data Dasar untuk Kalkulasi PDRB
"""
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Optional

@dataclass
class HasilKomoditas:
    """Hasil kalkulasi per komoditas — komponen sebelum agregasi subkategori."""
    komoditas_id: int
    komoditas_nama: str
    wilayah_kode: str
    tahun: int
    triwulan: Optional[int]

    # ADHB
    output_utama_adhb: Decimal = Decimal(0)
    output_ikutan_adhb: Decimal = Decimal(0)
    wip_adhb: Decimal = Decimal(0)
    output_sebelum_adj_adhb: Decimal = Decimal(0)   # = utama + ikutan + wip

    # ADHK
    output_utama_adhk: Decimal = Decimal(0)
    output_ikutan_adhk: Decimal = Decimal(0)
    wip_adhk: Decimal = Decimal(0)
    output_sebelum_adj_adhk: Decimal = Decimal(0)

    error: Optional[str] = None   # Pesan error jika data tidak lengkap


@dataclass
class HasilSubkategori:
    """Hasil kalkulasi per subkategori — setelah ADJ dan KA."""
    subkategori_kode: str
    wilayah_kode: str
    tahun: int
    triwulan: Optional[int]

    # ADHB
    output_primer_adhb: Decimal = Decimal(0)
    output_sekunder_adhb: Decimal = Decimal(0)
    adj_adhb: Decimal = Decimal(0)
    output_total_adhb: Decimal = Decimal(0)
    rasio_ka_adhb: Decimal = Decimal(0)
    ka_adhb: Decimal = Decimal(0)
    ntb_sebelum_adj_adhb: Decimal = Decimal(0)
    ntb_adhb: Decimal = Decimal(0)

    # ADHK
    output_primer_adhk: Decimal = Decimal(0)
    output_sekunder_adhk: Decimal = Decimal(0)
    adj_adhk: Decimal = Decimal(0)
    output_total_adhk: Decimal = Decimal(0)
    rasio_ka_adhk: Decimal = Decimal(0)
    ka_adhk: Decimal = Decimal(0)
    ntb_sebelum_adj_adhk: Decimal = Decimal(0)
    ntb_adhk: Decimal = Decimal(0)

    # Pelacakan kelengkapan data
    komoditas_dihitung: int = 0
    komoditas_dilewati: int = 0

    peringatan: list[str] = field(default_factory=list)

def _round6(value: Decimal) -> Decimal:
    """Pembulatan 6 desimal untuk penyimpanan ke database."""
    from decimal import ROUND_HALF_UP
    return value.quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)
