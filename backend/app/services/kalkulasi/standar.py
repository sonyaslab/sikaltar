"""
Strategi Kalkulasi Standar (Produksi/Revaluasi & Deflasi)
"""
from typing import Optional
from decimal import Decimal
from sqlalchemy.orm import Session

from app.models.input_data import InputHarga, InputIndeksDeflator, InputProduksi, InputIHP
from app.models.komoditas import Komoditas
from app.services.rasio_service import get_rasio, get_rasio_safe, RasioTidakDitemukanError
from app.services.kalkulasi.base import HasilKomoditas, HasilSubkategori, _round6

JUTA = Decimal("1000000")
TAHUN_DASAR = 2010

def _get_harga_berlaku(
    db: Session, komoditas_id: int, wilayah_kode: str, tahun: int, triwulan: Optional[int]
) -> Optional[Decimal]:
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

    if wilayah_kode != "65":
        return _get_harga_berlaku(db, komoditas_id, "65", tahun, triwulan)

    return None

def _get_ihp(
    db: Session, kategori_kode: str, komoditas_id: int, wilayah_kode: str, tahun: int, triwulan: Optional[int]
) -> Optional[Decimal]:
    row = db.query(InputIHP).filter(
        InputIHP.komoditas_id == komoditas_id,
        InputIHP.wilayah_kode == wilayah_kode,
        InputIHP.tahun == tahun,
        InputIHP.triwulan == triwulan,
    ).first()

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

    if wilayah_kode != "65":
        return _get_ihp(db, kategori_kode, komoditas_id, "65", tahun, triwulan)

    return None

def _get_harga_konstan(
    db: Session, komoditas_id: int, wilayah_kode: str
) -> Optional[Decimal]:
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

    if wilayah_kode != "65":
        return _get_harga_konstan(db, komoditas_id, "65")
    return None

def hitung_output_komoditas_standar(
    db: Session,
    komoditas_id: int,
    wilayah_kode: str,
    tahun: int,
    triwulan: Optional[int] = None,
) -> HasilKomoditas:
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
    if komoditas.faktor_konversi:
        kuantum = kuantum * Decimal(str(komoditas.faktor_konversi))

    harga_b = None
    if komoditas.metode_harga == 'IHP':
        ihp_t = _get_ihp(db, kategori_kode, komoditas_id, wilayah_kode, tahun, triwulan)
        harga_k = _get_harga_konstan(db, komoditas_id, wilayah_kode)
        if ihp_t is not None and harga_k is not None:
            harga_b = _round6(harga_k * (ihp_t / Decimal(100)))
    else:
        harga_b = _get_harga_berlaku(db, komoditas_id, wilayah_kode, tahun, triwulan)
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
    rasio_os_b = get_rasio_safe(db, "OS", "ADHB", tahun, komoditas_id=komoditas_id, kategori_kode=kategori_kode, wilayah_kode=wilayah_kode, default=Decimal(0))
    rasio_wip_b = get_rasio_safe(db, "WIP", "ADHB", tahun, komoditas_id=komoditas_id, kategori_kode=kategori_kode, wilayah_kode=wilayah_kode, default=Decimal(0))

    output_ikutan_b = _round6(output_utama_b * rasio_os_b)
    wip_b = _round6(output_utama_b * rasio_wip_b)

    hasil.output_utama_adhb = output_utama_b
    hasil.output_ikutan_adhb = output_ikutan_b
    hasil.wip_adhb = wip_b
    hasil.output_sebelum_adj_adhb = _round6(output_utama_b + output_ikutan_b + wip_b)

    harga_k = _get_harga_konstan(db, komoditas_id, wilayah_kode)
    if harga_k is None:
        hasil.error = (
            f"Harga konstan 2010 tidak tersedia: komoditas={komoditas_id}, "
            f"wilayah={wilayah_kode}"
        )
        return hasil

    output_utama_k = _round6(kuantum * harga_k / JUTA)
    rasio_os_k = get_rasio_safe(db, "OS", "ADHK", TAHUN_DASAR, komoditas_id=komoditas_id, kategori_kode=kategori_kode, wilayah_kode=wilayah_kode, default=Decimal(0))
    rasio_wip_k = get_rasio_safe(db, "WIP", "ADHK", TAHUN_DASAR, komoditas_id=komoditas_id, kategori_kode=kategori_kode, wilayah_kode=wilayah_kode, default=Decimal(0))

    output_ikutan_k = _round6(output_utama_k * rasio_os_k)
    wip_k = _round6(output_utama_k * rasio_wip_k)

    hasil.output_utama_adhk = output_utama_k
    hasil.output_ikutan_adhk = output_ikutan_k
    hasil.wip_adhk = wip_k
    hasil.output_sebelum_adj_adhk = _round6(output_utama_k + output_ikutan_k + wip_k)

    return hasil

def hitung_subkategori_standar(
    db: Session,
    subkategori_kode: str,
    wilayah_kode: str,
    tahun: int,
    triwulan: Optional[int] = None,
) -> HasilSubkategori:
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
        hasil.peringatan.append(f"Tidak ada komoditas aktif untuk subkategori {subkategori_kode!r}")
        return hasil

    total_primer_b = Decimal(0)
    total_primer_k = Decimal(0)

    # Catatan: Ini memanggil hitung_output_komoditas_standar langsung 
    # karena standar selalu pakai metode standar.
    from app.services.kalkulasi_service import simpan_lk_hasil
    for kom in komoditas_list:
        h = hitung_output_komoditas_standar(db, kom.id, wilayah_kode, tahun, triwulan)
        if h.error:
            hasil.komoditas_dilewati += 1
            hasil.peringatan.append(f"[{kom.kode_internal}] {h.error}")
            continue
        hasil.komoditas_dihitung += 1
        total_primer_b += h.output_sebelum_adj_adhb
        total_primer_k += h.output_sebelum_adj_adhk
        # Perlu menyimpan lk_hasil di sini atau di cascade? Di cascade_service (Step 1) juga disimpan, 
        # tapi itu terpisah. Kita tidak simpan di sini agar tidak dobel.
        # Wait, di cascade_service Step 1, dia memanggil hitung_output_komoditas dan menyimpan.
        # Di Step 2, hitung_subkategori dipanggil.
        # So kita tidak perlu simpan lk_hasil di sini.
        
    hasil.output_primer_adhb = _round6(total_primer_b)
    hasil.output_primer_adhk = _round6(total_primer_k)

    if total_primer_b == 0 and total_primer_k == 0:
        hasil.peringatan.append(f"Semua output_primer = 0 untuk {subkategori_kode!r} {tahun}")
        return hasil

    rasio_os_b = get_rasio_safe(db, "OS_SEK", "ADHB", tahun, kategori_kode=subkategori_kode, wilayah_kode=wilayah_kode, default=Decimal(0))
    try:
        rasio_ka_b = get_rasio(db, "KA", "ADHB", tahun, kategori_kode=subkategori_kode, wilayah_kode=wilayah_kode)
    except RasioTidakDitemukanError:
        rasio_ka_b = Decimal(0)
        hasil.peringatan.append(f"Rasio KA ADHB tidak ditemukan untuk {subkategori_kode!r} {tahun}")

    adj_b = adj_adhb_manual
    os_b = _round6(total_primer_b * rasio_os_b)
    total_b = _round6(total_primer_b + os_b)
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

    rasio_os_k = get_rasio_safe(db, "OS_SEK", "ADHK", TAHUN_DASAR, kategori_kode=subkategori_kode, wilayah_kode=wilayah_kode, default=Decimal(0))
    rasio_ka_k = get_rasio_safe(db, "KA", "ADHK", TAHUN_DASAR, kategori_kode=subkategori_kode, wilayah_kode=wilayah_kode, default=Decimal(0))

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

def hitung_kategori_deflasi_standar(
    db: Session,
    kategori_kode: str,
    wilayah_kode: str,
    tahun: int,
    triwulan: Optional[int] = None,
    output_total_adhb: Optional[Decimal] = None,
) -> HasilSubkategori:
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

    rasio_ka_b = get_rasio_safe(db, "KA", "ADHB", tahun, kategori_kode=kategori_kode, wilayah_kode=wilayah_kode, default=Decimal(0))
    ka_b = _round6(output_total_adhb * rasio_ka_b)
    ntb_sebelum_adj_b = _round6(output_total_adhb - ka_b)
    ntb_final_b = _round6(ntb_sebelum_adj_b + adj_adhb_manual)

    rasio_ka_k = get_rasio_safe(db, "KA", "ADHK", TAHUN_DASAR, kategori_kode=kategori_kode, wilayah_kode=wilayah_kode, default=Decimal(0))
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
