"""
seed_uji_coba.py  —  SEED MANDIRI + UJI COBA TABEL POKOK
=========================================================
Letakкan file ini di folder `backend/` (sejajar dengan folder `app/`).

Jalankan:
    cd backend
    .venv\\Scripts\\activate          (Windows)   atau  source .venv/bin/activate
    python seed_uji_coba.py

Script ini AMAN dijalankan berulang (idempoten): data yang sudah ada akan
di-update, bukan diduplikasi. Yang dilakukan:
  1. Buat tabel bila belum ada (Base.metadata.create_all)
  2. Seed 6 wilayah Kaltara
  3. Seed 17 kategori + seluruh subkategori (SNA 2008)
  4. Seed contoh komoditas + produksi + harga (Padi, Jagung, Sawit, Batubara)
  5. Seed rasio (OS, WIP, KA, ADJ) untuk komoditas tsb
  6. Seed 1 kategori metode DEFLASI sebagai contoh (6 Konstruksi):
        input Output ADHB langsung + indeks deflator
  7. Jalankan cascade (sync_recalculate) untuk 2022 & 2023
  8. Cetak Tabel Pokok PDRB (ADHB & ADHK) per kategori
"""
from __future__ import annotations

import os
import sys
from decimal import Decimal

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database import SessionLocal, engine, Base
from app.models.wilayah import Wilayah
from app.models.kategori_pdrb import KategoriPdrb
from app.models.komoditas import Komoditas
from app.models.input_data import InputProduksi, InputHarga, InputIndeksDeflator
from app.models.rasio import RasioReferensi
from app.models.hasil import PdrbRekap
from app.services.cascade_service import sync_recalculate

WILAYAH = "65"
TAHUN_DASAR = 2010
TAHUN_UJI = [2022, 2023]

# ─── 17 kategori + subkategori (kode, nama, parent, level, metode_adhb, metode_adhk, urutan) ───
KATEGORI_DATA = [
    ('1', 'Pertanian, Kehutanan dan Perikanan', None, 1, 'Produksi', 'Revaluasi', 10),
    ('1.1', 'Pertanian, Peternakan, Perburuan dan Jasa Pertanian', '1', 2, 'Produksi', 'Revaluasi', 11),
    ('1.1.a', 'Tanaman Pangan', '1.1', 3, 'Produksi', 'Revaluasi', 12),
    ('1.1.b', 'Tanaman Hortikultura Semusim', '1.1', 3, 'Produksi', 'Revaluasi', 13),
    ('1.1.c', 'Perkebunan Semusim', '1.1', 3, 'Produksi', 'Revaluasi', 14),
    ('1.1.d', 'Tanaman Hortikultura Tahunan dan Lainnya', '1.1', 3, 'Produksi', 'Revaluasi', 15),
    ('1.1.e', 'Perkebunan Tahunan', '1.1', 3, 'Produksi', 'Revaluasi', 16),
    ('1.1.f', 'Peternakan', '1.1', 3, 'Produksi', 'Revaluasi', 17),
    ('1.1.g', 'Jasa Pertanian dan Perburuan', '1.1', 3, 'Produksi', 'Revaluasi', 18),
    ('1.2', 'Kehutanan dan Penebangan Kayu', '1', 2, 'Produksi', 'Revaluasi', 20),
    ('1.3', 'Perikanan', '1', 2, 'Produksi', 'Revaluasi', 30),
    ('2', 'Pertambangan dan Penggalian', None, 1, 'Produksi', 'Revaluasi', 40),
    ('2.1', 'Pertambangan Minyak, Gas dan Panas Bumi', '2', 2, 'Produksi', 'Revaluasi', 41),
    ('2.2', 'Pertambangan Batubara dan Lignit', '2', 2, 'Produksi', 'Revaluasi', 42),
    ('2.3', 'Pertambangan Bijih Logam', '2', 2, 'Produksi', 'Revaluasi', 43),
    ('2.4', 'Pertambangan dan Penggalian Lainnya', '2', 2, 'Produksi', 'Revaluasi', 44),
    ('3', 'Industri Pengolahan', None, 1, 'Produksi', 'DoubleDflasi', 50),
    ('3.1', 'Industri Batubara dan Pengilangan Migas', '3', 2, 'Produksi', 'DoubleDflasi', 51),
    ('3.2', 'Industri Makanan dan Minuman', '3', 2, 'Produksi', 'DoubleDflasi', 52),
    ('3.3', 'Industri Pengolahan Tembakau', '3', 2, 'Produksi', 'DoubleDflasi', 53),
    ('3.4', 'Industri Tekstil dan Pakaian Jadi', '3', 2, 'Produksi', 'DoubleDflasi', 54),
    ('3.5', 'Industri Kulit, Barang dari Kulit dan Alas Kaki', '3', 2, 'Produksi', 'DoubleDflasi', 55),
    ('3.6', 'Industri Kayu, Barang dari Kayu dan Gabus; Anyaman', '3', 2, 'Produksi', 'DoubleDflasi', 56),
    ('3.7', 'Industri Kertas dan Barang dari Kertas; Percetakan', '3', 2, 'Produksi', 'DoubleDflasi', 57),
    ('3.8', 'Industri Kimia, Farmasi dan Obat Tradisional', '3', 2, 'Produksi', 'DoubleDflasi', 58),
    ('3.9', 'Industri Karet, Barang dari Karet dan Plastik', '3', 2, 'Produksi', 'DoubleDflasi', 59),
    ('3.10', 'Industri Barang Galian Bukan Logam', '3', 2, 'Produksi', 'DoubleDflasi', 60),
    ('3.11', 'Industri Logam Dasar', '3', 2, 'Produksi', 'DoubleDflasi', 61),
    ('3.12', 'Industri Barang dari Logam; Komputer, Elektronik, Optik; Listrik', '3', 2, 'Produksi', 'DoubleDflasi', 62),
    ('3.13', 'Industri Mesin dan Perlengkapan YTDL', '3', 2, 'Produksi', 'DoubleDflasi', 63),
    ('3.14', 'Industri Alat Angkutan', '3', 2, 'Produksi', 'DoubleDflasi', 64),
    ('3.15', 'Industri Furnitur', '3', 2, 'Produksi', 'DoubleDflasi', 65),
    ('3.16', 'Industri Pengolahan Lainnya; Jasa Reparasi dan Pemasangan Mesin', '3', 2, 'Produksi', 'DoubleDflasi', 66),
    ('4', 'Pengadaan Listrik dan Gas', None, 1, 'Produksi', 'Revaluasi', 70),
    ('4.1', 'Ketenagalistrikan', '4', 2, 'Produksi', 'Revaluasi', 71),
    ('4.2', 'Pengadaan Gas dan Produksi Es', '4', 2, 'Produksi', 'Revaluasi', 72),
    ('5', 'Pengadaan Air, Pengelolaan Sampah, Limbah dan Daur Ulang', None, 1, 'Produksi', 'Revaluasi', 80),
    ('6', 'Konstruksi', None, 1, 'CommodityFlow', 'Deflasi', 90),
    ('7', 'Perdagangan Besar dan Eceran; Reparasi Mobil dan Sepeda Motor', None, 1, 'Produksi', 'Revaluasi', 100),
    ('7.1', 'Perdagangan Mobil, Sepeda Motor dan Reparasinya', '7', 2, 'Produksi', 'Revaluasi', 101),
    ('7.2', 'Perdagangan Besar dan Eceran Bukan Mobil dan Sepeda Motor', '7', 2, 'Produksi', 'Deflasi', 102),
    ('8', 'Transportasi dan Pergudangan', None, 1, 'Produksi', 'Deflasi', 110),
    ('8.1', 'Angkutan Rel', '8', 2, 'Produksi', 'Deflasi', 111),
    ('8.2', 'Angkutan Darat', '8', 2, 'Produksi', 'Deflasi', 112),
    ('8.3', 'Angkutan Laut', '8', 2, 'Produksi', 'Deflasi', 113),
    ('8.4', 'Angkutan Sungai, Danau dan Penyeberangan', '8', 2, 'Produksi', 'Deflasi', 114),
    ('8.5', 'Angkutan Udara', '8', 2, 'Produksi', 'Deflasi', 115),
    ('8.6', 'Pergudangan dan Jasa Penunjang Angkutan; Pos dan Kurir', '8', 2, 'Produksi', 'Deflasi', 116),
    ('9', 'Penyediaan Akomodasi dan Makan Minum', None, 1, 'Produksi', 'Deflasi', 120),
    ('9.1', 'Penyediaan Akomodasi', '9', 2, 'Produksi', 'Deflasi', 121),
    ('9.2', 'Penyediaan Makan Minum', '9', 2, 'Produksi', 'Deflasi', 122),
    ('10', 'Informasi dan Komunikasi', None, 1, 'Produksi', 'Deflasi', 130),
    ('11', 'Jasa Keuangan dan Asuransi', None, 1, 'Langsung', 'Deflasi', 140),
    ('11.1', 'Jasa Perantara Keuangan', '11', 2, 'Langsung', 'Deflasi', 141),
    ('11.2', 'Asuransi dan Dana Pensiun', '11', 2, 'Langsung', 'Deflasi', 142),
    ('11.3', 'Jasa Keuangan Lainnya', '11', 2, 'Langsung', 'Deflasi', 143),
    ('11.4', 'Jasa Penunjang Keuangan', '11', 2, 'Langsung', 'Deflasi', 144),
    ('12', 'Real Estate', None, 1, 'Produksi', 'Deflasi', 150),
    ('13', 'Jasa Perusahaan', None, 1, 'Produksi', 'Deflasi', 160),
    ('14', 'Administrasi Pemerintahan, Pertahanan dan Jaminan Sosial Wajib', None, 1, 'Langsung', 'Deflasi', 170),
    ('15', 'Jasa Pendidikan', None, 1, 'Produksi', 'Deflasi', 180),
    ('16', 'Jasa Kesehatan dan Kegiatan Sosial', None, 1, 'Produksi', 'Deflasi', 190),
    ('17', 'Jasa Lainnya', None, 1, 'Produksi', 'Deflasi', 200),
]

WILAYAH_DATA = [
    ("65", "Provinsi Kalimantan Utara", "provinsi", None),
    ("6501", "Kabupaten Malinau", "kabupaten", "65"),
    ("6502", "Kabupaten Bulungan", "kabupaten", "65"),
    ("6503", "Kabupaten Tana Tidung", "kabupaten", "65"),
    ("6504", "Kabupaten Nunukan", "kabupaten", "65"),
    ("6571", "Kota Tarakan", "kota", "65"),
]


def upsert(db, model, filter_kwargs, values):
    row = db.query(model).filter_by(**filter_kwargs).first()
    if row:
        for k, v in values.items():
            setattr(row, k, v)
    else:
        row = model(**{**filter_kwargs, **values})
        db.add(row)
    db.flush()
    return row


def seed_wilayah(db):
    for kode, nama, level, parent in WILAYAH_DATA:
        upsert(db, Wilayah, {"kode": kode}, {"nama": nama, "level": level, "parent_kode": parent})
    print(f"  ✓ {len(WILAYAH_DATA)} wilayah")


def seed_kategori(db):
    # Insert parent dulu (urut by level) supaya FK parent_kode valid
    for kode, nama, parent, level, m_b, m_k, urut in sorted(KATEGORI_DATA, key=lambda x: x[3]):
        upsert(db, KategoriPdrb, {"kode": kode},
               {"nama": nama, "parent_kode": parent, "level": level,
                "metode_adhb": m_b, "metode_adhk": m_k, "urutan": urut})
    print(f"  ✓ {len(KATEGORI_DATA)} kategori/subkategori")


def seed_komoditas_dan_input(db):
    # (kode_internal, nama, kategori, satuan, faktor_konversi, harga2010,
    #  {tahun: (kuantum, harga_berlaku)})
    komoditas = [
        ("TPN-PADI", "Padi", "1.1.a", "Ton", None, Decimal("4700000"),
         {2022: (Decimal("120000"), Decimal("5000000")),
          2023: (Decimal("128000"), Decimal("5300000"))}),
        ("TPN-JAGUNG", "Jagung", "1.1.a", "Ton", None, Decimal("3000000"),
         {2022: (Decimal("45000"), Decimal("3500000")),
          2023: (Decimal("47000"), Decimal("3700000"))}),
        ("PKB-SAWIT", "Kelapa Sawit - CPO", "1.1.e", "Ton", Decimal("0.200000"), Decimal("6000000"),
         {2022: (Decimal("500000"), Decimal("11000000")),   # 500rb ton TBS → 100rb CPO
          2023: (Decimal("540000"), Decimal("12000000"))}),
        ("TMB-BATUBARA", "Batubara", "2.2", "Ton", None, Decimal("700000"),
         {2022: (Decimal("8000000"), Decimal("1500000")),
          2023: (Decimal("8500000"), Decimal("1650000"))}),
    ]
    for kode_int, nama, kat, satuan, fk, harga2010, per_tahun in komoditas:
        kom = upsert(db, Komoditas, {"kode_internal": kode_int},
                     {"nama": nama, "kategori_kode": kat, "satuan_produksi": satuan,
                      "satuan_harga": f"Rp/{satuan}", "faktor_konversi": fk, "aktif": True})
        # Harga konstan 2010 (sekali, di tahun 2010, triwulan NULL)
        upsert(db, InputHarga,
               {"komoditas_id": kom.id, "wilayah_kode": WILAYAH, "tahun": TAHUN_DASAR, "triwulan": None},
               {"harga_berlaku": harga2010, "harga_konstan_2010": harga2010})
        for tahun, (kuantum, harga_b) in per_tahun.items():
            upsert(db, InputProduksi,
                   {"komoditas_id": kom.id, "wilayah_kode": WILAYAH, "tahun": tahun, "triwulan": None},
                   {"kuantum": kuantum, "sumber_data": "SEED uji coba", "status": "sementara"})
            upsert(db, InputHarga,
                   {"komoditas_id": kom.id, "wilayah_kode": WILAYAH, "tahun": tahun, "triwulan": None},
                   {"harga_berlaku": harga_b})
    print(f"  ✓ {len(komoditas)} komoditas + produksi + harga")


def seed_rasio(db):
    """OS & WIP & KA & ADJ untuk subkategori produksi yang dipakai.
       ADHB: per tahun uji; ADHK: tahun dasar 2010."""
    subkat_pertanian = ["1.1.a", "1.1.e"]
    rows = []
    for sk in subkat_pertanian:
        for th in TAHUN_UJI:
            rows += [
                (sk, "OS", th, Decimal("0.161600"), "ADHB"),
                (sk, "WIP", th, Decimal("0.141400"), "ADHB"),
                (sk, "KA", th, Decimal("0.252500"), "ADHB"),
                (sk, "ADJ", th, Decimal("0.101200"), "ADHB"),
            ]
        rows += [
            (sk, "OS", TAHUN_DASAR, Decimal("0.151500"), "ADHK"),
            (sk, "WIP", TAHUN_DASAR, Decimal("0.131300"), "ADHK"),
            (sk, "KA", TAHUN_DASAR, Decimal("0.202000"), "ADHK"),
            (sk, "ADJ", TAHUN_DASAR, Decimal("0.125600"), "ADHK"),
        ]
    # Pertambangan batubara 2.2 — OS/WIP kecil, KA besar
    for th in TAHUN_UJI:
        rows += [
            ("2.2", "OS", th, Decimal("0.020000"), "ADHB"),
            ("2.2", "KA", th, Decimal("0.350000"), "ADHB"),
            ("2.2", "ADJ", th, Decimal("0.000000"), "ADHB"),
        ]
    rows += [
        ("2.2", "OS", TAHUN_DASAR, Decimal("0.020000"), "ADHK"),
        ("2.2", "KA", TAHUN_DASAR, Decimal("0.350000"), "ADHK"),
        ("2.2", "ADJ", TAHUN_DASAR, Decimal("0.000000"), "ADHK"),
    ]
    # Konstruksi (6) — metode Deflasi: hanya butuh rasio KA
    for th in TAHUN_UJI:
        rows.append(("6", "KA", th, Decimal("0.450000"), "ADHB"))
    rows.append(("6", "KA", TAHUN_DASAR, Decimal("0.450000"), "ADHK"))

    for kat, jenis, th, nilai, berlaku in rows:
        upsert(db, RasioReferensi,
               {"komoditas_id": None, "kategori_kode": kat, "jenis_rasio": jenis,
                "tahun": th, "berlaku_untuk": berlaku},
               {"nilai": nilai})
    print(f"  ✓ {len(rows)} baris rasio")


def seed_kategori_deflasi(db):
    """Contoh kategori metode DEFLASI (6 Konstruksi):
       - Output ADHB diinput langsung ke pdrb_rekap.output_total_adhb
       - Indeks deflator diinput ke input_indeks_deflator (basis 2010=100)"""
    data = {2022: (Decimal("850000"), Decimal("128.50")),
            2023: (Decimal("910000"), Decimal("133.20"))}
    for tahun, (output_adhb, indeks) in data.items():
        upsert(db, InputIndeksDeflator,
               {"kategori_kode": "6", "wilayah_kode": WILAYAH, "tahun": tahun, "triwulan": None},
               {"nilai_indeks": indeks})
        # Output ADHB langsung (input user) → disimpan di pdrb_rekap
        upsert(db, PdrbRekap,
               {"kategori_kode": "6", "wilayah_kode": WILAYAH, "tahun": tahun, "triwulan": None},
               {"output_total_adhb": output_adhb, "output_primer_adhb": output_adhb})
    print("  ✓ kategori Deflasi contoh (6 Konstruksi): output ADHB + indeks deflator")


def cetak_tabel_pokok(db):
    print("\n" + "=" * 78)
    print("TABEL POKOK PDRB — Provinsi Kalimantan Utara (Juta Rupiah)")
    print("=" * 78)
    level1 = [t[0] for t in KATEGORI_DATA if t[3] == 1]  # kolom ke-4 = level
    for tahun in TAHUN_UJI:
        print(f"\n— Tahun {tahun} —")
        print(f"{'Kat':<5}{'Uraian':<46}{'NTB ADHB':>13}{'NTB ADHK':>13}")
        print("-" * 78)
        tot_b = tot_k = Decimal(0)
        for kode in sorted(level1, key=lambda x: int(x)):
            row = (db.query(PdrbRekap)
                   .filter(PdrbRekap.kategori_kode == kode, PdrbRekap.wilayah_kode == WILAYAH,
                           PdrbRekap.tahun == tahun, PdrbRekap.triwulan.is_(None)).first())
            nama = next(n for (k, n, *_r) in KATEGORI_DATA if k == kode)
            b = Decimal(str(row.ntb_adhb)) if row and row.ntb_adhb else Decimal(0)
            k = Decimal(str(row.ntb_adhk)) if row and row.ntb_adhk else Decimal(0)
            tot_b += b; tot_k += k
            print(f"{kode:<5}{nama[:44]:<46}{b:>13,.0f}{k:>13,.0f}")
        print("-" * 78)
        print(f"{'':5}{'PDRB TOTAL':<46}{tot_b:>13,.0f}{tot_k:>13,.0f}")


def main():
    print("Membuat tabel (jika belum ada)...")
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        print("Seeding master & input data...")
        seed_wilayah(db)
        seed_kategori(db)
        seed_komoditas_dan_input(db)
        seed_rasio(db)
        seed_kategori_deflasi(db)
        db.commit()

        print("\nMenjalankan cascade recalculation...")
        for tahun in TAHUN_UJI:
            res = sync_recalculate(db, trigger_type="produksi", wilayah_kode=WILAYAH,
                                   tahun=tahun, triwulan=None)
            print(f"  ✓ {tahun}: daun={len(res.subkategori_affected)}, "
                  f"parent={len(res.kategori_affected)}, peringatan={len(res.warnings)}")

        cetak_tabel_pokok(db)
        print("\nSelesai. Cek juga endpoint:  GET /api/s3/tabel-pokok?wilayah_kode=65")
    finally:
        db.close()


if __name__ == "__main__":
    main()
