"""Pydantic schemas — InputHarga."""
from __future__ import annotations
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, Field, field_validator


class InputHargaRead(BaseModel):
    komoditas_id: int
    komoditas_nama: str
    kategori_kode: str
    wujud_produksi: Optional[str]
    satuan_harga: Optional[str]
    wilayah_kode: str
    tahun: int
    triwulan: Optional[int]
    harga_berlaku: Optional[Decimal]
    harga_konstan_2010: Optional[Decimal]
    sumber_data: Optional[str]

    model_config = {"from_attributes": True}


class InputHargaPatch(BaseModel):
    harga_berlaku: Optional[Decimal] = Field(None, ge=0)
    harga_konstan_2010: Optional[Decimal] = Field(None, ge=0)
    sumber_data: Optional[str] = Field(None, max_length=255)

    @field_validator("harga_berlaku", "harga_konstan_2010", mode="before")
    @classmethod
    def empty_string_to_none(cls, v):
        if v == "" or v == "null":
            return None
        return v


class KategoriHierarki(BaseModel):
    """Satu level dalam pohon kategori → komoditas."""
    kode: str
    nama: str
    level: int
    metode_adhb: Optional[str]
    metode_adhk: Optional[str]
    urutan: int
    children: list["KategoriHierarki"] = []
    komoditas: list["KomoditasSimple"] = []

    model_config = {"from_attributes": True}


class KomoditasSimple(BaseModel):
    id: int
    kode_internal: str
    nama: str
    kategori_kode: str
    satuan_produksi: Optional[str]
    satuan_harga: Optional[str]
    wujud_produksi: Optional[str]
    faktor_konversi: Optional[Decimal]
    aktif: bool

    model_config = {"from_attributes": True}


KategoriHierarki.model_rebuild()
