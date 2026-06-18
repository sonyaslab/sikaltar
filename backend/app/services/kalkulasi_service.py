"""
Service: KalkulasiService  (VERSI DIPERBAIKI)
Implementasi rumus perhitungan LK PDRB sesuai kaidah BPS SNA 2008.

PERUBAHAN vs versi lama (cari penanda  # [FIX] ):
  [FIX-2] Output Sekunder di tingkat subkategori memakai jenis rasio 'OS_SEK'
          (BUKAN 'OS'). Ini mencegah penghitungan ganda: 'OS' dipakai untuk
          Output Ikutan per-komoditas, 'OS_SEK' untuk Output Sekunder per-subkategori.
          Default 'OS_SEK' = 0, jadi jika tidak diisi tidak ada efek apa pun.
  [FIX-7] Harga berlaku kini punya fallback ke wilayah provinsi '65' (simetris
          dengan harga konstan).
  [FIX-3] hitung_subkategori mencatat jumlah komoditas yang dilewati (skipped)
          agar data tidak lengkap tidak "hilang diam-diam".
  (hitung_kategori_deflasi tetap dipakai — sekarang dipanggil oleh cascade.)

Unit output: Juta Rupiah (Rp 1.000.000)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional

from sqlalchemy.orm import Session

from app.models.input_data import InputHarga, InputIndeksDeflator, InputProduksi, InputIHP
from app.models.komoditas import Komoditas
from app.models.hasil import LkHasil
from app.services.rasio_service import get_rasio, get_rasio_safe, RasioTidakDitemukanError

JUTA = Decimal("1000000")
TAHUN_DASAR = 2010


# ─────────────────────────────────────────────────────────────────────────────
# Data classes hasil kalkulasi
# ─────────────────────────────────────────────────────────────────────────────

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

    # [FIX-3] Pelacakan kelengkapan data
    komoditas_dihitung: int = 0
    komoditas_dilewati: int = 0

    peringatan: list[str] = field(default_factory=list)


def _round6(value: Decimal) -> Decimal:
    """Pembulatan 6 desimal untuk penyimpanan ke database."""
    return value.quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)


def _get_harga_berlaku(
    db: Session, komoditas_id: int, wilayah_kode: str, tahun: int, triwulan: Optional[int]
) -> Optional[Decimal]:
    """
    Ambil harga_berlaku dari input_harga.
    Urutan lookup: (komoditas, wilayah, tahun, triwulan) → (komoditas, wilayah, tahun, NULL)
                   → [FIX-7] fallback ke provinsi '65'.
    """
    row = (
        db.query(InputHarga)
        .filter(
            InputHarga.komoditas_id == komoditas_id,
            InputHarga.wilayah_kode == wilayah_kode,
            InputHarga.tahun == tahun,
            InputHarga.triwulan == triwulan,
        )
        .first()
    )
    if row and row.harga_berlaku:
        return Decimal(str(row.harga_berlaku))

    # Fallback: harga tahunan rata-rata (triwulan NULL)
    if triwulan is not None:
        row = (
            db.query(InputHarga)
            .filter(
                InputHarga.komoditas_id == komoditas_id,
                InputHarga.wilayah_kode == wilayah_kode,
                InputHarga.tahun == tahun,
                InputHarga.triwulan.is_(None),
            )
            .first()
        )
        if row and row.harga_berlaku:
            return Decimal(str(row.harga_berlaku))

    # [FIX-7] Fallback ke harga provinsi 65 bila kabupaten kosong
    if wilayah_kode != "65":
        return _get_harga_berlaku(db, komoditas_id, "65", tahun, triwulan)

    return None

def _get_ihp(
    db: Session, kategori_kode: str, komoditas_id: int, wilayah_kode: str, tahun: int, triwulan: Optional[int]
) -> Optional[Decimal]:
    """Cari IHP untuk komoditas, fallback ke IHP kategori, fallback ke IHP provinsi."""
    # 1. Cari spesifik komoditas
    row = db.query(InputIHP).filter(
        InputIHP.komoditas_id == komoditas_id,
        InputIHP.wilayah_kode == wilayah_kode,
        InputIHP.tahun == tahun,
        InputIHP.triwulan == triwulan,
    ).first()

    # 2. Cari tingkat kategori (komoditas_id is None)
    if not row:
        row = db.query(InputIHP).filter(
            InputIHP.kategori_kode == kategori_kode,
            InputIHP.komoditas_id.is_(None),
            InputIHP.wilayah_kode == wilayah_kode,
            InputIHP.tahun == tahun,
            InputIHP.triwulan == triwulan,
        ).first()

    if row and row.nilai_indeks:
        return Decimal(str(row.nilai_indeks))

    # 3. Fallback ke triwulan NULL (tahunan)
    if triwulan is not None:
        row = db.query(InputIHP).filter(
            InputIHP.komoditas_id == komoditas_id,
            InputIHP.wilayah_kode == wilayah_kode,
            InputIHP.tahun == tahun,
            InputIHP.triwulan.is_(None),
        ).first()
        if not row:
            row = db.query(InputIHP).filter(
                InputIHP.kategori_kode == kategori_kode,
                InputIHP.komoditas_id.is_(None),
                InputIHP.wilayah_kode == wilayah_kode,
                InputIHP.tahun == tahun,
                InputIHP.triwulan.is_(None),
            ).first()
        if row and row.nilai_indeks:
            return Decimal(str(row.nilai_indeks))

    # 4. Fallback ke provinsi 65
    if wilayah_kode != "65":
        return _get_ihp(db, kategori_kode, komoditas_id, "65", tahun, triwulan)

    return None


def _get_harga_konstan(
    db: Session, komoditas_id: int, wilayah_kode: str
) -> Optional[Decimal]:
    """
    Ambil harga_konstan_2010 — disimpan sekali di tahun=2010, triwulan=NULL.
    Nilainya TETAP untuk semua tahun berjalan.
    """
    row = (
        db.query(InputHarga)
        .filter(
            InputHarga.komoditas_id == komoditas_id,
            InputHarga.wilayah_kode == wilayah_kode,
            InputHarga.tahun == TAHUN_DASAR,
            InputHarga.triwulan.is_(None),
        )
        .first()
    )
    if row and row.harga_konstan_2010:
        return Decimal(str(row.harga_konstan_2010))

    # Fallback: cari di wilayah provinsi (65) jika tidak ada di kabupaten
    if wilayah_kode != "65":
        return _get_harga_konstan(db, komoditas_id, "65")
    return None


# ─────────────────────────────────────────────────────────────────────────────
# Fungsi kalkulasi utama
# ─────────────────────────────────────────────────────────────────────────────

def hitung_output_komoditas(
    db: Session,
    komoditas_id: int,
    wilayah_kode: str,
    tahun: int,
    triwulan: Optional[int] = None,
) -> HasilKomoditas:
    """
    Hitung output per komoditas (metode Produksi + Revaluasi).

    ADHB:
      output_utama_b  = kuantum × harga_berlaku / 1.000.000
      output_ikutan_b = output_utama_b × rasio_OS(ADHB, tahun)   ← Output Ikutan per-komoditas
      wip_b           = output_utama_b × rasio_WIP(ADHB, tahun)

    ADHK (Revaluasi: kuantum sama, harga konstan 2010, rasio tahun DASAR):
      output_utama_k  = kuantum × harga_konstan_2010 / 1.000.000
      output_ikutan_k = output_utama_k × rasio_OS(ADHK, 2010)
      wip_k           = output_utama_k × rasio_WIP(ADHK, 2010)
    """
    komoditas = db.get(Komoditas, komoditas_id)
    if not komoditas:
        hasil = HasilKomoditas(
            komoditas_id=komoditas_id, komoditas_nama="?",
            wilayah_kode=wilayah_kode, tahun=tahun, triwulan=triwulan,
        )
        hasil.error = f"Komoditas ID={komoditas_id} tidak ditemukan"
        return hasil

    hasil = HasilKomoditas(
        komoditas_id=komoditas_id,
        komoditas_nama=komoditas.nama,
        wilayah_kode=wilayah_kode,
        tahun=tahun,
        triwulan=triwulan,
    )
    kategori_kode = komoditas.kategori_kode

    # ── Ambil data produksi ───────────────────────────────────────────────
    prod_row = (
        db.query(InputProduksi)
        .filter(
            InputProduksi.komoditas_id == komoditas_id,
            InputProduksi.wilayah_kode == wilayah_kode,
            InputProduksi.tahun == tahun,
            InputProduksi.triwulan == triwulan,
        )
        .first()
    )
    if not prod_row or prod_row.kuantum is None:
        hasil.error = (
            f"Data produksi tidak tersedia: komoditas={komoditas_id}, "
            f"wilayah={wilayah_kode}, tahun={tahun}, tw={triwulan}"
        )
        return hasil

    kuantum = Decimal(str(prod_row.kuantum))

    # Faktor konversi (mis: TBS → CPO)
    if komoditas.faktor_konversi:
        kuantum = kuantum * Decimal(str(komoditas.faktor_konversi))

    # ── ADHB ──────────────────────────────────────────────────────────────
    # Tentukan Harga Berlaku
    harga_b = None
    if komoditas.metode_harga == 'IHP':
        # Wajib pakai IHP
        ihp_t = _get_ihp(db, kategori_kode, komoditas_id, wilayah_kode, tahun, triwulan)
        harga_k = _get_harga_konstan(db, komoditas_id, wilayah_kode)
        if ihp_t is not None and harga_k is not None:
            harga_b = _round6(harga_k * (ihp_t / Decimal(100)))
    else:
        # Cari harga langsung
        harga_b = _get_harga_berlaku(db, komoditas_id, wilayah_kode, tahun, triwulan)
        # Fallback ke IHP jika harga langsung kosong
        if harga_b is None:
            ihp_t = _get_ihp(db, kategori_kode, komoditas_id, wilayah_kode, tahun, triwulan)
            harga_k = _get_harga_konstan(db, komoditas_id, wilayah_kode)
            if ihp_t is not None and harga_k is not None:
                harga_b = _round6(harga_k * (ihp_t / Decimal(100)))

    if harga_b is None:
        hasil.error = (
            f"Harga berlaku / IHP tidak tersedia: komoditas={komoditas_id}, "
            f"wilayah={wilayah_kode}, tahun={tahun}"
        )
        return hasil

    output_utama_b = _round6(kuantum * harga_b / JUTA)

    rasio_os_b = get_rasio_safe(
        db, "OS", "ADHB", tahun,
        komoditas_id=komoditas_id, kategori_kode=kategori_kode,
        wilayah_kode=wilayah_kode, default=Decimal(0),
    )
    rasio_wip_b = get_rasio_safe(
        db, "WIP", "ADHB", tahun,
        komoditas_id=komoditas_id, kategori_kode=kategori_kode,
        wilayah_kode=wilayah_kode, default=Decimal(0),
    )

    output_ikutan_b = _round6(output_utama_b * rasio_os_b)
    wip_b = _round6(output_utama_b * rasio_wip_b)

    hasil.output_utama_adhb = output_utama_b
    hasil.output_ikutan_adhb = output_ikutan_b
    hasil.wip_adhb = wip_b
    hasil.output_sebelum_adj_adhb = _round6(output_utama_b + output_ikutan_b + wip_b)

    # ── ADHK (Revaluasi) ──────────────────────────────────────────────────
    harga_k = _get_harga_konstan(db, komoditas_id, wilayah_kode)
    if harga_k is None:
        hasil.error = (
            f"Harga konstan 2010 tidak tersedia: komoditas={komoditas_id}, "
            f"wilayah={wilayah_kode}"
        )
        return hasil

    output_utama_k = _round6(kuantum * harga_k / JUTA)

    rasio_os_k = get_rasio_safe(
        db, "OS", "ADHK", TAHUN_DASAR,
        komoditas_id=komoditas_id, kategori_kode=kategori_kode,
        wilayah_kode=wilayah_kode, default=Decimal(0),
    )
    rasio_wip_k = get_rasio_safe(
        db, "WIP", "ADHK", TAHUN_DASAR,
        komoditas_id=komoditas_id, kategori_kode=kategori_kode,
        wilayah_kode=wilayah_kode, default=Decimal(0),
    )

    output_ikutan_k = _round6(output_utama_k * rasio_os_k)
    wip_k = _round6(output_utama_k * rasio_wip_k)

    hasil.output_utama_adhk = output_utama_k
    hasil.output_ikutan_adhk = output_ikutan_k
    hasil.wip_adhk = wip_k
    hasil.output_sebelum_adj_adhk = _round6(output_utama_k + output_ikutan_k + wip_k)

    return hasil


def hitung_subkategori(
    db: Session,
    subkategori_kode: str,
    wilayah_kode: str,
    tahun: int,
    triwulan: Optional[int] = None,
) -> HasilSubkategori:
    """
    Agregasi semua komoditas dalam subkategori → hitung ADJ, KA, NTB.
    (Metode Produksi/Revaluasi — berbasis komoditas.)

    ADHB:
      output_primer_b   = SUM(output_sebelum_adj_adhb) per komoditas
      output_sekunder_b = output_primer_b × rasio_OS_SEK(subkat, ADHB, tahun)  # [FIX-2]
      adj_b             = output_primer_b × rasio_ADJ(subkat, ADHB, tahun)
      output_total_b    = output_primer_b + output_sekunder_b + adj_b
      ka_b              = output_total_b × rasio_KA(subkat, ADHB, tahun)
      ntb_b             = output_total_b − ka_b

    ADHK: sama, tapi semua rasio dari tahun DASAR (2010).
    """
    hasil = HasilSubkategori(
        subkategori_kode=subkategori_kode,
        wilayah_kode=wilayah_kode,
        tahun=tahun,
        triwulan=triwulan,
    )

    from app.models.hasil import PdrbRekap
    rekap = (
        db.query(PdrbRekap)
        .filter(
            PdrbRekap.kategori_kode == subkategori_kode,
            PdrbRekap.wilayah_kode == wilayah_kode,
            PdrbRekap.tahun == tahun,
            PdrbRekap.triwulan == triwulan,
        )
        .first()
    )
    adj_adhb_manual = Decimal(str(rekap.adjustment_adhb)) if rekap and rekap.adjustment_adhb else Decimal(0)
    adj_adhk_manual = Decimal(str(rekap.adjustment_adhk)) if rekap and rekap.adjustment_adhk else Decimal(0)

    komoditas_list = (
        db.query(Komoditas)
        .filter(Komoditas.kategori_kode == subkategori_kode, Komoditas.aktif.is_(True))
        .all()
    )

    if not komoditas_list:
        hasil.peringatan.append(
            f"Tidak ada komoditas aktif untuk subkategori {subkategori_kode!r}"
        )
        return hasil

    total_primer_b = Decimal(0)
    total_primer_k = Decimal(0)

    for kom in komoditas_list:
        h = hitung_output_komoditas(db, kom.id, wilayah_kode, tahun, triwulan)
        if h.error:
            hasil.komoditas_dilewati += 1   # [FIX-3]
            hasil.peringatan.append(f"[{kom.kode_internal}] {h.error}")
            continue
        hasil.komoditas_dihitung += 1
        total_primer_b += h.output_sebelum_adj_adhb
        total_primer_k += h.output_sebelum_adj_adhk

    hasil.output_primer_adhb = _round6(total_primer_b)
    hasil.output_primer_adhk = _round6(total_primer_k)

    if total_primer_b == 0 and total_primer_k == 0:
        hasil.peringatan.append(f"Semua output_primer = 0 untuk {subkategori_kode!r} {tahun}")
        return hasil

    # ── ADHB: Output Sekunder + ADJ + KA ──────────────────────────────────
    # [FIX-2] Output Sekunder pakai 'OS_SEK' (default 0) → tidak menggandakan 'OS'
    rasio_os_b = get_rasio_safe(db, "OS_SEK", "ADHB", tahun,
                                kategori_kode=subkategori_kode, wilayah_kode=wilayah_kode,
                                default=Decimal(0))

    try:
        rasio_ka_b = get_rasio(db, "KA", "ADHB", tahun,
                               kategori_kode=subkategori_kode, wilayah_kode=wilayah_kode)
    except RasioTidakDitemukanError:
        rasio_ka_b = Decimal(0)
        hasil.peringatan.append(f"Rasio KA ADHB tidak ditemukan untuk {subkategori_kode!r} {tahun}")

    # Adjustment didapat dari manual input (tidak lagi pakai rasio ADJ)
    adj_b = adj_adhb_manual
    os_b = _round6(total_primer_b * rasio_os_b)
    total_b = _round6(total_primer_b + os_b) # Tidak ditambah adj dulu karena adj dilakukan setelah NTB
    ka_b = _round6(total_b * rasio_ka_b)
    ntb_sebelum_adj_b = _round6(total_b - ka_b)
    ntb_final_b = _round6(ntb_sebelum_adj_b + adj_b)

    hasil.output_sekunder_adhb = os_b
    hasil.adj_adhb = adj_b
    hasil.output_total_adhb = total_b
    hasil.rasio_ka_adhb = rasio_ka_b
    hasil.ka_adhb = ka_b
    hasil.ntb_sebelum_adj_adhb = ntb_sebelum_adj_b
    hasil.ntb_adhb = ntb_final_b

    # ── ADHK: rasio tahun dasar 2010 ──────────────────────────────────────
    rasio_os_k = get_rasio_safe(db, "OS_SEK", "ADHK", TAHUN_DASAR,
                                kategori_kode=subkategori_kode, wilayah_kode=wilayah_kode,
                                default=Decimal(0))

    rasio_ka_k = get_rasio_safe(db, "KA", "ADHK", TAHUN_DASAR,
                                kategori_kode=subkategori_kode, wilayah_kode=wilayah_kode,
                                default=Decimal(0))

    os_k = _round6(total_primer_k * rasio_os_k)
    adj_k = adj_adhk_manual
    total_k = _round6(total_primer_k + os_k)
    ka_k = _round6(total_k * rasio_ka_k)
    ntb_sebelum_adj_k = _round6(total_k - ka_k)
    ntb_final_k = _round6(ntb_sebelum_adj_k + adj_k)

    hasil.output_sekunder_adhk = os_k
    hasil.adj_adhk = adj_k
    hasil.output_total_adhk = total_k
    hasil.rasio_ka_adhk = rasio_ka_k
    hasil.ka_adhk = ka_k
    hasil.ntb_sebelum_adj_adhk = ntb_sebelum_adj_k
    hasil.ntb_adhk = ntb_final_k

    return hasil


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
    Dipakai untuk: Konstruksi (6), Perdagangan (7), Transportasi (8),
    Jasa (9–17), dll — kategori tanpa data kuantum×harga.

    ADHB: output_total_adhb = input langsung user (disimpan di pdrb_rekap.output_total_adhb)
    ADHK: output_total_adhk = output_total_adhb / (indeks_deflator / 100)
    NTB  = output_total − (output_total × rasio_KA)
    """
    hasil = HasilSubkategori(
        subkategori_kode=kategori_kode,
        wilayah_kode=wilayah_kode,
        tahun=tahun,
        triwulan=triwulan,
    )

    deflator_row = (
        db.query(InputIndeksDeflator)
        .filter(
            InputIndeksDeflator.kategori_kode == kategori_kode,
            InputIndeksDeflator.wilayah_kode == wilayah_kode,
            InputIndeksDeflator.tahun == tahun,
            InputIndeksDeflator.triwulan == triwulan,
        )
        .first()
    )
    # Fallback indeks ke provinsi 65
    if not deflator_row and wilayah_kode != "65":
        deflator_row = (
            db.query(InputIndeksDeflator)
            .filter(
                InputIndeksDeflator.kategori_kode == kategori_kode,
                InputIndeksDeflator.wilayah_kode == "65",
                InputIndeksDeflator.tahun == tahun,
                InputIndeksDeflator.triwulan == triwulan,
            )
            .first()
        )
    if not deflator_row:
        hasil.peringatan.append(
            f"Indeks deflator tidak tersedia: kategori={kategori_kode!r}, "
            f"wilayah={wilayah_kode!r}, tahun={tahun}, tw={triwulan}"
        )
        return hasil

    indeks = Decimal(str(deflator_row.nilai_indeks))
    if indeks == 0:
        hasil.peringatan.append(f"Indeks deflator = 0 untuk {kategori_kode!r} {tahun}")
        return hasil

    # Output ADHB: dari argumen, atau dari pdrb_rekap (input langsung user)
    from app.models.hasil import PdrbRekap
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
    if output_total_adhb is None:
        if rekap and rekap.output_total_adhb:
            output_total_adhb = Decimal(str(rekap.output_total_adhb))
        else:
            hasil.peringatan.append(
                f"Output ADHB tidak tersedia untuk kategori deflasi {kategori_kode!r} "
                f"(isi pdrb_rekap.output_total_adhb terlebih dulu)"
            )
            return hasil

    adj_adhb_manual = Decimal(str(rekap.adjustment_adhb)) if rekap and rekap.adjustment_adhb else Decimal(0)
    adj_adhk_manual = Decimal(str(rekap.adjustment_adhk)) if rekap and rekap.adjustment_adhk else Decimal(0)

    output_total_adhk = _round6(output_total_adhb / (indeks / Decimal(100)))

    rasio_ka_b = get_rasio_safe(db, "KA", "ADHB", tahun, kategori_kode=kategori_kode,
                                wilayah_kode=wilayah_kode, default=Decimal(0))
    ka_b = _round6(output_total_adhb * rasio_ka_b)
    ntb_sebelum_adj_b = _round6(output_total_adhb - ka_b)
    ntb_final_b = _round6(ntb_sebelum_adj_b + adj_adhb_manual)

    rasio_ka_k = get_rasio_safe(db, "KA", "ADHK", TAHUN_DASAR, kategori_kode=kategori_kode,
                                wilayah_kode=wilayah_kode, default=Decimal(0))
    ka_k = _round6(output_total_adhk * rasio_ka_k)
    ntb_sebelum_adj_k = _round6(output_total_adhk - ka_k)
    ntb_final_k = _round6(ntb_sebelum_adj_k + adj_adhk_manual)

    hasil.output_primer_adhb = output_total_adhb
    hasil.output_total_adhb = output_total_adhb
    hasil.rasio_ka_adhb = rasio_ka_b
    hasil.ka_adhb = ka_b
    hasil.adj_adhb = adj_adhb_manual
    hasil.ntb_sebelum_adj_adhb = ntb_sebelum_adj_b
    hasil.ntb_adhb = ntb_final_b

    hasil.output_primer_adhk = output_total_adhk
    hasil.output_total_adhk = output_total_adhk
    hasil.rasio_ka_adhk = rasio_ka_k
    hasil.ka_adhk = ka_k
    hasil.adj_adhk = adj_adhk_manual
    hasil.ntb_sebelum_adj_adhk = ntb_sebelum_adj_k
    hasil.ntb_adhk = ntb_final_k

    return hasil


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