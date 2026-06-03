"""
API Router — Master Data Komoditas
Sesuai spek: Grouping 4 level, Slot Lainnya, Inline Edit, Audit Trail.
"""
from __future__ import annotations

import re
from typing import Optional, Any
from fastapi import APIRouter, Body, Depends, HTTPException, Query, UploadFile, File
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.komoditas import Komoditas
from app.models.kategori_pdrb import KategoriPdrb
from app.models.master import AuditMaster
from app.services.mdm_audit_service import log_insert, log_update, log_update_many, log_nonaktifkan

router = APIRouter()

SENSITIVE_COLS = {'kbli_2009', 'kbli_2005', 'klui_1990', 'kbki_2010', 'faktor_konversi'}

def _kom_to_dict(k: Komoditas) -> dict:
    return {
        'id':               k.id,
        'kode_internal':    k.kode_internal,
        'nama':             k.nama,
        'kategori_kode':    k.kategori_kode,
        'wujud_produksi':   k.wujud_produksi,
        'satuan_produksi':  k.satuan_produksi,
        'satuan_harga':     k.satuan_harga or (f"Rp/{k.satuan_produksi}" if k.satuan_produksi else None),
        'indeks_deflator':  k.indeks_deflator,
        'indeks_dbl_defl':  k.indeks_dbl_defl,
        'klui_1990':        k.klui_1990,
        'kbli_2005':        k.kbli_2005,
        'kbli_2009':        k.kbli_2009,
        'kbki_2010':        k.kbki_2010,
        'identitas':        k.identitas,
        'pdrb_kbli_kode':   k.pdrb_kbli_kode,
        'pdrb_kbli_uraian': k.pdrb_kbli_uraian or (k.kategori.nama if k.kategori else None),
        'catatan_varietas': k.catatan_varietas,
        'faktor_konversi':  float(k.faktor_konversi) if k.faktor_konversi is not None else None,
        'punya_wip':        k.punya_wip,
        'punya_cbr':        k.punya_cbr,
        'punya_output_ikutan': k.punya_output_ikutan,
        'metode_harga':     k.metode_harga,
        'berlaku_mulai':    k.berlaku_mulai,
        'berlaku_sampai':   k.berlaku_sampai,
        'keterangan':       k.keterangan,
        'produk_jadi':      k.produk_jadi,
        'klui_uraian':      k.klui_uraian,
        'aktif':            k.aktif,
    }

@router.get('', summary='List komoditas dengan grouping hierarki')
def list_master_komoditas(
    q: Optional[str] = Query(None),
    kategori: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    kbli: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    # 1. Ambil semua kategori untuk struktur hierarki
    all_kategori = db.query(KategoriPdrb).order_by(KategoriPdrb.urutan).all()

    # 2. Ambil komoditas dengan filter
    kom_query = db.query(Komoditas)
    if q:
        kom_query = kom_query.filter(Komoditas.nama.ilike(f'%{q}%'))
    if kategori:
        kom_query = kom_query.filter(Komoditas.kategori_kode == kategori)
    if status == 'aktif':
        kom_query = kom_query.filter(Komoditas.aktif == True)
    elif status == 'nonaktif':
        kom_query = kom_query.filter(Komoditas.aktif == False)
    if kbli:
        kom_query = kom_query.filter(Komoditas.kbli_2009.ilike(f'%{kbli}%'))

    all_kom = kom_query.all()

    # Grouping komoditas by kategori_kode
    kom_by_kat = {}
    for k in all_kom:
        kom_by_kat.setdefault(k.kategori_kode, []).append(_kom_to_dict(k))

    # 3. Bangun hasil hierarkis
    result = []

    for kat in all_kategori:
        # Tentukan baris grup
        kat_item = {
            'type': 'group',
            'level': kat.level,
            'kode': kat.kode,
            'nama': kat.nama,
            'count_aktif': len([k for k in kom_by_kat.get(kat.kode, []) if k['aktif']]),
        }
        result.append(kat_item)

        # Jika level 3 (sub-subkategori), tampilkan komoditasnya
        if kat.level == 3:
            kom_list = kom_by_kat.get(kat.kode, [])
            # Sort by kode_internal
            kom_list.sort(key=lambda x: x['kode_internal'])
            result.extend([{**k, 'type': 'komoditas', 'level': 4} for k in kom_list])

            # Tambahkan "Slot Lainnya" jika tidak ada pencarian aktif yang membatasi
            if not q and not kbli:
                next_num = len(kom_list) + 1
                result.append({
                    'type': 'slot',
                    'level': 4,
                    'nama': f"Lainnya {kat.kode} ({next_num}) ...",
                    'kategori_kode': kat.kode,
                    'pdrb_kbli_uraian': kat.nama,
                    'aktif': False,
                })

    return result

@router.get('/{id}', summary='Detail satu komoditas')
def get_komoditas_detail(id: int, db: Session = Depends(get_db)):
    k = db.get(Komoditas, id)
    if not k:
        raise HTTPException(404, f'Komoditas ID={id} tidak ditemukan')
    return _kom_to_dict(k)

@router.put('/{id}', summary='Update full record komoditas')
def update_komoditas(
    id: int,
    payload: dict = Body(...),
    user_nama: str = Query('Admin'),
    db: Session = Depends(get_db),
):
    k = db.get(Komoditas, id)
    if not k:
        raise HTTPException(404, f'Komoditas ID={id} tidak ditemukan')

    alasan = payload.pop('alasan', None)
    berlaku_mulai_ubah = payload.pop('berlaku_mulai_ubah', None)

    changed = log_update_many(
        db, 'komoditas', k.id, k, payload, user_nama, alasan,
        berlaku_mulai=berlaku_mulai_ubah,
    )
    for col, val in payload.items():
        if hasattr(k, col):
            setattr(k, col, val)

    db.commit()
    return _kom_to_dict(k)

@router.patch('/{id}', summary='Update satu field (inline edit)')
def update_field(
    id: int,
    payload: dict = Body(...),
    user_nama: str = Query('Admin'),
    db: Session = Depends(get_db),
):
    k = db.get(Komoditas, id)
    if not k:
        raise HTTPException(404, f'Komoditas ID={id} tidak ditemukan')

    field = payload.get('field')
    value = payload.get('value')
    alasan = payload.get('alasan')
    berlaku_mulai = payload.get('berlaku_mulai')

    if not field or not hasattr(k, field):
        raise HTTPException(422, f"Field '{field}' tidak valid")

    # Validasi KBLI 2009 (5 digit)
    if field == 'kbli_2009' and value:
        if not re.match(r'^\d{5}$', str(value)):
            raise HTTPException(422, "KBLI 2009 harus berupa 5 digit angka")

    # Cek kolom sensitif
    if field in SENSITIVE_COLS and not alasan:
         raise HTTPException(422, f"Perubahan '{field}' wajib menyertakan alasan")

    nilai_lama = getattr(k, field)
    setattr(k, field, value)

    # Jika diisi dari slot (sebelumnya mungkin tidak aktif/belum ada), pastikan aktif
    if field == 'nama' and value and not k.aktif:
        k.aktif = True

    log_update(
        db, 'komoditas', k.id, field, nilai_lama, value,
        user_nama=user_nama, alasan=alasan, berlaku_mulai=berlaku_mulai
    )
    db.commit()
    return _kom_to_dict(k)

@router.post('', summary='Tambah komoditas baru', status_code=201)
def create_komoditas(
    payload: dict = Body(...),
    user_nama: str = Query('Admin'),
    db: Session = Depends(get_db),
):
    nama = payload.get('nama', '').strip()
    kategori_kode = payload.get('kategori_kode')

    if not nama or not kategori_kode:
        raise HTTPException(422, "Nama dan Kategori wajib diisi")

    # Generate kode internal: [kode_kategori].[3-digit-nomor]
    existing_count = db.query(func.count(Komoditas.id)).filter(Komoditas.kategori_kode == kategori_kode).scalar()
    new_num = existing_count + 1
    kode_internal = f"{kategori_kode}.{new_num:03d}"

    # Pastikan unik
    while db.query(Komoditas).filter(Komoditas.kode_internal == kode_internal).first():
        new_num += 1
        kode_internal = f"{kategori_kode}.{new_num:03d}"

    k = Komoditas(
        kode_internal=kode_internal,
        nama=nama,
        kategori_kode=kategori_kode,
        aktif=True,
        **{f: payload[f] for f in payload if hasattr(Komoditas, f) and f not in ['id', 'kode_internal']}
    )
    db.add(k)
    db.flush()
    log_insert(db, 'komoditas', k.id, user_nama, alasan=payload.get('alasan'))
    db.commit()
    return _kom_to_dict(k)

@router.delete('/{id}', summary='Soft delete komoditas')
def delete_komoditas(
    id: int,
    user_nama: str = Query('Admin'),
    db: Session = Depends(get_db),
):
    k = db.get(Komoditas, id)
    if not k:
        raise HTTPException(404, f'Komoditas ID={id} tidak ditemukan')

    k.aktif = False
    log_nonaktifkan(db, 'komoditas', k.id, user_nama)
    db.commit()
    return {'message': f'Komoditas {k.nama} dinonaktifkan'}

@router.get('/{id}/riwayat', summary='Audit trail perubahan')
def get_riwayat(id: int, db: Session = Depends(get_db)):
    rows = db.query(AuditMaster).filter(
        AuditMaster.tabel_nama == 'komoditas',
        AuditMaster.record_id == id
    ).order_by(AuditMaster.waktu.desc()).all()

    return [
        {
            'aksi': r.aksi,
            'kolom_ubah': r.kolom_ubah,
            'nilai_lama': r.nilai_lama,
            'nilai_baru': r.nilai_baru,
            'user_nama': r.user_nama,
            'waktu': r.waktu.isoformat(),
            'alasan': r.alasan,
            'berlaku_mulai': r.berlaku_mulai
        }
        for r in rows
    ]

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
            'changed_detail': diff['changed'],
            'new_detail':     diff['new'],
            'missing_detail': diff['missing_in_excel'],
        }
    except Exception as e:
        raise HTTPException(400, f'Gagal parse Excel: {e}')

@router.post('/import/apply', summary='Terapkan import Excel S0.CK')
async def apply_import(
    payload: dict = Body(...),
    user_nama: str = Query('Admin'),
    db: Session = Depends(get_db),
):
    try:
        from app.services.mdm_import_service import apply_import as _apply

        diff_result = payload.get('diff')
        apply_new = payload.get('apply_new', True)
        apply_changed = payload.get('apply_changed', True)
        kategori_kode = payload.get('kategori_kode')

        # Override log actions to 'IMPORT'
        # We need to modify mdm_import_service or pass aksi='IMPORT'
        # For now, let's assume we use a modified apply_import that accepts aksi

        # Actually mdm_import_service's apply_import calls log_insert/log_update.
        # We modified mdm_audit_service to accept 'aksi'.
        # We should update mdm_import_service.apply_import to use aksi='IMPORT'.

        result = _apply_master(db, diff_result, user_nama, kategori_kode, apply_new, apply_changed)
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

def _apply_master(db, diff_result, user_nama, kategori_kode_default, apply_new, apply_changed):
    from app.services.mdm_audit_service import log_insert, log_update
    inserted = 0
    updated = 0
    errors = []

    if apply_new:
        for item in diff_result.get('new', []):
            try:
                row = item['data']
                # Generate unique internal code
                k_kode = row.get('pdrb_kbli_kode') or kategori_kode_default or '1'
                existing_count = db.query(func.count(Komoditas.id)).filter(Komoditas.kategori_kode == k_kode).scalar()
                kode_internal = f"{k_kode}.{existing_count+1:03d}"
                while db.query(Komoditas).filter(Komoditas.kode_internal == kode_internal).first():
                    existing_count += 1
                    kode_internal = f"{k_kode}.{existing_count:03d}"

                kom = Komoditas(
                    kode_internal=kode_internal,
                    nama=row.get('nama'),
                    kategori_kode=k_kode,
                    aktif=True,
                    **{k: v for k, v in row.items() if k != 'nama' and hasattr(Komoditas, k)},
                )
                db.add(kom)
                db.flush()
                log_insert(db, 'komoditas', kom.id, user_nama, alasan='Import S0.CK', aksi='IMPORT')
                inserted += 1
            except Exception as e:
                errors.append(f"INSERT {item.get('key')}: {e}")

    if apply_changed:
        for item in diff_result.get('changed', []):
            try:
                kom = db.get(Komoditas, item['id'])
                if not kom: continue
                for diff in item['diffs']:
                    setattr(kom, diff['kolom'], diff['baru'])
                    log_update(db, 'komoditas', kom.id, diff['kolom'],
                               diff['lama'], diff['baru'], user_nama, alasan='Import S0.CK', aksi='IMPORT')
                updated += 1
            except Exception as e:
                errors.append(f"UPDATE {item.get('key')}: {e}")

    return {'inserted': inserted, 'updated': updated, 'errors': errors}
