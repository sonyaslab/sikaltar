"""
API Router — MDM Faktor Konversi
Subhalaman 5: Edit faktor konversi dengan audit dan cascade warning
"""
from __future__ import annotations
from typing import Optional
from fastapi import APIRouter, Body, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.komoditas import Komoditas
from app.models.master import AuditMaster
from app.services.mdm_audit_service import log_update

router = APIRouter()

# Data faktor konversi standar BPS
FAKTOR_STANDAR = [
    ('Tebu',          'Tebu Giling',       'Gula Hablur',  6.86),
    ('Kapas',         'Kapas Berbiji',      'Serat',        32.50),
    ('Tembakau',      'Daun Basah',         'Daun Kering',  14.00),
    ('Kapuk',         'Buah Kering',        'Serat Berbiji',20.00),
    ('Serat Karung',  'Serat Basah',        'Serat Basah',  1.00),
    ('Jarak',         'Buah',               'Biji Kering',  35.00),
    ('Karet',         'Lateks Kering',      'Karet Kering', 27.50),
    ('Kelapa Sawit',  'TBS',                'CPO',          20.00),
    ('Kelapa Dalam',  'Butir',              'Kopra',        22.50),
    ('Kelapa Hibrida','Butir',              'Kopra',        17.50),
    ('Kopi',          'Buah Basah',         'Kopi Berasan', 20.00),
    ('Teh',           'Pucuk Basah',        'Daun Kering',  23.00),
    ('Cengkeh',       'Bunga Segar',        'Bunga Kering', 22.50),
    ('Kakao',         'Buah Segar',         'Biji Kering',  32.50),
    ('Lada',          'Buah Segar',         'Biji Kering',  27.50),
    ('Kayu Manis',    'Kulit Basah',        'Kulit Kering', 54.50),
    ('Pala',          'Buah Segar',         'Biji Kering',  46.50),
    ('Panili',        'Polong Basah',       'Polong Kering',22.50),
    ('Pinang',        'Buah Segar',         'Biji Kering',  32.50),
    ('Sereh Wangi',   'Daun Segar',         'Minyak',       0.345),
    ('Nilam',         'Daun Segar',         'Minyak',       0.475),
    ('Gambir',        'Daun & Ranting Bsr', 'Gambir Kering',6.50),
]


@router.get('', summary='List semua komoditas dengan faktor konversi')
def list_faktor(
    q: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    query = db.query(Komoditas).filter(
        Komoditas.aktif.is_(True),
        Komoditas.faktor_konversi.is_not(None),
    )
    if q:
        query = query.filter(Komoditas.nama.ilike(f'%{q}%'))

    rows = query.order_by(Komoditas.nama).all()

    # Get latest berlaku_mulai from audit
    result = []
    for k in rows:
        audit = (
            db.query(AuditMaster)
            .filter(
                AuditMaster.tabel_nama == 'komoditas',
                AuditMaster.record_id == k.id,
                AuditMaster.kolom_ubah == 'faktor_konversi',
            ).order_by(AuditMaster.waktu.desc()).first()
        )
        result.append({
            'id': k.id, 'nama': k.nama, 'kategori_kode': k.kategori_kode,
            'bahan_baku': k.wujud_produksi,
            'produk_jadi': k.produk_jadi,
            'faktor_konversi': float(k.faktor_konversi) if k.faktor_konversi else None,
            'berlaku_mulai': audit.berlaku_mulai if audit else k.berlaku_mulai,
        })
    return result


@router.get('/standar', summary='Daftar faktor konversi standar BPS')
def get_faktor_standar():
    return [{
        'nama': item[0], 'bahan_baku': item[1],
        'produk_jadi': item[2], 'faktor_pct': item[3],
    } for item in FAKTOR_STANDAR]


@router.get('/{komoditas_id}/history', summary='Riwayat perubahan faktor konversi')
def get_faktor_history(komoditas_id: int, db: Session = Depends(get_db)):
    k = db.get(Komoditas, komoditas_id)
    if not k:
        raise HTTPException(404, 'Komoditas tidak ditemukan')
    audits = (
        db.query(AuditMaster)
        .filter(
            AuditMaster.tabel_nama == 'komoditas',
            AuditMaster.record_id == komoditas_id,
            AuditMaster.kolom_ubah == 'faktor_konversi',
        ).order_by(AuditMaster.waktu.desc()).all()
    )
    return {
        'komoditas_id': k.id, 'nama': k.nama,
        'faktor_sekarang': float(k.faktor_konversi) if k.faktor_konversi else None,
        'history': [
            {
                'nilai_lama': a.nilai_lama, 'nilai_baru': a.nilai_baru,
                'berlaku_mulai': a.berlaku_mulai, 'user_nama': a.user_nama,
                'waktu': a.waktu.isoformat() if a.waktu else None,
                'alasan': a.alasan,
            }
            for a in audits
        ],
    }


@router.put('/{komoditas_id}', summary='Update faktor konversi')
def update_faktor(
    komoditas_id: int,
    payload: dict = Body(...),
    user_nama: str = Query('Admin'),
    db: Session = Depends(get_db),
):
    k = db.get(Komoditas, komoditas_id)
    if not k:
        raise HTTPException(404, 'Komoditas tidak ditemukan')

    faktor_baru = payload.get('faktor_konversi')
    berlaku_mulai = payload.get('berlaku_mulai')
    alasan = payload.get('alasan', '').strip()
    sumber_kajian = payload.get('sumber_kajian', '').strip()

    if faktor_baru is None:
        raise HTTPException(422, 'faktor_konversi wajib diisi')
    if not alasan:
        raise HTTPException(422, 'alasan wajib diisi')
    if not berlaku_mulai:
        raise HTTPException(422, 'berlaku_mulai (tahun) wajib diisi')

    faktor_lama = float(k.faktor_konversi) if k.faktor_konversi else None
    log_update(
        db, 'komoditas', k.id, 'faktor_konversi',
        faktor_lama, faktor_baru, user_nama,
        alasan=f"{alasan} | Sumber: {sumber_kajian}",
        berlaku_mulai=berlaku_mulai,
    )
    k.faktor_konversi = faktor_baru
    if hasattr(k, 'berlaku_mulai'):
        pass  # Jangan update berlaku_mulai komoditas — itu waktu berlaku komoditas, bukan faktor
    db.commit()

    return {
        'id': k.id, 'nama': k.nama,
        'faktor_lama': faktor_lama, 'faktor_baru': faktor_baru,
        'berlaku_mulai': berlaku_mulai,
        'cascade_warning': (
            f'⚠ Perubahan faktor konversi {k.nama!r} berlaku mulai {berlaku_mulai}. '
            f'Gunakan endpoint /recalc untuk menghitung ulang data historis.'
        ),
    }


@router.post('/{komoditas_id}/recalc', summary='Trigger cascade recalculate historis')
def trigger_recalc(
    komoditas_id: int,
    tahun_mulai: int = Query(..., description='Tahun mulai recalculate'),
    tahun_akhir: int = Query(...),
    user_nama: str = Query('Admin'),
    db: Session = Depends(get_db),
):
    k = db.get(Komoditas, komoditas_id)
    if not k:
        raise HTTPException(404, 'Komoditas tidak ditemukan')

    from app.services.cascade_service import enqueue_cascade
    task_ids = []
    for tahun in range(tahun_mulai, tahun_akhir + 1):
        for tw in [None, 1, 2, 3, 4]:
            tid = enqueue_cascade('produksi', '65', tahun, tw, komoditas_id=komoditas_id)
            task_ids.append(tid)

    return {
        'message': f'Recalculate dijadwalkan untuk {k.nama!r} tahun {tahun_mulai}–{tahun_akhir}',
        'task_ids': task_ids,
        'komoditas': k.nama,
    }
