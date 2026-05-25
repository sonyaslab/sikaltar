"""
API Router — MDM Kode Klasifikasi (KBLI/KBKI/KLUI)
Subhalaman 3: Mapping kode antar versi + gap analysis
"""
from __future__ import annotations
from typing import Optional
from fastapi import APIRouter, Body, Depends, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.master import MasterVersi
from app.models.komoditas import Komoditas
from app.services.mdm_audit_service import log_insert

router = APIRouter()


@router.get('/versi', summary='List versi klasifikasi')
def list_versi(db: Session = Depends(get_db)):
    rows = db.query(MasterVersi).order_by(MasterVersi.tahun_terbit).all()
    return [{
        'id': r.id, 'kode_versi': r.kode_versi, 'nama_versi': r.nama_versi,
        'tahun_terbit': r.tahun_terbit, 'berlaku_mulai_pdrb': r.berlaku_mulai_pdrb,
        'catatan': r.catatan, 'aktif': r.aktif,
    } for r in rows]


@router.post('/versi', summary='Tambah versi klasifikasi baru', status_code=201)
def create_versi(
    payload: dict = Body(...),
    user_nama: str = Query('Admin'),
    db: Session = Depends(get_db),
):
    v = MasterVersi(**{k: payload[k] for k in
        ('kode_versi','nama_versi','tahun_terbit','berlaku_mulai_pdrb','catatan')
        if k in payload})
    v.aktif = True
    db.add(v)
    db.flush()
    log_insert(db, 'master_versi', v.id, user_nama)
    db.commit()
    return {'id': v.id, 'kode_versi': v.kode_versi}


@router.get('/mapping', summary='Tabel mapping komoditas ↔ kode klasifikasi')
def get_mapping(
    versi: str = Query('kbli_2009', description='kbli_2009|kbli_2005|klui_1990|kbki_2010'),
    kategori_kode: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    valid_cols = {'kbli_2009', 'kbli_2005', 'klui_1990', 'kbki_2010'}
    if versi not in valid_cols:
        versi = 'kbli_2009'

    q = db.query(Komoditas).filter(Komoditas.aktif.is_(True))
    if kategori_kode:
        q = q.filter(Komoditas.kategori_kode == kategori_kode)
    rows = q.order_by(Komoditas.kategori_kode, Komoditas.nama).all()

    return [{
        'id': k.id, 'nama': k.nama, 'kategori_kode': k.kategori_kode,
        'kode': getattr(k, versi, None),
        'status': 'terisi' if getattr(k, versi) else 'kosong',
    } for k in rows]


@router.get('/gap-analysis', summary='Komoditas tanpa kode KBLI/KBKI')
def get_gap_analysis(
    versi: str = Query('kbli_2009'),
    db: Session = Depends(get_db),
):
    valid = {'kbli_2009', 'kbli_2005', 'klui_1990', 'kbki_2010'}
    if versi not in valid:
        versi = 'kbli_2009'
    col = getattr(Komoditas, versi)
    rows = (
        db.query(Komoditas)
        .filter(Komoditas.aktif.is_(True), col.is_(None))
        .order_by(Komoditas.kategori_kode, Komoditas.nama)
        .all()
    )
    return {
        'versi': versi, 'total_kosong': len(rows),
        'rows': [{'id': k.id, 'nama': k.nama, 'kategori_kode': k.kategori_kode} for k in rows],
    }
