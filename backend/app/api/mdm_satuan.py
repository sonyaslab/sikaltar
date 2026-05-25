"""
API Router — MDM Satuan & Wujud Produksi
Subhalaman 4: Manajemen Master Satuan
"""
from __future__ import annotations
from typing import Optional
from fastapi import APIRouter, Body, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.master import MasterSatuan
from app.models.komoditas import Komoditas
from app.services.mdm_audit_service import log_insert, log_update_many, log_nonaktifkan

router = APIRouter()


@router.get('', summary='List satuan produksi')
def list_satuan(aktif_only: bool = Query(True), db: Session = Depends(get_db)):
    q = db.query(MasterSatuan)
    if aktif_only:
        q = q.filter(MasterSatuan.aktif.is_(True))
    satuan_list = q.order_by(MasterSatuan.kode).all()
    # Count komoditas per satuan
    counts = dict(
        db.query(Komoditas.satuan_produksi, func.count(Komoditas.id))
        .filter(Komoditas.aktif.is_(True))
        .group_by(Komoditas.satuan_produksi).all()
    )
    return [
        {
            'id': s.id, 'kode': s.kode, 'nama': s.nama,
            'keterangan': s.keterangan, 'aktif': s.aktif,
            'jumlah_komoditas': counts.get(s.kode, 0),
        }
        for s in satuan_list
    ]


@router.post('', summary='Tambah satuan baru', status_code=201)
def create_satuan(
    payload: dict = Body(...),
    user_nama: str = Query('Admin'),
    db: Session = Depends(get_db),
):
    kode = payload.get('kode', '').strip()
    if not kode:
        raise HTTPException(422, 'Kode satuan wajib diisi')
    if db.query(MasterSatuan).filter(MasterSatuan.kode == kode).first():
        raise HTTPException(409, f'Satuan {kode!r} sudah ada')
    s = MasterSatuan(kode=kode, nama=payload.get('nama', kode),
                     keterangan=payload.get('keterangan'), aktif=True)
    db.add(s)
    db.flush()
    log_insert(db, 'master_satuan', s.id, user_nama)
    db.commit()
    return {'id': s.id, 'kode': s.kode, 'nama': s.nama}


@router.put('/{satuan_id}', summary='Edit satuan')
def update_satuan(
    satuan_id: int, payload: dict = Body(...),
    user_nama: str = Query('Admin'), db: Session = Depends(get_db),
):
    s = db.get(MasterSatuan, satuan_id)
    if not s:
        raise HTTPException(404, 'Satuan tidak ditemukan')
    update_data = {k: v for k, v in payload.items() if k in ('nama', 'keterangan')}
    log_update_many(db, 'master_satuan', s.id, s, update_data, user_nama)
    for k, v in update_data.items():
        setattr(s, k, v)
    db.commit()
    return {'id': s.id, 'kode': s.kode, 'nama': s.nama}


@router.delete('/{satuan_id}', summary='Nonaktifkan satuan')
def delete_satuan(
    satuan_id: int, alasan: str = Query(...),
    user_nama: str = Query('Admin'), db: Session = Depends(get_db),
):
    s = db.get(MasterSatuan, satuan_id)
    if not s:
        raise HTTPException(404, 'Satuan tidak ditemukan')
    count = db.query(func.count(Komoditas.id)).filter(
        Komoditas.satuan_produksi == s.kode, Komoditas.aktif.is_(True)
    ).scalar() or 0
    if count > 0:
        raise HTTPException(409, f'Tidak bisa hapus: masih dipakai {count} komoditas aktif')
    s.aktif = False
    log_nonaktifkan(db, 'master_satuan', s.id, user_nama, alasan)
    db.commit()
    return {'message': f'Satuan {s.kode!r} dinonaktifkan'}
