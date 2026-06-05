@echo off
REM ============================================
REM Script Helper untuk Menjalankan SIKALTARA
REM ============================================

echo.
echo ========================================
echo   SIKALTARA Backend Server Starter
echo   BPS Kalimantan Utara
echo ========================================
echo.

REM Aktifkan virtual environment
call .venv\Scripts\activate.bat

echo [1/3] Virtual environment aktif...
echo.

REM Cek database connection (optional)
echo [2/3] Testing database connection...
python -c "from app.database import check_connection; exit(0 if check_connection() else 1)"
if errorlevel 1 (
    echo ERROR: Database tidak terhubung!
    echo Pastikan PostgreSQL sudah berjalan di port 5432
    echo.
    pause
    exit /b 1
)
echo Database OK!
echo.

REM Start server
echo [3/3] Starting FastAPI server...
echo.
echo ========================================
echo Server akan berjalan di:
echo   http://localhost:8000
echo.
echo Login page:
echo   http://localhost:8000/app/login.html
echo.
echo API Docs:
echo   http://localhost:8000/docs
echo.
echo Tekan Ctrl+C untuk stop server
echo ========================================
echo.

uvicorn app.main:app --reload --port 8000 --host 0.0.0.0

pause
