"""
API Router — MDM Audit Log
Subhalaman 7: Riwayat Perubahan Master
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.master import AuditMaster

router = APIRouter()


@router.get("", summary="List audit log master data")
def list_audit(
    tabel: Optional[str] = Query(None, description="Filter: komoditas|kategori_pdrb|rasio_referensi"),
    aksi: Optional[str] = Query(None, description="INSERT|UPDATE|DELETE|NONAKTIFKAN"),
    user_nama: Optional[str] = Query(None),
    q: Optional[str] = Query(None, description="Cari di kolom/nilai"),
    dari: Optional[str] = Query(None, description="Tanggal mulai YYYY-MM-DD"),
    sampai: Optional[str] = Query(None, description="Tanggal akhir YYYY-MM-DD"),
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    query = db.query(AuditMaster)

    if tabel:
        query = query.filter(AuditMaster.tabel_nama == tabel)
    if aksi:
        query = query.filter(AuditMaster.aksi == aksi)
    if user_nama:
        query = query.filter(AuditMaster.user_nama.ilike(f"%{user_nama}%"))
    if q:
        from sqlalchemy import or_
        query = query.filter(or_(
            AuditMaster.kolom_ubah.ilike(f"%{q}%"),
            AuditMaster.nilai_lama.ilike(f"%{q}%"),
            AuditMaster.nilai_baru.ilike(f"%{q}%"),
            AuditMaster.alasan.ilike(f"%{q}%"),
        ))
    if dari:
        try:
            query = query.filter(AuditMaster.waktu >= datetime.fromisoformat(dari))
        except ValueError:
            pass
    if sampai:
        try:
            query = query.filter(AuditMaster.waktu <= datetime.fromisoformat(sampai + 'T23:59:59'))
        except ValueError:
            pass

    total = query.count()
    rows = query.order_by(AuditMaster.waktu.desc()).offset((page - 1) * per_page).limit(per_page).all()

    return {
        "total": total,
        "page": page,
        "per_page": per_page,
        "rows": [
            {
                "id":          r.id,
                "tabel_nama":  r.tabel_nama,
                "record_id":   r.record_id,
                "aksi":        r.aksi,
                "kolom_ubah":  r.kolom_ubah,
                "nilai_lama":  r.nilai_lama,
                "nilai_baru":  r.nilai_baru,
                "user_nama":   r.user_nama,
                "waktu":       r.waktu.isoformat() if r.waktu else None,
                "alasan":      r.alasan,
                "berlaku_mulai": r.berlaku_mulai,
            }
            for r in rows
        ],
    }


@router.get("/record/{tabel}/{record_id}", summary="Riwayat perubahan satu record")
def get_record_audit(
    tabel: str,
    record_id: int,
    db: Session = Depends(get_db),
):
    rows = (
        db.query(AuditMaster)
        .filter(AuditMaster.tabel_nama == tabel, AuditMaster.record_id == record_id)
        .order_by(AuditMaster.waktu.desc())
        .all()
    )
    return [
        {
            "aksi":       r.aksi,
            "kolom_ubah": r.kolom_ubah,
            "nilai_lama": r.nilai_lama,
            "nilai_baru": r.nilai_baru,
            "user_nama":  r.user_nama,
            "waktu":      r.waktu.isoformat() if r.waktu else None,
            "alasan":     r.alasan,
        }
        for r in rows
    ]


@router.get("/export", summary="Export audit log ke CSV")
def export_audit(
    tabel: Optional[str] = Query(None),
    dari: Optional[str] = Query(None),
    sampai: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    import csv
    import io as _io

    query = db.query(AuditMaster)
    if tabel:
        query = query.filter(AuditMaster.tabel_nama == tabel)
    if dari:
        try:
            query = query.filter(AuditMaster.waktu >= datetime.fromisoformat(dari))
        except ValueError:
            pass
    if sampai:
        try:
            query = query.filter(AuditMaster.waktu <= datetime.fromisoformat(sampai + 'T23:59:59'))
        except ValueError:
            pass

    rows = query.order_by(AuditMaster.waktu.desc()).all()

    output = _io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Waktu', 'Tabel', 'Record ID', 'Aksi', 'Kolom', 'Nilai Lama', 'Nilai Baru', 'User', 'Alasan', 'Berlaku Mulai'])
    for r in rows:
        writer.writerow([
            r.waktu.isoformat() if r.waktu else '',
            r.tabel_nama, r.record_id, r.aksi,
            r.kolom_ubah or '', r.nilai_lama or '', r.nilai_baru or '',
            r.user_nama or '', r.alasan or '', r.berlaku_mulai or '',
        ])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type='text/csv',
        headers={'Content-Disposition': 'attachment; filename="audit_master.csv"'},
    )
