"""Pydantic schemas — InputProduksi."""
from __future__ import annotations
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, Field, field_validator


class InputProduksiRead(BaseModel):
    komoditas_id: int
    komoditas_nama: str
    kategori_kode: str
    wujud_produksi: Optional[str]
    satuan_produksi: Optional[str]
    wilayah_kode: str
    tahun: int
    triwulan: Optional[int]
    kuantum: Optional[Decimal]
    status: str
    sumber_data: Optional[str]
    # Triwulan breakdown (diisi jika filter=Tahunan dan data TW tersedia)
    tw1: Optional[Decimal] = None
    tw2: Optional[Decimal] = None
    tw3: Optional[Decimal] = None
    tw4: Optional[Decimal] = None
    total_tw: Optional[Decimal] = None        # sum TW1–TW4
    has_conflict: bool = False                # tahunan langsung DAN sum TW keduanya ada

    model_config = {"from_attributes": True}


class InputProduksiPatch(BaseModel):
    kuantum: Optional[Decimal] = Field(None, ge=0)
    sumber_data: Optional[str] = Field(None, max_length=255)
    status: Optional[str] = Field(None, pattern="^(sementara|tetap)$")

    @field_validator("kuantum", mode="before")
    @classmethod
    def empty_to_none(cls, v):
        if v == "" or v == "null":
            return None
        return v
