@echo off
REM ============================================================
REM SIKALTARA — Setup Script untuk Lingkungan BPS (Windows)
REM Sistem LK PDRB Provinsi Kalimantan Utara
REM ============================================================

echo.
echo  ╔══════════════════════════════════════════════════════╗
echo  ║   SIKALTARA — Sistem LK PDRB Kalimantan Utara        ║
echo  ║   BPS Indonesia, SNA 2008, Tahun Dasar 2010=100     ║
echo  ╚══════════════════════════════════════════════════════╝
echo.

REM --- Cek Python ---
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python tidak ditemukan. Install Python 3.11+ dari https://python.org
    pause
    exit /b 1
)
echo [OK] Python ditemukan
python --version

REM --- Masuk ke direktori backend ---
cd /d "%~dp0backend"

REM --- Buat virtual environment jika belum ada ---
if not exist ".venv" (
    echo.
    echo [SETUP] Membuat virtual environment...
    python -m venv .venv
)
echo [OK] Virtual environment siap

REM --- Aktifkan virtual environment ---
call .venv\Scripts\activate.bat
echo [OK] Virtual environment aktif

REM --- Install dependencies ---
echo.
echo [SETUP] Menginstall dependencies...
pip install -e ".[dev]" --quiet
if %errorlevel% neq 0 (
    echo [ERROR] Gagal menginstall dependencies
    pause
    exit /b 1
)
echo [OK] Dependencies terinstall

REM --- Buat .env jika belum ada ---
if not exist ".env" (
    echo.
    echo [SETUP] Membuat file konfigurasi .env dari template...
    copy .env.example .env
    echo.
    echo [PENTING] Edit file backend\.env dan sesuaikan DATABASE_URL
    echo           Contoh untuk PostgreSQL lokal:
    echo           DATABASE_URL=postgresql://postgres:password@localhost:5432/sikaltara_db
    echo.
)

REM --- Tanya apakah mau jalankan migrasi ---
echo.
set /p run_migrate="[?] Jalankan migrasi database sekarang? (y/n): "
if /i "%run_migrate%"=="y" (
    echo.
    echo [MIGRATE] Menjalankan migrasi database...
    alembic upgrade head
    if %errorlevel% neq 0 (
        echo [ERROR] Migrasi gagal. Pastikan PostgreSQL berjalan dan DATABASE_URL benar di .env
        pause
        exit /b 1
    )
    echo [OK] Migrasi database selesai
)

REM --- Jalankan tests ---
echo.
set /p run_tests="[?] Jalankan unit tests? (y/n): "
if /i "%run_tests%"=="y" (
    echo.
    echo [TEST] Menjalankan unit tests...
    pytest tests/ -v
)

REM --- Jalankan server ---
echo.
set /p run_server="[?] Jalankan development server sekarang? (y/n): "
if /i "%run_server%"=="y" (
    echo.
    echo [SERVER] Menjalankan FastAPI development server...
    echo          URL: http://localhost:8000
    echo          Dokumentasi API: http://localhost:8000/docs
    echo          Tekan Ctrl+C untuk berhenti
    echo.
    uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
)

echo.
echo [SELESAI] Setup SIKALTARA berhasil!
echo.
echo Perintah berguna:
echo   cd backend
echo   .venv\Scripts\activate
echo   alembic upgrade head       -- migrasi database
echo   pytest tests/ -v           -- jalankan tests
echo   uvicorn app.main:app --reload -- jalankan server
echo.
pause
