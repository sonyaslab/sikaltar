from decimal import Decimal
from typing import Optional
from pydantic import BaseModel


class InputIHPBase(BaseModel):
    kategori_kode: str
    komoditas_id: Optional[int] = None
    wilayah_kode: str
    tahun: int
    triwulan: Optional[int] = None
    nilai_indeks: Decimal
    sumber_data: Optional[str] = None


class InputIHPRead(InputIHPBase):
    id: int

    class Config:
        orm_mode = True


class InputIHPPatch(BaseModel):
    kategori_kode: str
    komoditas_id: Optional[int] = None
    wilayah_kode: str
    tahun: int
    triwulan: Optional[int] = None
    nilai_indeks: Optional[Decimal] = None
    sumber_data: Optional[str] = None
