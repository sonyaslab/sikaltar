# File: app/schemas/adjustment.py
"""
Pydantic Schemas untuk Adjustment Manual
"""
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel


class AdjustmentManualRequest(BaseModel):
    adjustment_manual_adhb: Optional[Decimal] = None
    adjustment_manual_adhk: Optional[Decimal] = None
    keterangan: Optional[str] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "adjustment_manual_adhb": 1500.50,
                "adjustment_manual_adhk": -250.25,
                "keterangan": "Penyesuaian berdasarkan data tambahan dari dinas"
            }
        }


class AdjustmentManualRead(BaseModel):
    kategori_kode: str
    ntb_hitung_adhb: Optional[Decimal]
    ntb_hitung_adhk: Optional[Decimal]
    adjustment_manual_adhb: Optional[Decimal]
    adjustment_manual_adhk: Optional[Decimal]
    ntb_final_adhb: Optional[Decimal]
    ntb_final_adhk: Optional[Decimal]