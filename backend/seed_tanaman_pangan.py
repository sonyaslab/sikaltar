"""
seed_tanaman_pangan.py
======================
Seed data LENGKAP dan TERKOREKSI untuk subkategori Tanaman Pangan (1.1.a).

Cara pakai:
  1. Pastikan PostgreSQL + backend sudah jalan (docker-compose up atau manual)
  2. Jalankan dari folder backend/:
       python seed_tanaman_pangan.py
  3. Script ini AMAN dijalankan berulang (upsert — update jika sudah ada)

Perbedaan dari seed_data.py lama:
  ✅ Komoditas lengkap 7 (bukan 3)
  ✅ Satuan harga BENAR: Rp/Ton + faktor_konversi=1
     (lama: Rp/Kg + faktor=1000 → overflow kalkulasi)
  ✅ Harga konstan 2010 dari Excel Indikator Produksi
  ✅ RasioReferensi KA/OS/ADJ diisi (sebelumnya tidak ada sama sekali)
"""

import os
import sys
from decimal import Decimal

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session

from app.database import SessionLocal, engine, Base
from app.models.wilayah import Wilayah
from app.models.kategori_pdrb import KategoriPdrb
from app.models.komoditas import Komoditas
from app.models.rasio import RasioReferensi
from app.models.input_data import InputHarga, InputProduksi


# ─── Helper: upsert ringan ────────────────────────────────────────────────────

def _upsert_komoditas(db: Session, data: dict) -> Komoditas:
    """Tambah komoditas baru atau update jika kode_internal sudah ada."""
    row = db.query(Komoditas).filter_by(kode_internal=data["kode_internal"]).first()
    if row:
        for k, v in data.items():
            setattr(row, k, v)
        print(f"  [UPDATE] Komoditas {data['kode_internal']} — {data['nama']}")
    else:
        row = Komoditas(**data)
        db.add(row)
        print(f"  [INSERT] Komoditas {data['kode_internal']} — {data['nama']}")
    return row


def _upsert_harga(db: Session, data: dict):
    row = db.query(InputHarga).filter_by(
        komoditas_id=data["komoditas_id"],
        wilayah_kode=data["wilayah_kode"],
        tahun=data["tahun"],
        triwulan=data.get("triwulan"),
    ).first()
    if row:
        for k, v in data.items():
            setattr(row, k, v)
    else:
        db.add(InputHarga(**data))


def _upsert_produksi(db: Session, data: dict):
    row = db.query(InputProduksi).filter_by(
        komoditas_id=data["komoditas_id"],
        wilayah_kode=data["wilayah_kode"],
        tahun=data["tahun"],
        triwulan=data.get("triwulan"),
    ).first()
    if row:
        for k, v in data.items():
            setattr(row, k, v)
    else:
        db.add(InputProduksi(**data))


def _upsert_rasio(db: Session, data: dict):
    row = db.query(RasioReferensi).filter_by(
        komoditas_id=data.get("komoditas_id"),
        kategori_kode=data.get("kategori_kode"),
        jenis_rasio=data["jenis_rasio"],
        tahun=data["tahun"],
        berlaku_untuk=data["berlaku_untuk"],
    ).first()
    if row:
        row.nilai = data["nilai"]
    else:
        db.add(RasioReferensi(**data))


# ─── MAIN SEED ────────────────────────────────────────────────────────────────

def seed_tanaman_pangan():
    print("\n" + "=" * 60)
    print("  SEED: Tanaman Pangan (1.1.a) — Kalimantan Utara")
    print("=" * 60)

    db: Session = SessionLocal()
    try:
        Base.metadata.create_all(bind=engine)

        # ── 1. Wilayah (skip jika sudah ada) ─────────────────────────────────
        if db.query(Wilayah).count() == 0:
            print("\n[1] Seeding Wilayah...")
            db.add_all([
                Wilayah(kode="65",   nama="Kalimantan Utara",     level="provinsi"),
                Wilayah(kode="6501", nama="Kabupaten Malinau",    level="kabupaten", parent_kode="65"),
                Wilayah(kode="6502", nama="Kabupaten Bulungan",   level="kabupaten", parent_kode="65"),
                Wilayah(kode="6503", nama="Kabupaten Tana Tidung",level="kabupaten", parent_kode="65"),
                Wilayah(kode="6504", nama="Kabupaten Nunukan",    level="kabupaten", parent_kode="65"),
                Wilayah(kode="6571", nama="Kota Tarakan",         level="kota",      parent_kode="65"),
            ])
            db.commit()
            print("  ✅ Wilayah selesai")
        else:
            print("\n[1] Wilayah sudah ada — dilewati")

        # ── 2. Kategori PDRB (skip jika sudah ada) ───────────────────────────
        if db.query(KategoriPdrb).filter_by(kode="1.1.a").first() is None:
            print("\n[2] Seeding Kategori PDRB...")
            db.add_all([
                KategoriPdrb(kode="1",     nama="Pertanian, Kehutanan, dan Perikanan",
                             level=1, urutan=1),
                KategoriPdrb(kode="1.1",   nama="Pertanian, Peternakan, Perburuan dan Jasa Pertanian",
                             parent_kode="1", level=2, urutan=2),
                KategoriPdrb(kode="1.1.a", nama="Tanaman Pangan",
                             parent_kode="1.1", level=3,
                             metode_adhb="Produksi", metode_adhk="Revaluasi",
                             urutan=3),
            ])
            db.commit()
            print("  ✅ Kategori selesai")
        else:
            print("\n[2] Kategori 1.1.a sudah ada — dilewati")

        # ── 3. Komoditas — 7 jenis dari Excel ────────────────────────────────
        #
        # PENTING — Penjelasan unit:
        #   satuan_produksi = "Ton"   (input data dari petugas dalam Ton)
        #   satuan_harga    = "Rp/Ton"
        #   faktor_konversi = 1       (tidak ada konversi, langsung Ton × Rp/Ton)
        #
        #   Formula kalkulasi: output = kuantum × harga / 1.000.000  (→ Juta Rp)
        #   Contoh Padi: 18.500 Ton × 4.320.000 Rp/Ton / 1.000.000 = 79.920 Juta Rp ✓
        #
        print("\n[3] Seeding/Update Komoditas Tanaman Pangan...")
        komoditas_defs = [
            dict(kode_internal="11a01", kategori_kode="1.1.a", nama="Padi",
                 satuan_produksi="Ton", satuan_harga="Rp/Ton",
                 faktor_konversi=Decimal("1"), aktif=True,
                 wujud_produksi="GKG (Gabah Kering Giling)"),
            dict(kode_internal="11a02", kategori_kode="1.1.a", nama="Jagung",
                 satuan_produksi="Ton", satuan_harga="Rp/Ton",
                 faktor_konversi=Decimal("1"), aktif=True,
                 wujud_produksi="Pipilan Kering"),
            dict(kode_internal="11a03", kategori_kode="1.1.a", nama="Kedelai",
                 satuan_produksi="Ton", satuan_harga="Rp/Ton",
                 faktor_konversi=Decimal("1"), aktif=True,
                 wujud_produksi="Biji Kering"),
            dict(kode_internal="11a04", kategori_kode="1.1.a", nama="Kacang Tanah",
                 satuan_produksi="Ton", satuan_harga="Rp/Ton",
                 faktor_konversi=Decimal("1"), aktif=True,
                 wujud_produksi="Biji Kering"),
            dict(kode_internal="11a05", kategori_kode="1.1.a", nama="Kacang Hijau",
                 satuan_produksi="Ton", satuan_harga="Rp/Ton",
                 faktor_konversi=Decimal("1"), aktif=True,
                 wujud_produksi="Biji Kering"),
            dict(kode_internal="11a06", kategori_kode="1.1.a", nama="Ubi Kayu",
                 satuan_produksi="Ton", satuan_harga="Rp/Ton",
                 faktor_konversi=Decimal("1"), aktif=True,
                 wujud_produksi="Umbi Basah"),
            dict(kode_internal="11a07", kategori_kode="1.1.a", nama="Ubi Jalar",
                 satuan_produksi="Ton", satuan_harga="Rp/Ton",
                 faktor_konversi=Decimal("1"), aktif=True,
                 wujud_produksi="Umbi Basah"),
        ]
        for d in komoditas_defs:
            _upsert_komoditas(db, d)
        db.commit()
        print("  ✅ 7 komoditas tersimpan")

        # ── 4. Harga ──────────────────────────────────────────────────────────
        #
        # Sumber: Excel "Indikator Produksi" → Sheet "Harga (Juta Rp.)" Tahun Dasar 2010
        #   Nilai di Excel dalam Juta Rp/Ton → disimpan dalam Rp/Ton = nilai × 1.000.000
        #
        #   Padi       : 4.32    Juta Rp/Ton → 4.320.000 Rp/Ton
        #   Jagung     : 3.7053  Juta Rp/Ton → 3.705.300 Rp/Ton
        #   Kedelai    : 6.1267  Juta Rp/Ton → 6.126.700 Rp/Ton
        #   Kacang Tanah: 9.58   Juta Rp/Ton → 9.580.000 Rp/Ton
        #   Kacang Hijau: 7.2    Juta Rp/Ton → 7.200.000 Rp/Ton
        #   Ubi Kayu   : 2.33715 Juta Rp/Ton → 2.337.150 Rp/Ton
        #   Ubi Jalar  : 3.4101  Juta Rp/Ton → 3.410.100 Rp/Ton
        #
        # Catatan: harga_berlaku tahun 2010 = harga_konstan_2010 (tahun dasar)
        #
        print("\n[4] Seeding/Update Harga...")

        kom_map = {
            k.kode_internal: k.id
            for k in db.query(Komoditas).filter(
                Komoditas.kode_internal.in_(
                    ["11a01","11a02","11a03","11a04","11a05","11a06","11a07"]
                )
            ).all()
        }

        # Harga konstan 2010 (dari Excel)
        harga_konstan_2010 = {
            "11a01": Decimal("4320000"),    # Padi
            "11a02": Decimal("3705300"),    # Jagung
            "11a03": Decimal("6126700"),    # Kedelai
            "11a04": Decimal("9580000"),    # Kacang Tanah
            "11a05": Decimal("7200000"),    # Kacang Hijau
            "11a06": Decimal("2337150"),    # Ubi Kayu
            "11a07": Decimal("3410100"),    # Ubi Jalar
        }

        # Harga berlaku 2024 (estimasi dari IHP — Indeks Harga Produsen 2024)
        # Sumber: Sheet "IHP 2016 to 2010", rata-rata 4 triwulan 2024, basis 2010
        # Harga berlaku = harga_konstan × (IHP / 100)
        ihp_2024 = {
            "11a01": Decimal("181.47"),   # Padi     IHP basis 2010
            "11a02": Decimal("170.96"),   # Jagung
            "11a03": Decimal("147.58"),   # Kedelai
            "11a04": Decimal("191.56"),   # Kacang Tanah
            "11a05": Decimal("175.27"),   # Kacang Hijau
            "11a06": Decimal("198.70"),   # Ubi Kayu
            "11a07": Decimal("189.47"),   # Ubi Jalar
        }

        for kode, hk in harga_konstan_2010.items():
            kid = kom_map.get(kode)
            if not kid:
                continue

            # Tahun dasar 2010: harga berlaku = harga konstan (basis)
            _upsert_harga(db, dict(
                komoditas_id=kid, wilayah_kode="65",
                tahun=2010, triwulan=None,
                harga_berlaku=hk,
                harga_konstan_2010=hk,
                sumber_data="BPS RI — Indikator Produksi (Excel)",
            ))

            # Harga berlaku 2024 dari IHP
            ihp = ihp_2024.get(kode, Decimal("150"))
            hb_2024 = (hk * ihp / Decimal("100")).quantize(Decimal("1"))
            _upsert_harga(db, dict(
                komoditas_id=kid, wilayah_kode="65",
                tahun=2024, triwulan=None,
                harga_berlaku=hb_2024,
                harga_konstan_2010=hk,
                sumber_data="Estimasi dari IHP 2024 (basis 2010)",
            ))

        db.commit()
        print("  ✅ Harga 2010 dan 2024 tersimpan")

        # ── 5. Produksi (contoh data — GANTI dengan data riil BPS Kaltara) ──
        #
        # ⚠️  Data produksi di bawah adalah SIMULASI untuk uji coba.
        #     Ganti dengan data riil dari:
        #     - Sistem Kerangka Sampel Area (KSA) untuk Padi
        #     - Survei Ubinan + SM Produksi untuk komoditas lain
        #
        print("\n[5] Seeding/Update Produksi (data uji — ganti dgn data riil)...")

        produksi_2010 = {   # Baseline tahun dasar (Ton)
            "11a01": Decimal("18500"),
            "11a02": Decimal("3200"),
            "11a03": Decimal("180"),
            "11a04": Decimal("95"),
            "11a05": Decimal("55"),
            "11a06": Decimal("12000"),
            "11a07": Decimal("4500"),
        }
        produksi_2024 = {   # Data berjalan 2024 (Ton, simulasi)
            "11a01": Decimal("21300"),
            "11a02": Decimal("4800"),
            "11a03": Decimal("130"),
            "11a04": Decimal("75"),
            "11a05": Decimal("40"),
            "11a06": Decimal("14500"),
            "11a07": Decimal("5200"),
        }

        for kode, q in produksi_2010.items():
            kid = kom_map.get(kode)
            if kid:
                _upsert_produksi(db, dict(
                    komoditas_id=kid, wilayah_kode="65",
                    tahun=2010, triwulan=None, kuantum=q,
                    sumber_data="Data Baseline 2010 (uji coba)",
                    status="tetap",
                ))
        for kode, q in produksi_2024.items():
            kid = kom_map.get(kode)
            if kid:
                _upsert_produksi(db, dict(
                    komoditas_id=kid, wilayah_kode="65",
                    tahun=2024, triwulan=None, kuantum=q,
                    sumber_data="Simulasi BPS Kaltara 2024 (uji coba)",
                    status="sementara",
                ))

        db.commit()
        print("  ✅ Produksi tersimpan (14 record: 2010 + 2024)")

        # ── 6. Rasio Referensi ────────────────────────────────────────────────
        #
        # Sumber: Excel "Indikator Produksi" → bagian NTB ADHB / NTB ADHK
        #   Tanaman Pangan (Utama): Rasio KA  = 0.1352  ← Konsumsi Antara
        #   Tanaman Pangan (Sekunder): Rasio OS = 0.10   ← Output ikutan/coverage
        #   Adjustment Coverage: Rasio ADJ     = 0.10    ← Koreksi cakupan
        #
        # berlaku_untuk="KEDUANYA" artinya rasio sama untuk ADHB dan ADHK
        # Untuk ADHB: dipakai rasio tahun berjalan
        # Untuk ADHK: kalkulasi_service.py pakai rasio tahun DASAR (2010)
        #
        print("\n[6] Seeding/Update Rasio Referensi...")

        # Tahun yang perlu diisi: minimal 2010 (tahun dasar) + tahun berjalan
        tahun_rasio = [2010, 2020, 2021, 2022, 2023, 2024]

        for tahun in tahun_rasio:
            _upsert_rasio(db, dict(
                komoditas_id=None, kategori_kode="1.1.a",
                jenis_rasio="KA", tahun=tahun,
                nilai=Decimal("0.1352"),
                berlaku_untuk="KEDUANYA",
            ))
            _upsert_rasio(db, dict(
                komoditas_id=None, kategori_kode="1.1.a",
                jenis_rasio="OS", tahun=tahun,
                nilai=Decimal("0.1"),
                berlaku_untuk="KEDUANYA",
            ))
            _upsert_rasio(db, dict(
                komoditas_id=None, kategori_kode="1.1.a",
                jenis_rasio="ADJ", tahun=tahun,
                nilai=Decimal("0.1"),
                berlaku_untuk="KEDUANYA",
            ))
            # WIP = 0 untuk tanaman pangan (tidak ada WIP)
            _upsert_rasio(db, dict(
                komoditas_id=None, kategori_kode="1.1.a",
                jenis_rasio="WIP", tahun=tahun,
                nilai=Decimal("0"),
                berlaku_untuk="KEDUANYA",
            ))

        db.commit()
        print(f"  ✅ Rasio KA/OS/ADJ/WIP tersimpan untuk {len(tahun_rasio)} tahun")

        # ── Ringkasan ─────────────────────────────────────────────────────────
        print("\n" + "=" * 60)
        print("✅ SEED SELESAI — Ringkasan:")
        print(f"   Komoditas  : {db.query(Komoditas).filter_by(kategori_kode='1.1.a').count()} (Tanaman Pangan)")
        print(f"   Input Harga: {db.query(InputHarga).count()} record")
        print(f"   Input Prod : {db.query(InputProduksi).count()} record")
        print(f"   Rasio Ref  : {db.query(RasioReferensi).count()} record")
        print("=" * 60)
        print()
        print("Langkah selanjutnya:")
        print("  1. Buka S1.P di browser → cek komoditas Tanaman Pangan muncul")
        print("  2. Buka S1.H → cek harga 2010 & 2024 terisi")
        print("  3. Jalankan kalkulasi S2 → cek NTB di tabel pokok S3")
        print("  4. Ganti data produksi simulasi dengan data riil BPS")
        print()

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    seed_tanaman_pangan()