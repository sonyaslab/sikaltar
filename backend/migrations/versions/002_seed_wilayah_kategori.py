"""
Migration 002: Seed Master Data
- 6 Wilayah Kalimantan Utara
- 17 Kategori PDRB + Subkategori lengkap (SNA 2008)
- Komoditas contoh untuk Kategori A (Pertanian, Kehutanan, Perikanan)
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


# ─────────────────────────────────────────────────────────────────────────────
# WILAYAH
# ─────────────────────────────────────────────────────────────────────────────
WILAYAH_DATA = [
    # (kode, nama, level, parent_kode)
    ("65",   "Provinsi Kalimantan Utara",  "provinsi",  None),
    ("6501", "Kabupaten Malinau",          "kabupaten", "65"),
    ("6502", "Kabupaten Bulungan",         "kabupaten", "65"),
    ("6503", "Kabupaten Tana Tidung",      "kabupaten", "65"),
    ("6504", "Kabupaten Nunukan",          "kabupaten", "65"),
    ("6571", "Kota Tarakan",               "kota",      "65"),
]


# ─────────────────────────────────────────────────────────────────────────────
# KATEGORI PDRB (SNA 2008, 17 Kategori)
# Format: (kode, nama, parent_kode, level, metode_adhb, metode_adhk, urutan)
# ─────────────────────────────────────────────────────────────────────────────
KATEGORI_DATA = [
    # ═══════════════════════════════════════════════════════════════════════
    # A — Pertanian, Kehutanan dan Perikanan
    # ═══════════════════════════════════════════════════════════════════════
    ("1",     "Pertanian, Kehutanan dan Perikanan",                              None,  1, "Produksi",   "Revaluasi",    10),
    ("1.1",   "Pertanian, Peternakan, Perburuan dan Jasa Pertanian",             "1",   2, "Produksi",   "Revaluasi",    11),
    ("1.1.a", "Tanaman Pangan",                                                  "1.1", 3, "Produksi",   "Revaluasi",    12),
    ("1.1.b", "Tanaman Hortikultura Semusim",                                    "1.1", 3, "Produksi",   "Revaluasi",    13),
    ("1.1.c", "Perkebunan Semusim",                                              "1.1", 3, "Produksi",   "Revaluasi",    14),
    ("1.1.d", "Tanaman Hortikultura Tahunan dan Lainnya",                        "1.1", 3, "Produksi",   "Revaluasi",    15),
    ("1.1.e", "Perkebunan Tahunan",                                              "1.1", 3, "Produksi",   "Revaluasi",    16),
    ("1.1.f", "Peternakan",                                                      "1.1", 3, "Produksi",   "Revaluasi",    17),
    ("1.1.g", "Jasa Pertanian dan Perburuan",                                    "1.1", 3, "Produksi",   "Revaluasi",    18),
    ("1.2",   "Kehutanan dan Penebangan Kayu",                                   "1",   2, "Produksi",   "Revaluasi",    20),
    ("1.3",   "Perikanan",                                                       "1",   2, "Produksi",   "Revaluasi",    30),

    # ═══════════════════════════════════════════════════════════════════════
    # B — Pertambangan dan Penggalian
    # ═══════════════════════════════════════════════════════════════════════
    ("2",     "Pertambangan dan Penggalian",                                     None,  1, "Produksi",   "Revaluasi",    40),
    ("2.1",   "Pertambangan Minyak, Gas dan Panas Bumi",                         "2",   2, "Produksi",   "Revaluasi",    41),
    ("2.2",   "Pertambangan Batubara dan Lignit",                                 "2",   2, "Produksi",   "Revaluasi",    42),
    ("2.3",   "Pertambangan Bijih Logam",                                         "2",   2, "Produksi",   "Revaluasi",    43),
    ("2.4",   "Pertambangan dan Penggalian Lainnya",                              "2",   2, "Produksi",   "Revaluasi",    44),

    # ═══════════════════════════════════════════════════════════════════════
    # C — Industri Pengolahan
    # ═══════════════════════════════════════════════════════════════════════
    ("3",     "Industri Pengolahan",                                             None,  1, "Produksi",   "DoubleDflasi", 50),
    ("3.1",   "Industri Batubara dan Pengilangan Migas",                          "3",   2, "Produksi",   "DoubleDflasi", 51),
    ("3.2",   "Industri Makanan dan Minuman",                                     "3",   2, "Produksi",   "DoubleDflasi", 52),
    ("3.3",   "Industri Pengolahan Tembakau",                                     "3",   2, "Produksi",   "DoubleDflasi", 53),
    ("3.4",   "Industri Tekstil dan Pakaian Jadi",                                "3",   2, "Produksi",   "DoubleDflasi", 54),
    ("3.5",   "Industri Kulit, Barang dari Kulit dan Alas Kaki",                  "3",   2, "Produksi",   "DoubleDflasi", 55),
    ("3.6",   "Industri Kayu, Barang dari Kayu dan Gabus; Anyaman",               "3",   2, "Produksi",   "DoubleDflasi", 56),
    ("3.7",   "Industri Kertas dan Barang dari Kertas; Percetakan",               "3",   2, "Produksi",   "DoubleDflasi", 57),
    ("3.8",   "Industri Kimia, Farmasi dan Obat Tradisional",                     "3",   2, "Produksi",   "DoubleDflasi", 58),
    ("3.9",   "Industri Karet, Barang dari Karet dan Plastik",                    "3",   2, "Produksi",   "DoubleDflasi", 59),
    ("3.10",  "Industri Barang Galian Bukan Logam",                               "3",   2, "Produksi",   "DoubleDflasi", 60),
    ("3.11",  "Industri Logam Dasar",                                             "3",   2, "Produksi",   "DoubleDflasi", 61),
    ("3.12",  "Industri Barang dari Logam; Komputer, Elektronik, Optik; Listrik", "3",   2, "Produksi",   "DoubleDflasi", 62),
    ("3.13",  "Industri Mesin dan Perlengkapan YTDL",                             "3",   2, "Produksi",   "DoubleDflasi", 63),
    ("3.14",  "Industri Alat Angkutan",                                           "3",   2, "Produksi",   "DoubleDflasi", 64),
    ("3.15",  "Industri Furnitur",                                                "3",   2, "Produksi",   "DoubleDflasi", 65),
    ("3.16",  "Industri Pengolahan Lainnya; Jasa Reparasi dan Pemasangan Mesin",  "3",   2, "Produksi",   "DoubleDflasi", 66),

    # ═══════════════════════════════════════════════════════════════════════
    # D — Pengadaan Listrik dan Gas
    # ═══════════════════════════════════════════════════════════════════════
    ("4",     "Pengadaan Listrik dan Gas",                                        None,  1, "Produksi",   "Revaluasi",    70),
    ("4.1",   "Ketenagalistrikan",                                                "4",   2, "Produksi",   "Revaluasi",    71),
    ("4.2",   "Pengadaan Gas dan Produksi Es",                                    "4",   2, "Produksi",   "Revaluasi",    72),

    # ═══════════════════════════════════════════════════════════════════════
    # E — Pengadaan Air, Pengelolaan Sampah, Limbah dan Daur Ulang
    # ═══════════════════════════════════════════════════════════════════════
    ("5",     "Pengadaan Air, Pengelolaan Sampah, Limbah dan Daur Ulang",         None,  1, "Produksi",   "Revaluasi",    80),

    # ═══════════════════════════════════════════════════════════════════════
    # F — Konstruksi
    # ═══════════════════════════════════════════════════════════════════════
    ("6",     "Konstruksi",                                                       None,  1, "CommodityFlow", "Deflasi",   90),

    # ═══════════════════════════════════════════════════════════════════════
    # G — Perdagangan Besar dan Eceran; Reparasi Mobil dan Sepeda Motor
    # ═══════════════════════════════════════════════════════════════════════
    ("7",     "Perdagangan Besar dan Eceran; Reparasi Mobil dan Sepeda Motor",    None,  1, "Produksi",   "Revaluasi",   100),
    ("7.1",   "Perdagangan Mobil, Sepeda Motor dan Reparasinya",                  "7",   2, "Produksi",   "Revaluasi",   101),
    ("7.2",   "Perdagangan Besar dan Eceran Bukan Mobil dan Sepeda Motor",        "7",   2, "Produksi",   "Deflasi",     102),

    # ═══════════════════════════════════════════════════════════════════════
    # H — Transportasi dan Pergudangan
    # ═══════════════════════════════════════════════════════════════════════
    ("8",     "Transportasi dan Pergudangan",                                     None,  1, "Produksi",   "Deflasi",     110),
    ("8.1",   "Angkutan Rel",                                                     "8",   2, "Produksi",   "Deflasi",     111),
    ("8.2",   "Angkutan Darat",                                                   "8",   2, "Produksi",   "Deflasi",     112),
    ("8.3",   "Angkutan Laut",                                                    "8",   2, "Produksi",   "Deflasi",     113),
    ("8.4",   "Angkutan Sungai, Danau dan Penyeberangan",                         "8",   2, "Produksi",   "Deflasi",     114),
    ("8.5",   "Angkutan Udara",                                                   "8",   2, "Produksi",   "Deflasi",     115),
    ("8.6",   "Pergudangan dan Jasa Penunjang Angkutan; Pos dan Kurir",           "8",   2, "Produksi",   "Deflasi",     116),

    # ═══════════════════════════════════════════════════════════════════════
    # I — Penyediaan Akomodasi dan Makan Minum
    # ═══════════════════════════════════════════════════════════════════════
    ("9",     "Penyediaan Akomodasi dan Makan Minum",                             None,  1, "Produksi",   "Deflasi",     120),
    ("9.1",   "Penyediaan Akomodasi",                                             "9",   2, "Produksi",   "Deflasi",     121),
    ("9.2",   "Penyediaan Makan Minum",                                           "9",   2, "Produksi",   "Deflasi",     122),

    # ═══════════════════════════════════════════════════════════════════════
    # J — Informasi dan Komunikasi
    # ═══════════════════════════════════════════════════════════════════════
    ("10",    "Informasi dan Komunikasi",                                         None,  1, "Produksi",   "Deflasi",     130),

    # ═══════════════════════════════════════════════════════════════════════
    # K — Jasa Keuangan dan Asuransi
    # ═══════════════════════════════════════════════════════════════════════
    ("11",    "Jasa Keuangan dan Asuransi",                                       None,  1, "Langsung",   "Deflasi",     140),
    ("11.1",  "Jasa Perantara Keuangan",                                          "11",  2, "Langsung",   "Deflasi",     141),
    ("11.2",  "Asuransi dan Dana Pensiun",                                        "11",  2, "Langsung",   "Deflasi",     142),
    ("11.3",  "Jasa Keuangan Lainnya",                                            "11",  2, "Langsung",   "Deflasi",     143),
    ("11.4",  "Jasa Penunjang Keuangan",                                          "11",  2, "Langsung",   "Deflasi",     144),

    # ═══════════════════════════════════════════════════════════════════════
    # L — Real Estate
    # ═══════════════════════════════════════════════════════════════════════
    ("12",    "Real Estate",                                                      None,  1, "Produksi",   "Deflasi",     150),

    # ═══════════════════════════════════════════════════════════════════════
    # M,N — Jasa Perusahaan
    # ═══════════════════════════════════════════════════════════════════════
    ("13",    "Jasa Perusahaan",                                                  None,  1, "Produksi",   "Deflasi",     160),

    # ═══════════════════════════════════════════════════════════════════════
    # O — Administrasi Pemerintahan, Pertahanan dan Jaminan Sosial Wajib
    # ═══════════════════════════════════════════════════════════════════════
    ("14",    "Administrasi Pemerintahan, Pertahanan dan Jaminan Sosial Wajib",   None,  1, "Langsung",   "Deflasi",     170),

    # ═══════════════════════════════════════════════════════════════════════
    # P — Jasa Pendidikan
    # ═══════════════════════════════════════════════════════════════════════
    ("15",    "Jasa Pendidikan",                                                  None,  1, "Produksi",   "Deflasi",     180),

    # ═══════════════════════════════════════════════════════════════════════
    # Q — Jasa Kesehatan dan Kegiatan Sosial
    # ═══════════════════════════════════════════════════════════════════════
    ("16",    "Jasa Kesehatan dan Kegiatan Sosial",                               None,  1, "Produksi",   "Deflasi",     190),

    # ═══════════════════════════════════════════════════════════════════════
    # R,S,T,U — Jasa Lainnya
    # ═══════════════════════════════════════════════════════════════════════
    ("17",    "Jasa Lainnya",                                                     None,  1, "Produksi",   "Deflasi",     200),
]


# ─────────────────────────────────────────────────────────────────────────────
# KOMODITAS CONTOH — Kategori A (Pertanian, Kehutanan, Perikanan)
# Tambahkan komoditas lain via UI atau import Excel
# Format: (kode_internal, nama, kategori_kode, satuan_produksi, satuan_harga,
#           faktor_konversi, wujud_produksi)
# ─────────────────────────────────────────────────────────────────────────────
KOMODITAS_DATA = [
    # ── 1.1.a Tanaman Pangan ──────────────────────────────────────────────
    ("TPN-PADI-SAWAH",    "Padi Sawah",         "1.1.a", "Ton", "Rp/Ton", None,   "Gabah Kering Giling"),
    ("TPN-PADI-LADANG",   "Padi Ladang",        "1.1.a", "Ton", "Rp/Ton", None,   "Gabah Kering Giling"),
    ("TPN-JAGUNG",        "Jagung",             "1.1.a", "Ton", "Rp/Ton", None,   "Pipilan Kering"),
    ("TPN-UBI-KAYU",      "Ubi Kayu",           "1.1.a", "Ton", "Rp/Ton", None,   "Umbi Segar"),
    ("TPN-UBI-JALAR",     "Ubi Jalar",          "1.1.a", "Ton", "Rp/Ton", None,   "Umbi Segar"),
    ("TPN-KACANG-TANAH",  "Kacang Tanah",       "1.1.a", "Ton", "Rp/Ton", None,   "Biji Kering"),
    ("TPN-KEDELAI",       "Kedelai",            "1.1.a", "Ton", "Rp/Ton", None,   "Biji Kering"),
    ("TPN-KACANG-HIJAU",  "Kacang Hijau",       "1.1.a", "Ton", "Rp/Ton", None,   "Biji Kering"),
    ("TPN-SORGUM",        "Sorgum",             "1.1.a", "Ton", "Rp/Ton", None,   "Biji Kering"),

    # ── 1.1.b Tanaman Hortikultura Semusim ────────────────────────────────
    ("HRT-SEM-CABAI-BESAR",  "Cabai Besar",     "1.1.b", "Ton", "Rp/Ton", None,   "Buah Segar"),
    ("HRT-SEM-CABAI-RAWIT",  "Cabai Rawit",     "1.1.b", "Ton", "Rp/Ton", None,   "Buah Segar"),
    ("HRT-SEM-BAWANG-MERAH", "Bawang Merah",    "1.1.b", "Ton", "Rp/Ton", None,   "Umbi Kering"),
    ("HRT-SEM-TOMAT",        "Tomat",           "1.1.b", "Ton", "Rp/Ton", None,   "Buah Segar"),
    ("HRT-SEM-MENTIMUN",     "Mentimun",        "1.1.b", "Ton", "Rp/Ton", None,   "Buah Segar"),
    ("HRT-SEM-KANGKUNG",     "Kangkung",        "1.1.b", "Ton", "Rp/Ton", None,   "Daun Segar"),
    ("HRT-SEM-BAYAM",        "Bayam",           "1.1.b", "Ton", "Rp/Ton", None,   "Daun Segar"),
    ("HRT-SEM-SEMANGKA",     "Semangka",        "1.1.b", "Ton", "Rp/Ton", None,   "Buah Segar"),

    # ── 1.1.c Perkebunan Semusim ───────────────────────────────────────────
    ("PKB-SEM-TEBU",         "Tebu",            "1.1.c", "Ton", "Rp/Ton", None,   "Batang Segar"),
    ("PKB-SEM-TEMBAKAU",     "Tembakau",        "1.1.c", "Ton", "Rp/Ton", None,   "Daun Kering"),

    # ── 1.1.d Tanaman Hortikultura Tahunan dan Lainnya ────────────────────
    ("HRT-TAH-PISANG",       "Pisang",          "1.1.d", "Ton", "Rp/Ton", None,   "Buah Segar"),
    ("HRT-TAH-NANAS",        "Nanas",           "1.1.d", "Ton", "Rp/Ton", None,   "Buah Segar"),
    ("HRT-TAH-MANGGA",       "Mangga",          "1.1.d", "Ton", "Rp/Ton", None,   "Buah Segar"),
    ("HRT-TAH-JERUK",        "Jeruk",           "1.1.d", "Ton", "Rp/Ton", None,   "Buah Segar"),
    ("HRT-TAH-PEPAYA",       "Pepaya",          "1.1.d", "Ton", "Rp/Ton", None,   "Buah Segar"),
    ("HRT-TAH-RAMBUTAN",     "Rambutan",        "1.1.d", "Ton", "Rp/Ton", None,   "Buah Segar"),
    ("HRT-TAH-DURIAN",       "Durian",          "1.1.d", "Ton", "Rp/Ton", None,   "Buah Segar"),

    # ── 1.1.e Perkebunan Tahunan ───────────────────────────────────────────
    # Sawit: produksi dalam TBS, lalu konversi ke CPO (faktor 0.20) dan PKO (faktor 0.05)
    ("PKB-TAH-SAWIT-CPO",    "Kelapa Sawit - CPO",         "1.1.e", "Ton", "Rp/Ton", 0.200000, "Tandan Buah Segar (TBS)"),
    ("PKB-TAH-SAWIT-PKO",    "Kelapa Sawit - PKO",         "1.1.e", "Ton", "Rp/Ton", 0.050000, "Tandan Buah Segar (TBS)"),
    ("PKB-TAH-KARET",        "Karet",                      "1.1.e", "Ton", "Rp/Ton", None,      "Karet Kering"),
    ("PKB-TAH-KELAPA",       "Kelapa",                     "1.1.e", "Ton", "Rp/Ton", None,      "Butir Kering"),
    ("PKB-TAH-KAKAO",        "Kakao",                      "1.1.e", "Ton", "Rp/Ton", None,      "Biji Kering"),
    ("PKB-TAH-LADA",         "Lada",                       "1.1.e", "Ton", "Rp/Ton", None,      "Biji Kering"),
    ("PKB-TAH-KOPI-ROB",     "Kopi Robusta",               "1.1.e", "Ton", "Rp/Ton", None,      "Biji Kering"),
    ("PKB-TAH-KOPI-ARA",     "Kopi Arabika",               "1.1.e", "Ton", "Rp/Ton", None,      "Biji Kering"),
    ("PKB-TAH-AREN",         "Aren",                       "1.1.e", "Ton", "Rp/Ton", None,      "Nira/Gula Aren"),
    ("PKB-TAH-KEMIRI",       "Kemiri",                     "1.1.e", "Ton", "Rp/Ton", None,      "Biji Kering"),
    ("PKB-TAH-PINANG",       "Pinang",                     "1.1.e", "Ton", "Rp/Ton", None,      "Biji Kering"),

    # ── 1.1.f Peternakan ──────────────────────────────────────────────────
    ("TRN-SAPI-POTONG",      "Sapi Potong",               "1.1.f", "Ekor", "Rp/Ekor", None,   "Ternak Hidup"),
    ("TRN-KERBAU",           "Kerbau",                    "1.1.f", "Ekor", "Rp/Ekor", None,   "Ternak Hidup"),
    ("TRN-KAMBING",          "Kambing",                   "1.1.f", "Ekor", "Rp/Ekor", None,   "Ternak Hidup"),
    ("TRN-DOMBA",            "Domba",                     "1.1.f", "Ekor", "Rp/Ekor", None,   "Ternak Hidup"),
    ("TRN-BABI",             "Babi",                      "1.1.f", "Ekor", "Rp/Ekor", None,   "Ternak Hidup"),
    ("TRN-AYAM-KAMPUNG",     "Ayam Kampung",              "1.1.f", "000 Ekor", "Rp/Ekor", None, "Ternak Hidup"),
    ("TRN-AYAM-PEDAGING",    "Ayam Pedaging (Broiler)",   "1.1.f", "000 Ekor", "Rp/Ekor", None, "Ternak Hidup"),
    ("TRN-AYAM-PETELUR",     "Ayam Petelur",              "1.1.f", "000 Ekor", "Rp/Ekor", None, "Ternak Hidup"),
    ("TRN-ITIK",             "Itik/Bebek",                "1.1.f", "000 Ekor", "Rp/Ekor", None, "Ternak Hidup"),
    ("TRN-TELUR-AYAM",       "Telur Ayam",                "1.1.f", "Ton", "Rp/Ton",   None,   "Butir Segar"),
    ("TRN-SUSU-SAPI",        "Susu Sapi",                 "1.1.f", "Ton", "Rp/Ton",   None,   "Liter Segar"),

    # ── 1.2 Kehutanan dan Penebangan Kayu ─────────────────────────────────
    ("KHT-KAYU-BULAT",       "Kayu Bulat (Log)",          "1.2",   "M3",  "Rp/M3",  None,   "Kayu Gelondongan"),
    ("KHT-KAYU-OLAHAN",      "Kayu Olahan (Gergajian)",   "1.2",   "M3",  "Rp/M3",  None,   "Kayu Gergajian"),
    ("KHT-ROTAN",            "Rotan",                     "1.2",   "Ton", "Rp/Ton", None,   "Batang Basah"),
    ("KHT-DAMAR",            "Damar",                     "1.2",   "Ton", "Rp/Ton", None,   "Getah Kering"),
    ("KHT-MADU",             "Madu Hutan",                "1.2",   "Ton", "Rp/Ton", None,   "Liter"),
    ("KHT-GAHARU",           "Gaharu",                    "1.2",   "Kg",  "Rp/Kg",  None,   "Kayu/Serpihan"),

    # ── 1.3 Perikanan ─────────────────────────────────────────────────────
    ("PRK-TANGKAP-LAUT",     "Perikanan Tangkap Laut",    "1.3",   "Ton", "Rp/Ton", None,   "Ikan Segar"),
    ("PRK-TANGKAP-SUNGAI",   "Perikanan Tangkap Sungai/Danau", "1.3", "Ton", "Rp/Ton", None, "Ikan Segar"),
    ("PRK-BUDIDAYA-TAMBAK",  "Budidaya Tambak (Udang)",   "1.3",   "Ton", "Rp/Ton", None,   "Udang Segar"),
    ("PRK-BUDIDAYA-KOLAM",   "Budidaya Kolam (Ikan Air Tawar)", "1.3", "Ton", "Rp/Ton", None, "Ikan Segar"),
    ("PRK-BUDIDAYA-KJA",     "Budidaya Keramba Jaring Apung", "1.3", "Ton", "Rp/Ton", None, "Ikan Segar"),
    ("PRK-RUMPUT-LAUT",      "Rumput Laut",               "1.3",   "Ton", "Rp/Ton", None,   "Rumput Laut Kering"),
]


def upgrade() -> None:
    conn = op.get_bind()

    # ── Seed Wilayah ──────────────────────────────────────────────────────
    for kode, nama, level, parent_kode in WILAYAH_DATA:
        conn.execute(
            sa.text(
                "INSERT INTO wilayah (kode, nama, level, parent_kode) "
                "VALUES (:kode, :nama, :level, :parent_kode) "
                "ON CONFLICT (kode) DO NOTHING"
            ),
            {"kode": kode, "nama": nama, "level": level, "parent_kode": parent_kode},
        )

    # ── Seed Kategori PDRB ────────────────────────────────────────────────
    for row in KATEGORI_DATA:
        kode, nama, parent_kode, level, metode_adhb, metode_adhk, urutan = row
        conn.execute(
            sa.text(
                "INSERT INTO kategori_pdrb "
                "(kode, nama, parent_kode, level, metode_adhb, metode_adhk, urutan) "
                "VALUES (:kode, :nama, :parent_kode, :level, :metode_adhb, :metode_adhk, :urutan) "
                "ON CONFLICT (kode) DO NOTHING"
            ),
            {
                "kode": kode, "nama": nama, "parent_kode": parent_kode,
                "level": level, "metode_adhb": metode_adhb,
                "metode_adhk": metode_adhk, "urutan": urutan,
            },
        )

    # ── Seed Komoditas ────────────────────────────────────────────────────
    for row in KOMODITAS_DATA:
        kode_internal, nama, kategori_kode, satuan_prod, satuan_harga, faktor_konversi, wujud = row
        conn.execute(
            sa.text(
                "INSERT INTO komoditas "
                "(kode_internal, nama, kategori_kode, satuan_produksi, satuan_harga, "
                "faktor_konversi, wujud_produksi, aktif) "
                "VALUES (:kode_internal, :nama, :kategori_kode, :satuan_produksi, :satuan_harga, "
                ":faktor_konversi, :wujud_produksi, true) "
                "ON CONFLICT (kode_internal) DO NOTHING"
            ),
            {
                "kode_internal": kode_internal, "nama": nama, "kategori_kode": kategori_kode,
                "satuan_produksi": satuan_prod, "satuan_harga": satuan_harga,
                "faktor_konversi": faktor_konversi, "wujud_produksi": wujud,
            },
        )


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(sa.text("DELETE FROM komoditas"))
    conn.execute(sa.text("DELETE FROM kategori_pdrb"))
    conn.execute(sa.text("DELETE FROM wilayah"))
