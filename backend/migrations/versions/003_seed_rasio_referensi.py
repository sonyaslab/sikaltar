"""
Migration 003: Seed Rasio Referensi (SUT 2019 BPS)

Struktur rasio:
- OS  (Output Sekunder/Ikutan): berlaku per kelompok kategori
- WIP (Work In Progress)      : berlaku per kelompok kategori
- KA  (Konsumsi Antara)       : berlaku per kelompok kategori
- ADJ (Adjustment factor)     : per subkategori, berbeda-beda nilainya

Strategi penyimpanan:
  komoditas_id=NULL + kategori_kode diisi → berlaku untuk seluruh subkategori itu
  komoditas_id=NULL + kategori_kode=NULL  → tidak digunakan (terlalu luas)

Untuk OS/WIP yang berlaku untuk "semua komoditas pertanian 1.1.a s/d 1.3",
kita seed per subkategori (1.1.a, 1.1.b, ... 1.3) agar lookup tetap granular.
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def _insert_rasio(conn, kategori_kode, jenis_rasio, tahun, nilai, berlaku_untuk):
    """Helper insert rasio_referensi dengan kategori scope (komoditas_id=NULL)."""
    conn.execute(
        sa.text(
            "INSERT INTO rasio_referensi "
            "(komoditas_id, kategori_kode, jenis_rasio, tahun, nilai, berlaku_untuk) "
            "VALUES (NULL, :kategori_kode, :jenis_rasio, :tahun, :nilai, :berlaku_untuk) "
            "ON CONFLICT (komoditas_id, kategori_kode, jenis_rasio, tahun, berlaku_untuk) "
            "DO UPDATE SET nilai = EXCLUDED.nilai"
        ),
        {
            "kategori_kode": kategori_kode,
            "jenis_rasio": jenis_rasio,
            "tahun": tahun,
            "nilai": nilai,
            "berlaku_untuk": berlaku_untuk,
        },
    )


def upgrade() -> None:
    conn = op.get_bind()

    # ─────────────────────────────────────────────────────────────────────
    # Subkategori pertanian yang mendapat rasio OS & WIP
    # ─────────────────────────────────────────────────────────────────────
    PERTANIAN_SUBKAT = ["1.1.a", "1.1.b", "1.1.c", "1.1.d", "1.1.e", "1.1.f", "1.1.g", "1.2", "1.3"]

    # Tanaman yang memiliki WIP (pangan + perkebunan semusim + tahunan)
    WIP_SUBKAT = ["1.1.a", "1.1.c", "1.1.e"]

    # Hortikultura semusim & tahunan dan peternakan: WIP = 0
    WIP_NOL_SUBKAT = ["1.1.b", "1.1.d", "1.1.f", "1.1.g", "1.2", "1.3"]

    # ─────────────────────────────────────────────────────────────────────
    # RASIO OS (Output Sekunder/Ikutan) — Sumber: SUT 2019 BPS
    # Berlaku: semua komoditas pertanian 1.1.a s/d 1.3
    #   2008-2010 : 15.15% → 0.151500
    #   2011+     : 16.16% → 0.161600
    # ─────────────────────────────────────────────────────────────────────
    os_schedule = [
        *[(y, 0.151500) for y in range(2008, 2011)],   # 2008, 2009, 2010
        *[(y, 0.161600) for y in range(2011, 2031)],   # 2011 s/d 2030
    ]
    for subkat in PERTANIAN_SUBKAT:
        for tahun, nilai in os_schedule:
            for berlaku in ("ADHB", "ADHK"):
                _insert_rasio(conn, subkat, "OS", tahun, nilai, berlaku)

    # ─────────────────────────────────────────────────────────────────────
    # RASIO WIP (Work In Progress)
    # Tanaman pangan + perkebunan semusim + tahunan:
    #   2008-2010 : 13.13% → 0.131300
    #   2011+     : 14.14% → 0.141400
    # Hortikultura semusim/tahunan + peternakan + kehutanan + perikanan: WIP = 0
    # ─────────────────────────────────────────────────────────────────────
    wip_schedule = [
        *[(y, 0.131300) for y in range(2008, 2011)],
        *[(y, 0.141400) for y in range(2011, 2031)],
    ]
    for subkat in WIP_SUBKAT:
        for tahun, nilai in wip_schedule:
            for berlaku in ("ADHB", "ADHK"):
                _insert_rasio(conn, subkat, "WIP", tahun, nilai, berlaku)

    for subkat in WIP_NOL_SUBKAT:
        for tahun in range(2008, 2031):
            for berlaku in ("ADHB", "ADHK"):
                _insert_rasio(conn, subkat, "WIP", tahun, 0.000000, berlaku)

    # ─────────────────────────────────────────────────────────────────────
    # RASIO KA (Konsumsi Antara) — berlaku untuk semua subkategori pertanian
    #   2008-2009 : 10.00% → 0.100000
    #   2010      : 20.20% → 0.202000
    #   2011+     : 25.25% → 0.252500
    # ─────────────────────────────────────────────────────────────────────
    ka_schedule_pertanian = [
        (2008, 0.100000), (2009, 0.100000),
        (2010, 0.202000),
        *[(y, 0.252500) for y in range(2011, 2031)],
    ]
    for subkat in PERTANIAN_SUBKAT:
        for tahun, nilai in ka_schedule_pertanian:
            for berlaku in ("ADHB", "ADHK"):
                _insert_rasio(conn, subkat, "KA", tahun, nilai, berlaku)

    # ─────────────────────────────────────────────────────────────────────
    # RASIO ADJ (Adjustment Factor) — Sumber: Excel LK BPS
    # Disimpan terpisah untuk ADHB dan ADHK (bisa berbeda)
    # ─────────────────────────────────────────────────────────────────────

    # Kelompok 1: Subkategori pertanian umum (1.1.a s/d 1.1.g)
    #   2008-2010 : 12.56% → 0.125600
    #   2011+     : 10.12% → 0.101200
    ADJ_PERTANIAN_UMUM = ["1.1.a", "1.1.b", "1.1.c", "1.1.d", "1.1.e", "1.1.f", "1.1.g"]
    adj_pertanian_umum = [
        *[(y, 0.125600) for y in range(2008, 2011)],
        *[(y, 0.101200) for y in range(2011, 2031)],
    ]
    for subkat in ADJ_PERTANIAN_UMUM:
        for tahun, nilai in adj_pertanian_umum:
            for berlaku in ("ADHB", "ADHK"):
                _insert_rasio(conn, subkat, "ADJ", tahun, nilai, berlaku)

    # Kelompok 2: Kehutanan (1.2) — ADJ berbeda per tahun
    adj_kehutanan = [
        (2008, 0.100000), (2009, 0.100000),
        (2010, 0.102100),
        (2011, 0.103700),
        (2012, 0.104500),
        (2013, 0.105800),
        (2014, 0.112400),
        *[(y, 0.112400) for y in range(2015, 2031)],  # asumsi konstan setelah 2014
    ]
    for tahun, nilai in adj_kehutanan:
        for berlaku in ("ADHB", "ADHK"):
            _insert_rasio(conn, "1.2", "ADJ", tahun, nilai, berlaku)

    # Kelompok 3: Perikanan (1.3)
    #   2008-2010 : 12.65% → 0.126500
    #   2011+     :  9.82% → 0.098200
    adj_perikanan = [
        *[(y, 0.126500) for y in range(2008, 2011)],
        *[(y, 0.098200) for y in range(2011, 2031)],
    ]
    for tahun, nilai in adj_perikanan:
        for berlaku in ("ADHB", "ADHK"):
            _insert_rasio(conn, "1.3", "ADJ", tahun, nilai, berlaku)

    # ─────────────────────────────────────────────────────────────────────
    # RASIO KA — Kategori Pertambangan (2.x)
    # Menggunakan rasio serupa; diisi dengan nilai umum
    # Sesuaikan bila ada data SUT spesifik untuk migas/batubara
    # ─────────────────────────────────────────────────────────────────────
    TAMBANG_SUBKAT = ["2.1", "2.2", "2.3", "2.4"]
    ka_tambang = [
        *[(y, 0.100000) for y in range(2008, 2010)],
        (2010, 0.202000),
        *[(y, 0.252500) for y in range(2011, 2031)],
    ]
    for subkat in TAMBANG_SUBKAT:
        for tahun, nilai in ka_tambang:
            for berlaku in ("ADHB", "ADHK"):
                _insert_rasio(conn, subkat, "KA", tahun, nilai, berlaku)

    # ADJ Pertambangan umum (2.1, 2.3): 12.56% → 10.12%
    for subkat in ["2.1", "2.3"]:
        for tahun, nilai in adj_pertanian_umum:
            for berlaku in ("ADHB", "ADHK"):
                _insert_rasio(conn, subkat, "ADJ", tahun, nilai, berlaku)

    # ADJ Batubara (2.2) dan Penggalian Lainnya (2.4):
    #   2008-2010 : 11.67% → 0.116700
    #   2011+     : 10.98% → 0.109800
    adj_batubara = [
        *[(y, 0.116700) for y in range(2008, 2011)],
        *[(y, 0.109800) for y in range(2011, 2031)],
    ]
    for subkat in ["2.2", "2.4"]:
        for tahun, nilai in adj_batubara:
            for berlaku in ("ADHB", "ADHK"):
                _insert_rasio(conn, subkat, "ADJ", tahun, nilai, berlaku)

    # ─────────────────────────────────────────────────────────────────────
    # RASIO ADJ — Industri Pengolahan (3.x)
    # Sebagian besar: 12.56% → 10.12% (seperti pertanian umum)
    # 3.8 (Kimia/Farmasi): 12.65% → 9.82% (seperti perikanan)
    # 3.9 (Karet/Plastik): 12.65% → 9.82%
    # ─────────────────────────────────────────────────────────────────────
    INDUSTRI_UMUM = ["3.1","3.2","3.3","3.4","3.5","3.6","3.7","3.10","3.11","3.12","3.13","3.14","3.15","3.16"]
    for subkat in INDUSTRI_UMUM:
        for tahun, nilai in adj_pertanian_umum:
            for berlaku in ("ADHB", "ADHK"):
                _insert_rasio(conn, subkat, "ADJ", tahun, nilai, berlaku)

    adj_industri_khusus = [
        *[(y, 0.126500) for y in range(2008, 2011)],
        *[(y, 0.098200) for y in range(2011, 2031)],
    ]
    for subkat in ["3.8", "3.9"]:
        for tahun, nilai in adj_industri_khusus:
            for berlaku in ("ADHB", "ADHK"):
                _insert_rasio(conn, subkat, "ADJ", tahun, nilai, berlaku)

    # ─────────────────────────────────────────────────────────────────────
    # RASIO ADJ — Ketenagalistrikan (4.1)
    #   2008-2010 : 12.65% → 0.126500
    #   2011+     :  9.82% → 0.098200
    # ─────────────────────────────────────────────────────────────────────
    for tahun, nilai in adj_industri_khusus:
        for berlaku in ("ADHB", "ADHK"):
            _insert_rasio(conn, "4.1", "ADJ", tahun, nilai, berlaku)

    # ─────────────────────────────────────────────────────────────────────
    # INDEKS DEFLATOR: Nilai 100 untuk tahun 2010 (tahun dasar)
    # Diisi untuk semua kategori dengan metode Deflasi
    # ─────────────────────────────────────────────────────────────────────
    KATEGORI_DEFLASI = ["6", "7.2", "8.1","8.2","8.3","8.4","8.5","8.6",
                        "9.1","9.2", "10", "11","11.1","11.2","11.3","11.4",
                        "12", "13", "14", "15", "16", "17"]
    WILAYAH_KODES = ["65", "6501", "6502", "6503", "6504", "6571"]

    for kategori in KATEGORI_DEFLASI:
        for wilayah in WILAYAH_KODES:
            conn.execute(
                sa.text(
                    "INSERT INTO input_indeks_deflator "
                    "(kategori_kode, wilayah_kode, tahun, triwulan, nilai_indeks) "
                    "VALUES (:kategori_kode, :wilayah_kode, 2010, NULL, 100.0000) "
                    "ON CONFLICT (kategori_kode, wilayah_kode, tahun, triwulan) DO NOTHING"
                ),
                {"kategori_kode": kategori, "wilayah_kode": wilayah},
            )


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(sa.text("DELETE FROM input_indeks_deflator WHERE tahun = 2010 AND triwulan IS NULL"))
    conn.execute(sa.text("DELETE FROM rasio_referensi"))
