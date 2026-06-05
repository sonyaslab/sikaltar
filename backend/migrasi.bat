@echo off
REM ============================================
REM Script untuk Menjalankan Database Migration
REM ============================================

echo.
echo ========================================
echo   SIKALTARA Database Migration
echo   BPS Kalimantan Utara
echo ========================================
echo.

REM Aktifkan virtual environment
call .venv\Scripts\activate.bat

echo [INFO] Virtual environment aktif
echo.

REM Cek status migrasi saat ini
echo [1/2] Checking current migration status...
alembic current
echo.

REM Jalankan migrasi
echo [2/2] Running database migrations...
alembic upgrade head

if errorlevel 1 (
    echo.
    echo ERROR: Migration gagal!
    echo Periksa koneksi database di file .env
    pause
    exit /b 1
)

echo.
echo ========================================
echo Migration BERHASIL!
echo.
echo Akun default yang dibuat:
echo   1. Username: admin
echo      Password: admin123
echo      Role: Administrator
echo.
echo   2. Username: operator_test
echo      Password: operator123
echo      Role: Operator (Kab. Malinau)
echo.
echo Silakan jalankan: jalankan.bat
echo untuk start server
echo ========================================
echo.

pause
