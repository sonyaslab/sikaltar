"""
Tests: RasioService
Verifikasi sistem priority lookup: override → referensi → parent fallback → error
"""
from __future__ import annotations

from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from app.database import Base
from app.models.kategori_pdrb import KategoriPdrb
from app.models.komoditas import Komoditas
from app.models.rasio import RasioReferensi, RasioOverride
from app.models.wilayah import Wilayah
from app.services.rasio_service import get_rasio, get_rasio_safe, RasioTidakDitemukanError


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def db_engine():
    """In-memory SQLite untuk testing (tidak perlu PostgreSQL)."""
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)


@pytest.fixture
def db(db_engine) -> Session:
    """Session dengan rollback otomatis setelah setiap test."""
    connection = db_engine.connect()
    transaction = connection.begin()
    session = sessionmaker(bind=connection)()
    yield session
    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def setup_master_data(db: Session):
    """Seed data minimal: 1 wilayah, 1 kategori, 1 komoditas."""
    wilayah = Wilayah(kode="65", nama="Prov. Kaltara", level="provinsi", parent_kode=None)
    wilayah_kab = Wilayah(kode="6501", nama="Kab. Malinau", level="kabupaten", parent_kode="65")
    kat = KategoriPdrb(kode="1.1.a", nama="Tanaman Pangan", parent_kode="1.1", level=3,
                       metode_adhb="Produksi", metode_adhk="Revaluasi", urutan=12)
    kat_parent = KategoriPdrb(kode="1.1", nama="Pertanian", parent_kode="1", level=2,
                               metode_adhb="Produksi", metode_adhk="Revaluasi", urutan=11)
    kat_root = KategoriPdrb(kode="1", nama="Pertanian, Kehutanan, Perikanan", parent_kode=None,
                             level=1, metode_adhb="Produksi", metode_adhk="Revaluasi", urutan=10)
    kom = Komoditas(kode_internal="TPN-PADI-SAWAH", nama="Padi Sawah", kategori_kode="1.1.a",
                    satuan_produksi="Ton", satuan_harga="Rp/Ton", aktif=True)

    db.add_all([wilayah, wilayah_kab, kat_root, kat_parent, kat, kom])
    db.flush()
    return {"wilayah": wilayah, "kat": kat, "kom": kom}


# ─────────────────────────────────────────────────────────────────────────────
# Tests: Referensi (default nasional)
# ─────────────────────────────────────────────────────────────────────────────

def test_get_rasio_dari_referensi_kategori(db: Session, setup_master_data):
    """Rasio ditemukan langsung dari rasio_referensi per kategori."""
    rasio = RasioReferensi(
        komoditas_id=None, kategori_kode="1.1.a",
        jenis_rasio="OS", tahun=2023, nilai=Decimal("0.161600"), berlaku_untuk="ADHB"
    )
    db.add(rasio)
    db.flush()

    result = get_rasio(db, "OS", "ADHB", 2023, kategori_kode="1.1.a")
    assert result == Decimal("0.161600")


def test_get_rasio_fallback_ke_parent_1_level(db: Session, setup_master_data):
    """Jika tidak ada di 1.1.a, fallback ke parent 1.1."""
    rasio = RasioReferensi(
        komoditas_id=None, kategori_kode="1.1",
        jenis_rasio="KA", tahun=2023, nilai=Decimal("0.252500"), berlaku_untuk="ADHB"
    )
    db.add(rasio)
    db.flush()

    result = get_rasio(db, "KA", "ADHB", 2023, kategori_kode="1.1.a")
    assert result == Decimal("0.252500")


def test_get_rasio_fallback_ke_parent_2_level(db: Session, setup_master_data):
    """Fallback melewati 2 level: 1.1.a → 1.1 → 1."""
    rasio = RasioReferensi(
        komoditas_id=None, kategori_kode="1",
        jenis_rasio="ADJ", tahun=2023, nilai=Decimal("0.101200"), berlaku_untuk="ADHK"
    )
    db.add(rasio)
    db.flush()

    result = get_rasio(db, "ADJ", "ADHK", 2023, kategori_kode="1.1.a")
    assert result == Decimal("0.101200")


def test_get_rasio_berlaku_keduanya(db: Session, setup_master_data):
    """Rasio dengan berlaku_untuk='KEDUANYA' cocok untuk ADHB maupun ADHK."""
    rasio = RasioReferensi(
        komoditas_id=None, kategori_kode="1.1.a",
        jenis_rasio="WIP", tahun=2023, nilai=Decimal("0.141400"), berlaku_untuk="KEDUANYA"
    )
    db.add(rasio)
    db.flush()

    assert get_rasio(db, "WIP", "ADHB", 2023, kategori_kode="1.1.a") == Decimal("0.141400")
    assert get_rasio(db, "WIP", "ADHK", 2023, kategori_kode="1.1.a") == Decimal("0.141400")


# ─────────────────────────────────────────────────────────────────────────────
# Tests: Override (prioritas lebih tinggi dari referensi)
# ─────────────────────────────────────────────────────────────────────────────

def test_override_lebih_prioritas_dari_referensi(db: Session, setup_master_data):
    """Override per wilayah mengalahkan referensi nasional."""
    # Referensi nasional
    referensi = RasioReferensi(
        komoditas_id=None, kategori_kode="1.1.a",
        jenis_rasio="OS", tahun=2023, nilai=Decimal("0.161600"), berlaku_untuk="ADHB"
    )
    # Override untuk Kab. Malinau
    override = RasioOverride(
        komoditas_id=None, kategori_kode="1.1.a",
        jenis_rasio="OS", wilayah_kode="6501",
        tahun=2023, nilai=Decimal("0.180000"), berlaku_untuk="ADHB",
        keterangan="Penyesuaian kondisi lokal Malinau",
    )
    db.add_all([referensi, override])
    db.flush()

    # Tanpa wilayah → pakai referensi
    result_nasional = get_rasio(db, "OS", "ADHB", 2023, kategori_kode="1.1.a")
    assert result_nasional == Decimal("0.161600")

    # Dengan wilayah "6501" → pakai override
    result_lokal = get_rasio(db, "OS", "ADHB", 2023, kategori_kode="1.1.a", wilayah_kode="6501")
    assert result_lokal == Decimal("0.180000")

    # Wilayah lain (6502) → jatuh ke referensi
    result_lain = get_rasio(db, "OS", "ADHB", 2023, kategori_kode="1.1.a", wilayah_kode="6502")
    assert result_lain == Decimal("0.161600")


# ─────────────────────────────────────────────────────────────────────────────
# Tests: Error dan safe mode
# ─────────────────────────────────────────────────────────────────────────────

def test_raise_error_jika_tidak_ditemukan(db: Session, setup_master_data):
    """RasioTidakDitemukanError jika tidak ada rasio sama sekali."""
    with pytest.raises(RasioTidakDitemukanError) as exc_info:
        get_rasio(db, "CBR", "ADHB", 2023, kategori_kode="1.1.a")

    err = exc_info.value
    assert err.jenis_rasio == "CBR"
    assert err.tahun == 2023


def test_get_rasio_safe_kembalikan_default(db: Session, setup_master_data):
    """get_rasio_safe tidak raise error, kembalikan default."""
    result = get_rasio_safe(
        db, "CBR", "ADHB", 2023,
        kategori_kode="1.1.a",
        default=Decimal("0.0")
    )
    assert result == Decimal("0.0")


def test_get_rasio_safe_kembalikan_none_jika_tidak_ada_default(db: Session, setup_master_data):
    """get_rasio_safe kembalikan None jika default tidak diisi."""
    result = get_rasio_safe(db, "CBR", "ADHB", 2023, kategori_kode="1.1.a")
    assert result is None


# ─────────────────────────────────────────────────────────────────────────────
# Tests: Jadwal tahun (OS berbeda 2008-2010 vs 2011+)
# ─────────────────────────────────────────────────────────────────────────────

def test_rasio_os_berbeda_per_tahun(db: Session, setup_master_data):
    """Rasio OS 0.1515 untuk 2010, 0.1616 untuk 2023."""
    rasio_lama = RasioReferensi(
        komoditas_id=None, kategori_kode="1.1.a",
        jenis_rasio="OS", tahun=2010, nilai=Decimal("0.151500"), berlaku_untuk="ADHB"
    )
    rasio_baru = RasioReferensi(
        komoditas_id=None, kategori_kode="1.1.a",
        jenis_rasio="OS", tahun=2023, nilai=Decimal("0.161600"), berlaku_untuk="ADHB"
    )
    db.add_all([rasio_lama, rasio_baru])
    db.flush()

    assert get_rasio(db, "OS", "ADHB", 2010, kategori_kode="1.1.a") == Decimal("0.151500")
    assert get_rasio(db, "OS", "ADHB", 2023, kategori_kode="1.1.a") == Decimal("0.161600")
