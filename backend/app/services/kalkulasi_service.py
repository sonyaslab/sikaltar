"""
Service: KalkulasiService
Implementasi rumus perhitungan LK PDRB sesuai kaidah BPS SNA 2008.

Metode yang didukung:
  - Produksi + Revaluasi  : Kategori A (Pertanian), B (Pertambangan)
  - Deflasi               : Kategori F (Konstruksi), G.2, H, I, J, K, L, M,N, O, P, Q, R,S,T,U
  - Double Deflasi        : Kategori C (Industri Pengolahan)

Unit output: Juta Rupiah (Rp 1.000.000)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional

from sqlalchemy.orm import Session

from app.models.input_data import InputHarga, InputIndeksDeflator, InputProduksi
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
    ntb_adhb: Decimal = Decimal(0)

    # ADHK
    output_primer_adhk: Decimal = Decimal(0)
    output_sekunder_adhk: Decimal = Decimal(0)
    adj_adhk: Decimal = Decimal(0)
    output_total_adhk: Decimal = Decimal(0)
    rasio_ka_adhk: Decimal = Decimal(0)
    ka_adhk: Decimal = Decimal(0)
    ntb_adhk: Decimal = Decimal(0)

    peringatan: list[str] = field(default_factory=list)


def _round6(value: Decimal) -> Decimal:
    """Pembulatan 6 desimal untuk penyimpanan ke database."""
    return value.quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)


def _get_harga_berlaku(
    db: Session, komoditas_id: int, wilayah_kode: str, tahun: int, triwulan: Optional[int]
) -> Optional[Decimal]:
    """
    Ambil harga_berlaku dari input_harga.
    Urutan lookup: (komoditas, wilayah, tahun, triwulan) → (komoditas, wilayah, tahun, NULL).
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

    # Fallback: harga tahunan rata-rata
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
      output_ikutan_b = output_utama_b × rasio_OS(ADHB, tahun)
      wip_b           = output_utama_b × rasio_WIP(ADHB, tahun)

    ADHK:
      output_utama_k  = kuantum × harga_konstan_2010 / 1.000.000
      output_ikutan_k = output_utama_k × rasio_OS(ADHK, 2010)     ← pakai rasio tahun dasar
      wip_k           = output_utama_k × rasio_WIP(ADHK, 2010)    ← pakai rasio tahun dasar
    """
    # Ambil metadata komoditas
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
        hasil.error = f"Data produksi tidak tersedia: komoditas={komoditas_id}, wilayah={wilayah_kode}, tahun={tahun}, tw={triwulan}"
        return hasil

    kuantum = Decimal(str(prod_row.kuantum))

    # Terapkan faktor konversi jika ada (mis: TBS → CPO)
    if komoditas.faktor_konversi:
        kuantum = kuantum * Decimal(str(komoditas.faktor_konversi))

    # ── ADHB ──────────────────────────────────────────────────────────────
    harga_b = _get_harga_berlaku(db, komoditas_id, wilayah_kode, tahun, triwulan)
    if harga_b is None:
        hasil.error = f"Harga berlaku tidak tersedia: komoditas={komoditas_id}, wilayah={wilayah_kode}, tahun={tahun}"
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

    # ── ADHK (Revaluasi: kuantum sama, harga konstan 2010) ────────────────
    harga_k = _get_harga_konstan(db, komoditas_id, wilayah_kode)
    if harga_k is None:
        hasil.error = f"Harga konstan 2010 tidak tersedia: komoditas={komoditas_id}, wilayah={wilayah_kode}"
        return hasil

    output_utama_k = _round6(kuantum * harga_k / JUTA)

    # ADHK menggunakan rasio tahun DASAR (2010), bukan tahun berjalan
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

    ADHB:
      output_primer_b  = SUM(output_sebelum_adj_adhb) per komoditas
      output_sekunder_b = output_primer_b × rasio_OS(subkat, ADHB, tahun)
      adj_b            = output_primer_b × rasio_ADJ(subkat, ADHB, tahun)
      output_total_b   = output_primer_b + output_sekunder_b + adj_b
      ka_b             = output_total_b × rasio_KA(subkat, ADHB, tahun)
      ntb_b            = output_total_b − ka_b

    ADHK: sama, tapi semua rasio dari tahun DASAR (2010)
    """
    hasil = HasilSubkategori(
        subkategori_kode=subkategori_kode,
        wilayah_kode=wilayah_kode,
        tahun=tahun,
        triwulan=triwulan,
    )

    # Ambil semua komoditas dalam subkategori ini
    from app.models.komoditas import Komoditas
    komoditas_list = (
        db.query(Komoditas)
        .filter(Komoditas.kategori_kode == subkategori_kode, Komoditas.aktif.is_(True))
        .all()
    )

    if not komoditas_list:
        hasil.peringatan.append(f"Tidak ada komoditas aktif untuk subkategori {subkategori_kode!r}")
        return hasil

    # Jumlahkan output per komoditas
    total_primer_b = Decimal(0)
    total_primer_k = Decimal(0)

    for kom in komoditas_list:
        h = hitung_output_komoditas(db, kom.id, wilayah_kode, tahun, triwulan)
        if h.error:
            # Komoditas dengan data tidak lengkap dilewati, dicatat sebagai peringatan
            hasil.peringatan.append(f"[{kom.kode_internal}] {h.error}")
            continue
        total_primer_b += h.output_sebelum_adj_adhb
        total_primer_k += h.output_sebelum_adj_adhk

    hasil.output_primer_adhb = _round6(total_primer_b)
    hasil.output_primer_adhk = _round6(total_primer_k)

    if total_primer_b == 0 and total_primer_k == 0:
        hasil.peringatan.append(f"Semua output_primer = 0 untuk {subkategori_kode!r} {tahun}")
        return hasil

    # ── ADHB: ADJ + KA ────────────────────────────────────────────────────
    try:
        rasio_os_b = get_rasio(db, "OS", "ADHB", tahun, kategori_kode=subkategori_kode, wilayah_kode=wilayah_kode)
    except RasioTidakDitemukanError:
        rasio_os_b = Decimal(0)
        hasil.peringatan.append(f"Rasio OS ADHB tidak ditemukan untuk {subkategori_kode!r} tahun {tahun}")

    try:
        rasio_adj_b = get_rasio(db, "ADJ", "ADHB", tahun, kategori_kode=subkategori_kode, wilayah_kode=wilayah_kode)
    except RasioTidakDitemukanError:
        rasio_adj_b = Decimal(0)
        hasil.peringatan.append(f"Rasio ADJ ADHB tidak ditemukan untuk {subkategori_kode!r} tahun {tahun}")

    try:
        rasio_ka_b = get_rasio(db, "KA", "ADHB", tahun, kategori_kode=subkategori_kode, wilayah_kode=wilayah_kode)
    except RasioTidakDitemukanError:
        rasio_ka_b = Decimal(0)
        hasil.peringatan.append(f"Rasio KA ADHB tidak ditemukan untuk {subkategori_kode!r} tahun {tahun}")

    os_b = _round6(total_primer_b * rasio_os_b)
    adj_b = _round6(total_primer_b * rasio_adj_b)
    total_b = _round6(total_primer_b + os_b + adj_b)
    ka_b = _round6(total_b * rasio_ka_b)

    hasil.output_sekunder_adhb = os_b
    hasil.adj_adhb = adj_b
    hasil.output_total_adhb = total_b
    hasil.rasio_ka_adhb = rasio_ka_b
    hasil.ka_adhb = ka_b
    hasil.ntb_adhb = _round6(total_b - ka_b)

    # ── ADHK: ADJ + KA (rasio tahun dasar 2010) ───────────────────────────
    try:
        rasio_os_k = get_rasio(db, "OS", "ADHK", TAHUN_DASAR, kategori_kode=subkategori_kode, wilayah_kode=wilayah_kode)
    except RasioTidakDitemukanError:
        rasio_os_k = Decimal(0)

    try:
        rasio_adj_k = get_rasio(db, "ADJ", "ADHK", TAHUN_DASAR, kategori_kode=subkategori_kode, wilayah_kode=wilayah_kode)
    except RasioTidakDitemukanError:
        rasio_adj_k = Decimal(0)

    try:
        rasio_ka_k = get_rasio(db, "KA", "ADHK", TAHUN_DASAR, kategori_kode=subkategori_kode, wilayah_kode=wilayah_kode)
    except RasioTidakDitemukanError:
        rasio_ka_k = Decimal(0)

    os_k = _round6(total_primer_k * rasio_os_k)
    adj_k = _round6(total_primer_k * rasio_adj_k)
    total_k = _round6(total_primer_k + os_k + adj_k)
    ka_k = _round6(total_k * rasio_ka_k)

    hasil.output_sekunder_adhk = os_k
    hasil.adj_adhk = adj_k
    hasil.output_total_adhk = total_k
    hasil.rasio_ka_adhk = rasio_ka_k
    hasil.ka_adhk = ka_k
    hasil.ntb_adhk = _round6(total_k - ka_k)

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
    Hitung NTB untuk kategori dengan metode DEFLASI.
    Digunakan untuk: Konstruksi (6), Pemerintahan (14), sebagian Transportasi (8.x), dll.

    ADHB: output_total_adhb = input langsung dari user (bukan produksi × harga)
    ADHK: output_total_adhk = output_total_adhb / (indeks_deflator / 100)
    """
    hasil = HasilSubkategori(
        subkategori_kode=kategori_kode,
        wilayah_kode=wilayah_kode,
        tahun=tahun,
        triwulan=triwulan,
    )

    # Ambil indeks deflator
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
    if not deflator_row:
        hasil.peringatan.append(
            f"Indeks deflator tidak tersedia: kategori={kategori_kode!r}, "
            f"wilayah={wilayah_kode!r}, tahun={tahun}, tw={triwulan}"
        )
        return hasil

    indeks = Decimal(str(deflator_row.nilai_indeks))

    # Gunakan output_adhb yang sudah tersimpan di pdrb_rekap jika tidak disuplai
    if output_total_adhb is None:
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
        if rekap and rekap.output_total_adhb:
            output_total_adhb = Decimal(str(rekap.output_total_adhb))
        else:
            hasil.peringatan.append(f"Output ADHB tidak tersedia untuk kategori deflasi {kategori_kode!r}")
            return hasil

    output_total_adhk = _round6(output_total_adhb / (indeks / Decimal(100)))

    # Rasio KA ADHB
    rasio_ka_b = get_rasio_safe(db, "KA", "ADHB", tahun, kategori_kode=kategori_kode,
                                 wilayah_kode=wilayah_kode, default=Decimal(0))
    ka_b = _round6(output_total_adhb * rasio_ka_b)

    # Rasio KA ADHK (tahun dasar)
    rasio_ka_k = get_rasio_safe(db, "KA", "ADHK", TAHUN_DASAR, kategori_kode=kategori_kode,
                                 wilayah_kode=wilayah_kode, default=Decimal(0))
    ka_k = _round6(output_total_adhk * rasio_ka_k)

    hasil.output_total_adhb = output_total_adhb
    hasil.rasio_ka_adhb = rasio_ka_b
    hasil.ka_adhb = ka_b
    hasil.ntb_adhb = _round6(output_total_adhb - ka_b)

    hasil.output_total_adhk = output_total_adhk
    hasil.rasio_ka_adhk = rasio_ka_k
    hasil.ka_adhk = ka_k
    hasil.ntb_adhk = _round6(output_total_adhk - ka_k)

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
    """
    Simpan atau update hasil kalkulasi ke tabel lk_hasil.
    Gunakan upsert (UPDATE jika sudah ada, INSERT jika belum).
    """
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
            komoditas_id=komoditas_id,
            wilayah_kode=wilayah_kode,
            tahun=tahun,
            triwulan=triwulan,
        )
        db.add(row)

    # Update komponen
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
