"""
Tests: KalkulasiService
Verifikasi akurasi perhitungan output komoditas dan subkategori.
Menggunakan data fixture minimal untuk validasi formula ADHB dan ADHK.
"""
from __future__ import annotations

from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from app.database import Base
from app.models.kategori_pdrb import KategoriPdrb
from app.models.komoditas import Komoditas
from app.models.input_data import InputHarga, InputProduksi
from app.models.rasio import RasioReferensi
from app.models.wilayah import Wilayah
from app.services.kalkulasi_service import hitung_output_komoditas, hitung_subkategori


@pytest.fixture(scope="module")
def db_engine():
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)


@pytest.fixture
def db(db_engine) -> Session:
    connection = db_engine.connect()
    transaction = connection.begin()
    session = sessionmaker(bind=connection)()
    yield session
    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def setup_kalkulasi(db: Session):
    """
    Data fixture lengkap untuk satu komoditas (Padi Sawah).
    Nilai diambil dari contoh nyata LK BPS:
      Produksi: 5.000 Ton
      Harga Berlaku 2023: Rp 5.000.000/Ton
      Harga Konstan 2010: Rp 3.000.000/Ton
      Rasio OS ADHB 2023: 16.16%
      Rasio WIP ADHB 2023: 14.14% (tanaman pangan)
      Rasio KA ADHB 2023: 25.25%
      Rasio ADJ ADHB 2023: 10.12%
    """
    # Master data
    wilayah = Wilayah(kode="65", nama="Kaltara", level="provinsi", parent_kode=None)
    kat_root = KategoriPdrb(kode="1", nama="Pertanian", parent_kode=None, level=1,
                             metode_adhb="Produksi", metode_adhk="Revaluasi", urutan=10)
    kat_sub = KategoriPdrb(kode="1.1", nama="Pertanian Tanaman", parent_kode="1", level=2,
                            metode_adhb="Produksi", metode_adhk="Revaluasi", urutan=11)
    kat = KategoriPdrb(kode="1.1.a", nama="Tanaman Pangan", parent_kode="1.1", level=3,
                       metode_adhb="Produksi", metode_adhk="Revaluasi", urutan=12)
    kom = Komoditas(kode_internal="TPN-PADI-SAWAH", nama="Padi Sawah", kategori_kode="1.1.a",
                    satuan_produksi="Ton", satuan_harga="Rp/Ton", aktif=True)
    db.add_all([wilayah, kat_root, kat_sub, kat, kom])
    db.flush()

    # Input data
    prod = InputProduksi(
        komoditas_id=kom.id, wilayah_kode="65", tahun=2023,
        triwulan=None, kuantum=Decimal("5000.000000"),
        sumber_data="Dinas Pertanian", status="sementara",
    )
    harga_berlaku = InputHarga(
        komoditas_id=kom.id, wilayah_kode="65", tahun=2023,
        triwulan=None, harga_berlaku=Decimal("5000000.00"),
        harga_konstan_2010=None,
    )
    harga_konstan = InputHarga(
        komoditas_id=kom.id, wilayah_kode="65", tahun=2010,
        triwulan=None, harga_berlaku=Decimal("3000000.00"),
        harga_konstan_2010=Decimal("3000000.00"),
    )
    db.add_all([prod, harga_berlaku, harga_konstan])
    db.flush()

    # Rasio (tahun 2023 untuk ADHB, tahun 2010 untuk ADHK)
    rasio_data = [
        # (kategori_kode, jenis, tahun, nilai, berlaku_untuk)
        ("1.1.a", "OS",  2023, Decimal("0.161600"), "ADHB"),
        ("1.1.a", "WIP", 2023, Decimal("0.141400"), "ADHB"),
        ("1.1.a", "KA",  2023, Decimal("0.252500"), "ADHB"),
        ("1.1.a", "ADJ", 2023, Decimal("0.101200"), "ADHB"),
        # ADHK pakai rasio tahun dasar 2010
        ("1.1.a", "OS",  2010, Decimal("0.151500"), "ADHK"),
        ("1.1.a", "WIP", 2010, Decimal("0.131300"), "ADHK"),
        ("1.1.a", "KA",  2010, Decimal("0.202000"), "ADHK"),
        ("1.1.a", "ADJ", 2010, Decimal("0.125600"), "ADHK"),
    ]
    for kat_kode, jenis, tahun, nilai, berlaku in rasio_data:
        r = RasioReferensi(
            komoditas_id=None, kategori_kode=kat_kode,
            jenis_rasio=jenis, tahun=tahun, nilai=nilai, berlaku_untuk=berlaku,
        )
        db.add(r)
    db.flush()

    return {"kom": kom, "wilayah_kode": "65"}


# ─────────────────────────────────────────────────────────────────────────────
# Tests: hitung_output_komoditas
# ─────────────────────────────────────────────────────────────────────────────

def test_output_utama_adhb(db: Session, setup_kalkulasi):
    """output_utama_adhb = 5000 Ton × Rp5.000.000 / 1.000.000 = Rp 25.000 juta."""
    kom = setup_kalkulasi["kom"]
    hasil = hitung_output_komoditas(db, kom.id, "65", 2023)
    assert hasil.error is None
    assert hasil.output_utama_adhb == Decimal("25000.000000")


def test_output_ikutan_adhb(db: Session, setup_kalkulasi):
    """output_ikutan_adhb = 25.000 × 16.16% = 4.040 juta."""
    kom = setup_kalkulasi["kom"]
    hasil = hitung_output_komoditas(db, kom.id, "65", 2023)
    expected = Decimal("25000.000000") * Decimal("0.161600")
    assert hasil.output_ikutan_adhb == expected.quantize(Decimal("0.000001"))


def test_wip_adhb(db: Session, setup_kalkulasi):
    """wip_adhb = 25.000 × 14.14% = 3.535 juta."""
    kom = setup_kalkulasi["kom"]
    hasil = hitung_output_komoditas(db, kom.id, "65", 2023)
    expected = Decimal("25000.000000") * Decimal("0.141400")
    assert hasil.wip_adhb == expected.quantize(Decimal("0.000001"))


def test_output_sebelum_adj_adhb(db: Session, setup_kalkulasi):
    """output_sebelum_adj = utama + ikutan + wip."""
    kom = setup_kalkulasi["kom"]
    hasil = hitung_output_komoditas(db, kom.id, "65", 2023)
    expected = hasil.output_utama_adhb + hasil.output_ikutan_adhb + hasil.wip_adhb
    assert hasil.output_sebelum_adj_adhb == expected.quantize(Decimal("0.000001"))


def test_output_utama_adhk_pakai_harga_2010(db: Session, setup_kalkulasi):
    """output_utama_adhk = 5000 Ton × Rp3.000.000 / 1.000.000 = Rp 15.000 juta."""
    kom = setup_kalkulasi["kom"]
    hasil = hitung_output_komoditas(db, kom.id, "65", 2023)
    assert hasil.output_utama_adhk == Decimal("15000.000000")


def test_adhk_pakai_rasio_tahun_2010(db: Session, setup_kalkulasi):
    """ADHK menggunakan rasio OS 2010 (0.1515), bukan rasio 2023 (0.1616)."""
    kom = setup_kalkulasi["kom"]
    hasil = hitung_output_komoditas(db, kom.id, "65", 2023)
    # Rasio OS ADHK = 2010 punya nilai 0.151500
    expected_ikutan_k = Decimal("15000.000000") * Decimal("0.151500")
    assert hasil.output_ikutan_adhk == expected_ikutan_k.quantize(Decimal("0.000001"))


def test_error_jika_tidak_ada_produksi(db: Session, setup_kalkulasi):
    """Kembalikan error jika data produksi tidak tersedia."""
    kom = setup_kalkulasi["kom"]
    hasil = hitung_output_komoditas(db, kom.id, "65", 2019)  # tahun 2019 tidak ada data
    assert hasil.error is not None
    assert "produksi" in hasil.error.lower()


# ─────────────────────────────────────────────────────────────────────────────
# Tests: hitung_subkategori
# ─────────────────────────────────────────────────────────────────────────────

def test_ntb_adhb_positif(db: Session, setup_kalkulasi):
    """NTB ADHB harus positif untuk pertanian normal."""
    hasil = hitung_subkategori(db, "1.1.a", "65", 2023)
    assert hasil.ntb_adhb > 0


def test_output_total_adhb_lebih_besar_dari_primer(db: Session, setup_kalkulasi):
    """output_total = primer + sekunder + adj > primer."""
    hasil = hitung_subkategori(db, "1.1.a", "65", 2023)
    assert hasil.output_total_adhb > hasil.output_primer_adhb


def test_ntb_adhb_sama_dengan_output_minus_ka(db: Session, setup_kalkulasi):
    """ntb = output_total - ka."""
    hasil = hitung_subkategori(db, "1.1.a", "65", 2023)
    expected = hasil.output_total_adhb - hasil.ka_adhb
    assert abs(hasil.ntb_adhb - expected) < Decimal("0.000010")  # toleransi pembulatan


def test_rasio_ka_adhb_tersimpan(db: Session, setup_kalkulasi):
    """Rasio KA ADHB yang digunakan tersimpan di hasil."""
    hasil = hitung_subkategori(db, "1.1.a", "65", 2023)
    assert hasil.rasio_ka_adhb == Decimal("0.252500")


def test_subkategori_tanpa_komoditas(db: Session, setup_kalkulasi):
    """Subkategori tanpa komoditas kembalikan peringatan, bukan error."""
    hasil = hitung_subkategori(db, "1.3", "65", 2023)  # Perikanan — tidak ada komoditas di fixture
    assert len(hasil.peringatan) > 0
    assert hasil.ntb_adhb == Decimal(0)


# ─────────────────────────────────────────────────────────────────────────────
# Tests: Konversi faktor (CPO dari TBS)
# ─────────────────────────────────────────────────────────────────────────────

def test_faktor_konversi_sawit(db: Session):
    """Produksi TBS × faktor_konversi 0.20 = produksi CPO."""
    # Buat komoditas CPO dengan faktor konversi 0.20
    kat = KategoriPdrb(kode="1.1.e", nama="Perkebunan Tahunan", parent_kode="1.1", level=3,
                       metode_adhb="Produksi", metode_adhk="Revaluasi", urutan=16)
    wilayah = Wilayah(kode="65", nama="Kaltara", level="provinsi", parent_kode=None)
    kom = Komoditas(kode_internal="PKB-TAH-SAWIT-CPO", nama="Kelapa Sawit - CPO",
                    kategori_kode="1.1.e", satuan_produksi="Ton", satuan_harga="Rp/Ton",
                    faktor_konversi=Decimal("0.200000"), wujud_produksi="TBS", aktif=True)
    db.add_all([kat, wilayah, kom])
    db.flush()

    # TBS = 10.000 Ton → CPO = 10.000 × 0.20 = 2.000 Ton
    prod = InputProduksi(komoditas_id=kom.id, wilayah_kode="65", tahun=2023,
                         triwulan=None, kuantum=Decimal("10000.000000"), status="sementara")
    harga = InputHarga(komoditas_id=kom.id, wilayah_kode="65", tahun=2023,
                       triwulan=None, harga_berlaku=Decimal("10000000.00"))
    harga_2010 = InputHarga(komoditas_id=kom.id, wilayah_kode="65", tahun=2010,
                             triwulan=None, harga_berlaku=Decimal("6000000.00"),
                             harga_konstan_2010=Decimal("6000000.00"))
    rasio_os = RasioReferensi(komoditas_id=None, kategori_kode="1.1.e", jenis_rasio="OS",
                               tahun=2023, nilai=Decimal("0.161600"), berlaku_untuk="ADHB")
    rasio_wip = RasioReferensi(komoditas_id=None, kategori_kode="1.1.e", jenis_rasio="WIP",
                                tahun=2023, nilai=Decimal("0.141400"), berlaku_untuk="ADHB")
    rasio_os_k = RasioReferensi(komoditas_id=None, kategori_kode="1.1.e", jenis_rasio="OS",
                                 tahun=2010, nilai=Decimal("0.151500"), berlaku_untuk="ADHK")
    rasio_wip_k = RasioReferensi(komoditas_id=None, kategori_kode="1.1.e", jenis_rasio="WIP",
                                  tahun=2010, nilai=Decimal("0.131300"), berlaku_untuk="ADHK")
    db.add_all([prod, harga, harga_2010, rasio_os, rasio_wip, rasio_os_k, rasio_wip_k])
    db.flush()

    hasil = hitung_output_komoditas(db, kom.id, "65", 2023)
    assert hasil.error is None
    # CPO = 2.000 Ton × Rp10.000.000 / 1.000.000 = Rp 20.000 juta
    assert hasil.output_utama_adhb == Decimal("20000.000000")
