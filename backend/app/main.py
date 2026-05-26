"""
SIKALTARA — FastAPI Application Entry Point
Sistem LK PDRB Provinsi Kalimantan Utara
"""
from __future__ import annotations

import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.database import check_connection


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup dan shutdown lifecycle."""
    if check_connection():
        print("[SIKALTARA] ✅ Koneksi database berhasil")
    else:
        print("[SIKALTARA] ❌ Koneksi database GAGAL — periksa konfigurasi DATABASE_URL")
    yield


app = FastAPI(
    title="SIKALTARA — Sistem LK PDRB Kalimantan Utara",
    description=(
        "Backend API untuk Lembar Kerja PDRB Provinsi Kalimantan Utara. "
        "Standar: BPS Indonesia, SNA 2008, Tahun Dasar 2010=100."
    ),
    version="2.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if os.getenv("APP_ENV") == "development" else [
        "http://localhost:8000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Health ───────────────────────────────────────────────────────────────────
@app.get("/health", tags=["Health"])
def health_check():
    db_ok = check_connection()
    return {
        "status": "ok" if db_ok else "degraded",
        "database": "connected" if db_ok else "disconnected",
        "environment": os.getenv("APP_ENV", "unknown"),
    }


# ─── API Routers ──────────────────────────────────────────────────────────────
from app.api.referensi import router as referensi_router          # noqa: E402
from app.api.input_harga import router as harga_router             # noqa: E402
from app.api.input_produksi import router as produksi_router       # noqa: E402
from app.api.input_rasio import router as rasio_router             # noqa: E402
from app.api.input_deflator_sse import deflator_router, sse_router # noqa: E402
from app.api.s2 import router as s2_router                         # noqa: E402
from app.api.mdm_kategori import router as mdm_kategori_router     # noqa: E402
from app.api.mdm_komoditas import router as mdm_komoditas_router   # noqa: E402
from app.api.mdm_klasifikasi import router as mdm_klasifikasi_router  # noqa: E402
from app.api.mdm_satuan import router as mdm_satuan_router         # noqa: E402
from app.api.mdm_faktor_konversi import router as mdm_faktor_router  # noqa: E402
from app.api.mdm_audit import router as mdm_audit_router           # noqa: E402
from app.api.mdm_metode import router as mdm_metode_router         # noqa: E402
from app.api.s3 import router as s3_router                         # noqa: E402

app.include_router(referensi_router, prefix="/api", tags=["Referensi"])
app.include_router(harga_router, prefix="/api/input/harga", tags=["S1.H — Harga"])
app.include_router(produksi_router, prefix="/api/input/produksi", tags=["S1.P — Produksi"])
app.include_router(rasio_router, prefix="/api/rasio", tags=["S1.R — Rasio"])
app.include_router(deflator_router, prefix="/api/input/deflator", tags=["S1.I — Deflator"])
app.include_router(sse_router, prefix="/api", tags=["SSE Events"])
app.include_router(s2_router, prefix="/api/s2", tags=["S2 — Lembar Kerja Hasil"])
app.include_router(s3_router, prefix="/api/s3", tags=["S3 — Tabel Pokok & Dashboard"])

# ─── MDM Routers ────────────────────────────────────────────────────────────────
app.include_router(mdm_kategori_router,    prefix="/api/mdm/kategori",        tags=["MDM — Kategori"])
app.include_router(mdm_komoditas_router,   prefix="/api/mdm/komoditas",       tags=["MDM — Komoditas"])
app.include_router(mdm_klasifikasi_router, prefix="/api/mdm/klasifikasi",     tags=["MDM — Klasifikasi"])
app.include_router(mdm_satuan_router,      prefix="/api/mdm/satuan",          tags=["MDM — Satuan"])
app.include_router(mdm_faktor_router,      prefix="/api/mdm/faktor-konversi", tags=["MDM — Faktor Konversi"])
app.include_router(mdm_audit_router,       prefix="/api/mdm/audit",           tags=["MDM — Audit Log"])
app.include_router(mdm_metode_router,      prefix="/api/mdm/metode",          tags=["MDM — Metode Estimasi"])



# ─── Frontend Static Files ────────────────────────────────────────────────────
frontend_dir = Path(__file__).resolve().parent.parent.parent / "frontend"
if frontend_dir.exists():
    # Serve semua file statis di /app/*
    app.mount("/app", StaticFiles(directory=str(frontend_dir), html=True), name="frontend")


@app.get("/", include_in_schema=False)
def root():
    idx = frontend_dir / "index.html"
    if idx.exists():
        return FileResponse(str(idx))
    return {"aplikasi": "SIKALTARA", "versi": "2.0.0", "ui": "/app/index.html"}
