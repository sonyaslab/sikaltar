"""Pydantic schemas — Rasio & Deflator."""
from __future__ import annotations
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, Field


# ── Rasio ─────────────────────────────────────────────────────────────────────

class RasioRow(BaseModel):
    """Satu baris di tabel rasio: nilai default + override lokal."""
    kategori_kode: str
    kategori_nama: str
    komoditas_id: Optional[int] = None
    komoditas_nama: Optional[str] = None
    jenis_rasio: str
    tahun: int
    berlaku_untuk: str
    nilai_default: Optional[Decimal]     # dari rasio_referensi
    nilai_override: Optional[Decimal]    # dari rasio_override (None = belum di-override)
    override_id: Optional[int] = None   # ID rasio_override jika ada
    override_keterangan: Optional[str] = None
    is_overridden: bool = False          # True jika nilai_override terisi


class RasioOverridePatch(BaseModel):
    komoditas_id: Optional[int] = None
    kategori_kode: str
    jenis_rasio: str
    wilayah_kode: str
    tahun: int
    nilai: Decimal = Field(..., ge=0, le=10)
    berlaku_untuk: str = Field(..., pattern="^(ADHB|ADHK|KEDUANYA)$")
    keterangan: Optional[str] = Field(None, max_length=500)


class RasioImpactPreview(BaseModel):
    """Estimasi dampak perubahan rasio sebelum di-save."""
    komoditas_count: int
    ntb_adhb_sebelum: Optional[Decimal]
    ntb_adhb_sesudah: Optional[Decimal]
    ntb_adhb_delta: Optional[Decimal]
    ntb_adhk_sebelum: Optional[Decimal]
    ntb_adhk_sesudah: Optional[Decimal]
    ntb_adhk_delta: Optional[Decimal]


# ── Deflator ──────────────────────────────────────────────────────────────────

class DeflatorRead(BaseModel):
    kategori_kode: str
    kategori_nama: str
    metode_adhb: Optional[str]
    metode_adhk: Optional[str]
    wilayah_kode: str
    tahun: int
    triwulan: Optional[int]
    nilai_indeks: Optional[Decimal]
    nilai_indeks_tahun_lalu: Optional[Decimal]   # READ-ONLY, dari t-1
    perubahan_pct: Optional[Decimal]             # READ-ONLY, dihitung
    is_editable: bool                            # True hanya jika metode_adhk == 'Deflasi'

    model_config = {"from_attributes": True}


class DeflatorPatch(BaseModel):
    nilai_indeks: Decimal = Field(..., ge=0, le=10000)
