"""API Router — Wilayah & Komoditas Hierarki."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.wilayah import Wilayah
from app.models.kategori_pdrb import KategoriPdrb
from app.models.komoditas import Komoditas
from app.schemas.harga import KategoriHierarki, KomoditasSimple

router = APIRouter()


@router.get("/wilayah", summary="Daftar wilayah Kalimantan Utara")
def get_wilayah(db: Session = Depends(get_db)):
    rows = db.query(Wilayah).order_by(Wilayah.kode).all()
    return [
        {"kode": w.kode, "nama": w.nama, "level": w.level, "parent_kode": w.parent_kode}
        for w in rows
    ]


@router.get("/komoditas/hierarki", summary="Pohon kategori + komoditas (nested JSON)")
def get_hierarki(db: Session = Depends(get_db)):
    """
    Kembalikan nested JSON:
    [
      { kode:'1', nama:'...', level:1, children:[
          { kode:'1.1', level:2, children:[
              { kode:'1.1.a', level:3, komoditas:[...] }
          ]}
      ]}
    ]
    """
    # Ambil semua kategori
    all_kat = (
        db.query(KategoriPdrb)
        .order_by(KategoriPdrb.urutan)
        .all()
    )
    # Ambil semua komoditas aktif
    all_kom = (
        db.query(Komoditas)
        .filter(Komoditas.aktif.is_(True))
        .order_by(Komoditas.nama)
        .all()
    )

    # Index komoditas per kategori_kode
    kom_by_kat: dict[str, list] = {}
    for k in all_kom:
        kom_by_kat.setdefault(k.kategori_kode, []).append({
            "id": k.id,
            "kode_internal": k.kode_internal,
            "nama": k.nama,
            "kategori_kode": k.kategori_kode,
            "satuan_produksi": k.satuan_produksi,
            "satuan_harga": k.satuan_harga,
            "wujud_produksi": k.wujud_produksi,
            "faktor_konversi": str(k.faktor_konversi) if k.faktor_konversi else None,
            "aktif": k.aktif,
        })

    # Build pohon
    kat_map: dict[str, dict] = {}
    for kat in all_kat:
        kat_map[kat.kode] = {
            "kode": kat.kode,
            "nama": kat.nama,
            "level": kat.level,
            "metode_adhb": kat.metode_adhb,
            "metode_adhk": kat.metode_adhk,
            "urutan": kat.urutan,
            "children": [],
            "komoditas": kom_by_kat.get(kat.kode, []),
        }

    roots = []
    for kat in all_kat:
        node = kat_map[kat.kode]
        if kat.parent_kode and kat.parent_kode in kat_map:
            kat_map[kat.parent_kode]["children"].append(node)
        elif not kat.parent_kode:
            roots.append(node)

    return roots


@router.get("/komoditas", summary="Daftar komoditas flat")
def get_komoditas_flat(
    kategori_kode: str | None = None,
    aktif: bool = True,
    db: Session = Depends(get_db),
):
    q = db.query(Komoditas).filter(Komoditas.aktif == aktif)
    if kategori_kode:
        q = q.filter(Komoditas.kategori_kode == kategori_kode)
    rows = q.order_by(Komoditas.nama).all()
    return [
        {
            "id": k.id, "kode_internal": k.kode_internal, "nama": k.nama,
            "kategori_kode": k.kategori_kode, "satuan_produksi": k.satuan_produksi,
            "satuan_harga": k.satuan_harga, "wujud_produksi": k.wujud_produksi,
            "faktor_konversi": str(k.faktor_konversi) if k.faktor_konversi else None,
        }
        for k in rows
    ]
