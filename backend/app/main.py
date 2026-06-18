"""
SIKALTARA — FastAPI Application Entry Point
Sistem LK PDRB Provinsi Kalimantan Utara
"""
from __future__ import annotations

import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.database import check_connection
from app.dependencies.auth import require_operator_or_admin, require_admin


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

_IS_DEV = os.getenv("APP_ENV", "production") == "development"
_ALLOWED_ORIGINS = [
    "http://localhost:8000",
    "http://127.0.0.1:8000",
    "http://localhost:3000",
] if _IS_DEV else [
    os.getenv("APP_ORIGIN", "http://localhost:8000"),
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_ALLOWED_ORIGINS,
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
from app.api.input_ihp import router as ihp_router                 # noqa: E402
from app.api.input_adjustment import router as adjustment_router   # noqa: E402
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
from app.api.master_komoditas import router as master_komoditas_router # noqa: E402
from app.api.master_summary import router as master_summary_router # noqa: E402
from app.routers.auth import router as auth_router                 # noqa: E402
from app.routers.admin_users import router as admin_users_router   # noqa: E402

# ─── Auth Router (TIDAK dilindungi — public endpoint) ────────────────────────
app.include_router(auth_router, prefix="/auth", tags=["Autentikasi"])

# ─── Protected API Routers ────────────────────────────────────────────────────
_auth_dep = [Depends(require_operator_or_admin)]

app.include_router(referensi_router, prefix="/api", tags=["Referensi"],
                   dependencies=_auth_dep)
app.include_router(harga_router, prefix="/api/input/harga", tags=["S1.H — Harga"],
                   dependencies=_auth_dep)
app.include_router(ihp_router, prefix="/api/input/ihp", tags=["S1.IHP — Indeks Harga Produksi"],
                   dependencies=_auth_dep)
app.include_router(adjustment_router, prefix="/api/input/adjustment", tags=["Adjustment Manual"],
                   dependencies=_auth_dep)
app.include_router(produksi_router, prefix="/api/input/produksi", tags=["S1.P — Produksi"],
                   dependencies=_auth_dep)
app.include_router(rasio_router, prefix="/api/rasio", tags=["S1.R — Rasio"],
                   dependencies=_auth_dep)
app.include_router(deflator_router, prefix="/api/input/deflator", tags=["S1.I — Deflator"],
                   dependencies=_auth_dep)
app.include_router(sse_router, prefix="/api", tags=["SSE Events"])
app.include_router(s2_router, prefix="/api/s2", tags=["S2 — Lembar Kerja Hasil"],
                   dependencies=_auth_dep)
app.include_router(s3_router, prefix="/api/s3", tags=["S3 — Tabel Pokok & Dashboard"],
                   dependencies=_auth_dep)

# ─── MDM Routers (operator_or_admin) ─────────────────────────────────────────
app.include_router(mdm_kategori_router,    prefix="/api/mdm/kategori",        tags=["MDM — Kategori"],
                   dependencies=_auth_dep)
app.include_router(mdm_komoditas_router,   prefix="/api/mdm/komoditas",       tags=["MDM — Komoditas"],
                   dependencies=_auth_dep)
app.include_router(mdm_klasifikasi_router, prefix="/api/mdm/klasifikasi",     tags=["MDM — Klasifikasi"],
                   dependencies=_auth_dep)
app.include_router(mdm_satuan_router,      prefix="/api/mdm/satuan",          tags=["MDM — Satuan"],
                   dependencies=_auth_dep)
app.include_router(mdm_faktor_router,      prefix="/api/mdm/faktor-konversi", tags=["MDM — Faktor Konversi"],
                   dependencies=_auth_dep)
app.include_router(mdm_audit_router,       prefix="/api/mdm/audit",           tags=["MDM — Audit Log"],
                   dependencies=_auth_dep)
app.include_router(mdm_metode_router,      prefix="/api/mdm/metode",          tags=["MDM — Metode Estimasi"],
                   dependencies=_auth_dep)
app.include_router(master_komoditas_router, prefix="/api/master/komoditas",   tags=["Master — Komoditas"],
                   dependencies=_auth_dep)
app.include_router(master_summary_router,   prefix="/api/master/summary",     tags=["Master — Summary"],
                   dependencies=_auth_dep)

# ─── Admin Users Router ───────────────────────────────────────────────────────
app.include_router(
    admin_users_router,
    prefix="/admin/users",
    tags=["Admin — Manajemen User"],
    dependencies=[Depends(require_admin)],
)

# ─── Frontend Static Files ────────────────────────────────────────────────────
frontend_dir = Path(__file__).resolve().parent.parent.parent / "frontend"

if frontend_dir.exists():
    # Mount lengkap di /app/* (untuk production + nginx)
    app.mount("/app", StaticFiles(directory=str(frontend_dir), html=True), name="frontend")

    # ── DEV MODE (tanpa Docker/Nginx) ──────────────────────────────────────────
    # Mount /css dan /js langsung dari root agar <link href="css/main.css"> dan
    # <script src="js/auth.js"> di index.html bisa resolve ke /css/... dan /js/...
    for _sub in ("css", "js"):
        _sub_path = frontend_dir / _sub
        if _sub_path.exists():
            app.mount(f"/{_sub}", StaticFiles(directory=str(_sub_path)), name=_sub)


@app.get("/", include_in_schema=False)
def root():
    """Serve index.html langsung dari root. CSS & JS di-handle mount /css dan /js."""
    idx = frontend_dir / "index.html"
    if idx.exists():
        return FileResponse(str(idx))
    return {"aplikasi": "SIKALTARA", "versi": "2.0.0", "ui": "/app/index.html"}


@app.get("/{filename}.html", include_in_schema=False)
def serve_html_page(filename: str):
    """
    Serve semua halaman HTML dari root path (dev tanpa nginx).
    Dibutuhkan agar navigasi antar halaman berfungsi — misal /login.html,
    /s1-harga.html, /s3-dashboard.html, /admin-users.html, dll.
    """
    html_file = frontend_dir / f"{filename}.html"
    if html_file.exists():
        return FileResponse(str(html_file))
    raise HTTPException(status_code=404, detail=f"Halaman '{filename}.html' tidak ditemukan.")