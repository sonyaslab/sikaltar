# SIKALTARA — Sistem Lembar Kerja PDRB Kalimantan Utara

**Badan Pusat Statistik Provinsi Kalimantan Utara**
Standar: SNA 2008 | Tahun Dasar: 2010=100 | Metode: BPS Indonesia

---

## Struktur Proyek

```
SIKALTARA/
├── setup.bat                    ← Jalankan ini pertama kali di Windows
├── docker-compose.yml           ← PostgreSQL + Redis (opsional)
└── backend/
    ├── pyproject.toml           ← Dependencies Python
    ├── alembic.ini              ← Konfigurasi migrasi
    ├── .env.example             ← Template konfigurasi (salin ke .env)
    ├── app/
    │   ├── main.py              ← FastAPI entry point
    │   ├── database.py          ← Koneksi PostgreSQL
    │   ├── models/              ← 10 tabel SQLAlchemy
    │   │   ├── wilayah.py
    │   │   ├── kategori_pdrb.py
    │   │   ├── komoditas.py
    │   │   ├── rasio.py
    │   │   ├── input_data.py
    │   │   └── hasil.py
    │   └── services/            ← Logika kalkulasi BPS
    │       ├── rasio_service.py
    │       ├── kalkulasi_service.py
    │       ├── agregasi_service.py
    │       └── cascade_service.py
    ├── migrations/
    │   └── versions/
    │       ├── 001_create_tables.py
    │       ├── 002_seed_wilayah_kategori.py   ← 6 wilayah + 17 kategori + komoditas
    │       └── 003_seed_rasio_referensi.py    ← Rasio SUT 2019 BPS
    └── tests/
        ├── test_rasio_service.py
        └── test_kalkulasi_service.py
```

---

## Cara Instalasi

### Opsi A: Dengan Docker (Direkomendasikan)

```powershell
# 1. Start PostgreSQL + Redis
docker-compose up -d

# 2. Setup dan migrasi
setup.bat
```

### Opsi B: PostgreSQL Lokal (Tanpa Docker)

1. Install [PostgreSQL 15/16](https://www.postgresql.org/download/windows/)
2. Buat database:
   ```sql
   CREATE DATABASE sikaltara_db;
   CREATE USER sikaltara WITH PASSWORD 'sikaltara2024';
   GRANT ALL PRIVILEGES ON DATABASE sikaltara_db TO sikaltara;
   ```
3. Jalankan `setup.bat`

---

## Konfigurasi

Salin `backend/.env.example` ke `backend/.env` dan sesuaikan:

```env
DATABASE_URL=postgresql://sikaltara:sikaltara2024@localhost:5432/sikaltara_db
REDIS_URL=redis://localhost:6379/0
APP_ENV=development
```

---

## Migrasi Database

```powershell
cd backend
.venv\Scripts\activate

# Jalankan semua migrasi (create tables + seed data)
alembic upgrade head

# Cek status migrasi
alembic current

# Rollback 1 langkah
alembic downgrade -1
```

---

## Menjalankan Server

```powershell
cd backend
.venv\Scripts\activate
uvicorn app.main:app --reload --port 8000
```

Buka browser: `http://localhost:8000/docs` untuk dokumentasi API interaktif.

---

## Menjalankan Tests

```powershell
cd backend
.venv\Scripts\activate
pytest tests/ -v
```

Tests menggunakan **SQLite in-memory** — tidak perlu PostgreSQL berjalan.

---

## Arsitektur Kalkulasi

```
Input Produksi + Harga Berlaku
         │
         ▼
  hitung_output_komoditas()          ← Level komoditas
  • output_utama_adhb  = Q × Pb / 1Jt
  • output_ikutan_adhb = utama × rasio_OS(ADHB, tahun)
  • wip_adhb           = utama × rasio_WIP(ADHB, tahun)
  • output_utama_adhk  = Q × P2010 / 1Jt
  • output_ikutan_adhk = utama × rasio_OS(ADHK, 2010)   ← TAHUN DASAR
  • wip_adhk           = utama × rasio_WIP(ADHK, 2010)  ← TAHUN DASAR
         │
         ▼ SUM per subkategori
  hitung_subkategori()                ← Level subkategori
  • output_sekunder_b  = primer × rasio_OS(subkat, ADHB, tahun)
  • adj_b              = primer × rasio_ADJ(subkat, ADHB, tahun)
  • output_total_b     = primer + sekunder + adj
  • ka_b               = total × rasio_KA(subkat, ADHB, tahun)
  • ntb_b              = total - ka                       ← PDRB ADHB
         │
         ▼ Roll-up ke kategori parent
  pdrb_rekap (SUM subkategori)
         │
         ▼
  hitung_indikator_turunan()
  • distribusi_pct      = ntb_kategori / ntb_total × 100
  • laju_pertumbuhan_pct = (ntb_adhk_t / ntb_adhk_{t-1} - 1) × 100
  • indeks_implisit      = ntb_adhb / ntb_adhk × 100
  • laju_implisit_pct    = (implisit_t / implisit_{t-1} - 1) × 100
```

---

## Sistem Rasio (SUT 2019 BPS)

| Jenis | Subkategori | 2008-2010 | 2011+ |
|-------|-------------|-----------|-------|
| OS    | 1.1.a–1.3   | 15.15%    | 16.16% |
| WIP   | Pangan, Perkebunan | 13.13% | 14.14% |
| WIP   | Hortikultura, Peternakan | 0% | 0% |
| KA    | Semua pertanian | 10.00% (2008-09), 20.20% (2010) | 25.25% |
| ADJ   | Pertanian umum | 12.56% | 10.12% |
| ADJ   | Kehutanan (1.2) | 10.00–10.21% | 10.37–11.24% (per tahun) |
| ADJ   | Perikanan (1.3) | 12.65% | 9.82% |

### Prioritas Lookup Rasio

```
1. rasio_override (wilayah + komoditas spesifik)
2. rasio_override (wilayah + kategori)
3. rasio_referensi (komoditas spesifik)
4. rasio_referensi (kategori subkategori)
5. rasio_referensi (kategori parent: 1.1.a → 1.1 → 1)
6. ❌ RasioTidakDitemukanError
```

---

## Wilayah yang Didukung

| Kode | Nama | Level |
|------|------|-------|
| 65   | Provinsi Kalimantan Utara | Provinsi |
| 6501 | Kabupaten Malinau | Kabupaten |
| 6502 | Kabupaten Bulungan | Kabupaten |
| 6503 | Kabupaten Tana Tidung | Kabupaten |
| 6504 | Kabupaten Nunukan | Kabupaten |
| 6571 | Kota Tarakan | Kota |

---

## Pengembangan Selanjutnya

- [ ] **Fase 2**: REST API endpoints (PATCH input, GET hasil)
- [ ] **Fase 3**: UI Lembar Kerja (tabel, form input real-time)
- [ ] **Fase 4**: SSE/WebSocket reactive updates
- [ ] **Fase 5**: Export Excel/PDF format BPS
- [ ] **Fase 6**: Import massal dari file Excel Dinas
