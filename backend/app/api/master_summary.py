"""
API Router — Master Summary
Landing page untuk admin/master
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.komoditas import Komoditas
from app.models.kategori_pdrb import KategoriPdrb
from app.models.rasio import RasioReferensi
from app.models.master import AuditMaster

router = APIRouter()

@router.get('', summary='Summary data master')
def get_master_summary(db: Session = Depends(get_db)):
    kom_count = db.query(func.count(Komoditas.id)).filter(Komoditas.aktif == True).scalar() or 0
    kat_count = db.query(func.count(KategoriPdrb.id)).scalar() or 0
    rasio_count = db.query(func.count(RasioReferensi.id)).scalar() or 0

    recent_audits = db.query(AuditMaster).order_by(AuditMaster.waktu.desc()).limit(5).all()

    return {
        'stats': {
            'komoditas': kom_count,
            'kategori': kat_count,
            'rasio': rasio_count
        },
        'recent_changes': [
            {
                'id': r.id,
                'waktu': r.waktu.isoformat(),
                'tabel': r.tabel_nama,
                'aksi': r.aksi,
                'kolom': r.kolom_ubah,
                'lama': r.nilai_lama,
                'baru': r.nilai_baru,
                'user': r.user_nama,
                'record_id': r.record_id
            } for r in recent_audits
        ]
    }
