"""
API Router — MDM Komoditas
Subhalaman 2: Manajemen Komoditas (CRUD + Import Excel S0.CK)
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Body, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.komoditas import Komoditas
from app.models.kategori_pdrb import KategoriPdrb
from app.models.master import AuditMaster
from app.services.mdm_audit_service import log_insert, log_update_many, log_nonaktifkan

router = APIRouter()

# Kolom yang mengharuskan alasan + berlaku_mulai saat update
SENSITIVE_COLS = {'kbli_2009', 'kbli_2005', 'klui_1990', 'kbki_2010',
                  'faktor_konversi', 'satuan_produksi', 'metode_harga'}


def _kom_to_dict(k: Komoditas) -> dict:
    return {
        'id':               k.id,
        'kode_internal':    k.kode_internal,
        'nama':             k.nama,
        'kategori_kode':    k.kategori_kode,
        'kategori_nama':    k.kategori.nama if k.kategori else None,
        'satuan_produksi':  k.satuan_produksi,
        'satuan_harga':     k.satuan_harga,
        'faktor_konversi':  float(k.faktor_konversi) if k.faktor_konversi else None,
        'wujud_produksi':   k.wujud_produksi,
        'aktif':            k.aktif,
        # MDM fields
        'klui_1990':        k.klui_1990,
        'kbli_2005':        k.kbli_2005,
        'kbli_2009':        k.kbli_2009,
        'kbki_2010':        k.kbki_2010,
        'identitas':        k.identitas,
        'pdrb_kbli_kode':   k.pdrb_kbli_kode,
        'pdrb_kbli_uraian': k.pdrb_kbli_uraian,
        'klui_uraian':      k.klui_uraian,
        'catatan_varietas': k.catatan_varietas,
        'indeks_deflator':  k.indeks_deflator,
        'indeks_dbl_defl':  k.indeks_dbl_defl,
        'urutan_tampil':    k.urutan_tampil,
        'berlaku_mulai':    k.berlaku_mulai,
        'berlaku_sampai':   k.berlaku_sampai,
        'keterangan':       k.keterangan,
        'produk_jadi':      k.produk_jadi,
        'punya_wip':        k.punya_wip,
        'punya_cbr':        k.punya_cbr,
        'punya_output_ikutan': k.punya_output_ikutan,
        'metode_harga':     k.metode_harga,
    }


@router.get('', summary='List komoditas dengan filter')
def list_komoditas(
    q: Optional[str] = Query(None),
    kategori_kode: Optional[str] = Query(None),
    status: str = Query('aktif', description='aktif|nonaktif|semua'),
    kbli: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    query = db.query(Komoditas)
    if q:
        query = query.filter(Komoditas.nama.ilike(f'%{q}%'))
    if kategori_kode:
        query = query.filter(Komoditas.kategori_kode == kategori_kode)
    if status == 'aktif':
        query = query.filter(Komoditas.aktif.is_(True))
    elif status == 'nonaktif':
        query = query.filter(Komoditas.aktif.is_(False))
    if kbli:
        query = query.filter(
            Komoditas.kbli_2009.ilike(f'%{kbli}%') |
            Komoditas.kbli_2005.ilike(f'%{kbli}%')
        )

    total = query.count()
    rows = (
        query.order_by(Komoditas.kategori_kode, Komoditas.urutan_tampil, Komoditas.nama)
        .offset((page - 1) * per_page).limit(per_page).all()
    )
    return {'total': total, 'page': page, 'per_page': per_page,
            'rows': [_kom_to_dict(k) for k in rows]}


@router.get('/stats', summary='Statistik ringkasan komoditas')
def get_stats(db: Session = Depends(get_db)):
    total_aktif = db.query(func.count(Komoditas.id)).filter(Komoditas.aktif.is_(True)).scalar() or 0
    total_semua = db.query(func.count(Komoditas.id)).scalar() or 0
    tanpa_kbli = (
        db.query(func.count(Komoditas.id))
        .filter(Komoditas.aktif.is_(True), Komoditas.kbli_2009.is_(None))
        .scalar() or 0
    )
    return {'total_aktif': total_aktif, 'total_semua': total_semua, 'tanpa_kbli_2009': tanpa_kbli}


@router.get('/{komoditas_id}', summary='Detail komoditas + riwayat perubahan')
def get_komoditas(
    komoditas_id: int,
    include_audit: bool = Query(True),
    db: Session = Depends(get_db),
):
    k = db.get(Komoditas, komoditas_id)
    if not k:
        raise HTTPException(404, f'Komoditas ID={komoditas_id} tidak ditemukan')
    result = _kom_to_dict(k)
    if include_audit:
        audits = (
            db.query(AuditMaster)
            .filter(AuditMaster.tabel_nama == 'komoditas', AuditMaster.record_id == komoditas_id)
            .order_by(AuditMaster.waktu.desc())
            .limit(100)
            .all()
        )
        result['audit_history'] = [
            {
                'aksi': a.aksi, 'kolom_ubah': a.kolom_ubah,
                'nilai_lama': a.nilai_lama, 'nilai_baru': a.nilai_baru,
                'user_nama': a.user_nama, 'waktu': a.waktu.isoformat() if a.waktu else None,
                'alasan': a.alasan, 'berlaku_mulai': a.berlaku_mulai,
            }
            for a in audits
        ]
    return result


@router.post('', summary='Tambah komoditas baru', status_code=201)
def create_komoditas(
    payload: dict = Body(...),
    user_nama: str = Query('Admin'),
    db: Session = Depends(get_db),
):
    nama = payload.get('nama', '').strip()
    if not nama:
        raise HTTPException(422, 'Nama komoditas wajib diisi')
    kategori_kode = payload.get('kategori_kode', '')
    if not db.query(KategoriPdrb).filter(KategoriPdrb.kode == kategori_kode).first():
        raise HTTPException(404, f'Kategori {kategori_kode!r} tidak ditemukan')

    # Generate kode internal unik
    base_kode = f"{kategori_kode.replace('.', '-').upper()}-{nama[:15].replace(' ', '-').upper()}"
    kode = base_kode
    i = 1
    while db.query(Komoditas).filter(Komoditas.kode_internal == kode).first():
        kode = f'{base_kode}-{i}'
        i += 1

    mdm_fields = [
        'klui_1990', 'kbli_2005', 'kbli_2009', 'kbki_2010', 'identitas',
        'pdrb_kbli_kode', 'pdrb_kbli_uraian', 'klui_uraian', 'catatan_varietas',
        'indeks_deflator', 'indeks_dbl_defl', 'urutan_tampil', 'berlaku_mulai',
        'berlaku_sampai', 'keterangan', 'produk_jadi', 'punya_wip', 'punya_cbr',
        'punya_output_ikutan', 'metode_harga', 'wujud_produksi', 'satuan_produksi',
        'satuan_harga', 'faktor_konversi',
    ]
    k = Komoditas(
        kode_internal=kode, nama=nama, kategori_kode=kategori_kode, aktif=True,
        **{f: payload[f] for f in mdm_fields if f in payload},
    )
    db.add(k)
    db.flush()
    log_insert(db, 'komoditas', k.id, user_nama, alasan=payload.get('alasan'))
    db.commit()
    return _kom_to_dict(k)


@router.put('/{komoditas_id}', summary='Edit komoditas')
def update_komoditas(
    komoditas_id: int,
    payload: dict = Body(...),
    user_nama: str = Query('Admin'),
    db: Session = Depends(get_db),
):
    k = db.get(Komoditas, komoditas_id)
    if not k:
        raise HTTPException(404, f'Komoditas ID={komoditas_id} tidak ditemukan')

    alasan = payload.pop('alasan', None)
    berlaku_mulai_ubah = payload.pop('berlaku_mulai_ubah', None)

    # Cek kolom sensitif
    sensitive_changed = [c for c in SENSITIVE_COLS if c in payload]
    if sensitive_changed and not alasan:
        raise HTTPException(
            422,
            f'Kolom {sensitive_changed} termasuk sensitif. Wajib isi field "alasan".',
        )

    all_editable = [
        'nama', 'kategori_kode', 'satuan_produksi', 'satuan_harga', 'faktor_konversi',
        'wujud_produksi', 'aktif', 'klui_1990', 'kbli_2005', 'kbli_2009', 'kbki_2010',
        'identitas', 'pdrb_kbli_kode', 'pdrb_kbli_uraian', 'klui_uraian',
        'catatan_varietas', 'indeks_deflator', 'indeks_dbl_defl', 'urutan_tampil',
        'berlaku_mulai', 'berlaku_sampai', 'keterangan', 'produk_jadi',
        'punya_wip', 'punya_cbr', 'punya_output_ikutan', 'metode_harga',
    ]
    update_data = {col: payload[col] for col in all_editable if col in payload}
    changed = log_update_many(
        db, 'komoditas', k.id, k, update_data, user_nama, alasan,
        berlaku_mulai=berlaku_mulai_ubah,
    )
    for col, val in update_data.items():
        if hasattr(k, col):
            setattr(k, col, val)

    db.commit()

    # Jika faktor_konversi berubah, perlu cascade warning
    cascade_needed = 'faktor_konversi' in changed
    return {**_kom_to_dict(k), 'changed_columns': changed, 'cascade_needed': cascade_needed}


@router.post('/{komoditas_id}/nonaktifkan', summary='Nonaktifkan komoditas (soft delete)')
def nonaktifkan_komoditas(
    komoditas_id: int,
    alasan: str = Query(...),
    user_nama: str = Query('Admin'),
    db: Session = Depends(get_db),
):
    k = db.get(Komoditas, komoditas_id)
    if not k:
        raise HTTPException(404, f'Komoditas ID={komoditas_id} tidak ditemukan')
    k.aktif = False
    log_nonaktifkan(db, 'komoditas', k.id, user_nama, alasan)
    db.commit()
    return {'message': f'Komoditas {k.nama!r} dinonaktifkan', 'id': k.id}


@router.post('/import/preview', summary='Preview diff import Excel S0.CK')
async def preview_import(
    file: UploadFile = File(...),
    kategori_kode: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    try:
        from app.services.mdm_import_service import parse_excel_s0ck, diff_import
        content = await file.read()
        parsed = parse_excel_s0ck(content)
        diff = diff_import(db, parsed, kategori_kode)
        return {
            'total_excel': len(parsed),
            'unchanged':   len(diff['unchanged']),
            'changed':     len(diff['changed']),
            'new':         len(diff['new']),
            'missing_in_excel': len(diff['missing_in_excel']),
            'changed_detail': diff['changed'][:50],
            'new_detail':     diff['new'][:50],
            'missing_detail': diff['missing_in_excel'][:50],
        }
    except ImportError as e:
        raise HTTPException(500, str(e))
    except Exception as e:
        raise HTTPException(400, f'Gagal parse Excel: {e}')


@router.post('/import/apply', summary='Terapkan import Excel S0.CK')
async def apply_import(
    file: UploadFile = File(...),
    kategori_kode: Optional[str] = Query(None),
    apply_new: bool = Query(True),
    apply_changed: bool = Query(True),
    user_nama: str = Query('Admin'),
    db: Session = Depends(get_db),
):
    try:
        from app.services.mdm_import_service import parse_excel_s0ck, diff_import, apply_import as _apply
        content = await file.read()
        parsed = parse_excel_s0ck(content)
        diff = diff_import(db, parsed, kategori_kode)
        result = _apply(db, diff, user_nama, kategori_kode, apply_new, apply_changed)
        db.commit()
        return {
            'inserted': result['inserted'],
            'updated':  result['updated'],
            'errors':   result['errors'],
            'message':  f"Import selesai: +{result['inserted']} baru, ~{result['updated']} diperbarui",
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(500, f'Gagal apply import: {e}')
