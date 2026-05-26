"""
API Router — S3 Tabel Pokok & Dashboard Ringkasan PDRB

Endpoints:
  GET /api/s3/tabel-pokok              → 6 tabel BPS (ADHB, ADHK, Distribusi, Laju, Indeks, Laju Imp)
  GET /api/s3/dashboard/kpi            → 4 KPI cards
  GET /api/s3/dashboard/tren           → Line chart ADHB vs ADHK per tahun
  GET /api/s3/dashboard/distribusi     → Donut chart distribusi 17 kategori
  GET /api/s3/dashboard/laju-kategori  → Bar chart laju pertumbuhan per kategori
  GET /api/s3/dashboard/triwulanan     → Tabel ringkasan triwulanan
  GET /api/s3/dashboard/kelengkapan    → Progress kelengkapan data per wilayah
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.hasil import LkHasil, PdrbRekap
from app.models.kategori_pdrb import KategoriPdrb
from app.models.komoditas import Komoditas
from app.models.wilayah import Wilayah

router = APIRouter()
TAHUN_MIN = 2008


def _f(val) -> Optional[float]:
    """Decimal/None → float."""
    return float(val) if val is not None else None


def _tahun_range(db: Session, wilayah_kode: str) -> tuple[int, int]:
    """Deteksi min/max tahun dari pdrb_rekap untuk wilayah ini."""
    r = (
        db.query(func.min(PdrbRekap.tahun), func.max(PdrbRekap.tahun))
        .filter(PdrbRekap.wilayah_kode == wilayah_kode, PdrbRekap.triwulan.is_(None))
        .first()
    )
    lo = r[0] if r and r[0] else TAHUN_MIN
    hi = r[1] if r and r[1] else TAHUN_MIN
    return lo, hi


def _level1_kodes(db: Session) -> list[str]:
    return [
        r[0]
        for r in db.query(KategoriPdrb.kode)
        .filter(KategoriPdrb.level == 1)
        .order_by(KategoriPdrb.urutan)
        .all()
    ]


# ─── /api/s3/tabel-pokok ──────────────────────────────────────────────────────

@router.get("/tabel-pokok", summary="6 Tabel Pokok PDRB BPS (ADHB/ADHK/Distribusi/Laju/Indeks/Laju Imp)")
def get_tabel_pokok(
    wilayah_kode: str = Query("65"),
    tahun_awal: int = Query(2008, ge=2008),
    tahun_akhir: Optional[int] = Query(None),
    db: Session = Depends(get_db),
):
    """
    Kembalikan 6 tabel pokok BPS untuk range tahun terpilih.
    Sumber: pdrb_rekap WHERE triwulan IS NULL.
    PDRB Total = SUM NTB 17 kategori level-1.
    """
    if tahun_akhir is None:
        _, tahun_akhir = _tahun_range(db, wilayah_kode)
        tahun_akhir = max(tahun_akhir, tahun_awal)

    tahun_list = list(range(tahun_awal, tahun_akhir + 1))

    # Semua kategori level 1–3
    all_kat = (
        db.query(KategoriPdrb)
        .filter(KategoriPdrb.level <= 3)
        .order_by(KategoriPdrb.urutan)
        .all()
    )
    l1_kodes = [k.kode for k in all_kat if k.level == 1]

    # Bulk fetch rekap tahunan
    rekap_rows = (
        db.query(PdrbRekap)
        .filter(
            PdrbRekap.wilayah_kode == wilayah_kode,
            PdrbRekap.tahun.between(tahun_awal, tahun_akhir),
            PdrbRekap.triwulan.is_(None),
        )
        .all()
    )
    # Index: [kategori_kode][tahun]
    rmap: dict[str, dict[int, PdrbRekap]] = {}
    for r in rekap_rows:
        rmap.setdefault(r.kategori_kode, {})[r.tahun] = r

    # Hitung TOTAL per tahun (sum level-1)
    tot_adhb: dict[int, Optional[float]] = {}
    tot_adhk: dict[int, Optional[float]] = {}
    tot_indeks: dict[int, Optional[float]] = {}
    for t in tahun_list:
        sb = sum(_f(rmap.get(k, {}).get(t, None) and rmap[k][t].ntb_adhb) or 0 for k in l1_kodes)
        sk = sum(_f(rmap.get(k, {}).get(t, None) and rmap[k][t].ntb_adhk) or 0 for k in l1_kodes)
        tot_adhb[t] = sb if sb > 0 else None
        tot_adhk[t] = sk if sk > 0 else None
        tot_indeks[t] = round((sb / sk) * 100, 4) if sk > 0 else None

    # Laju total ADHK YoY
    tot_laju: dict[int, Optional[float]] = {tahun_awal: None}
    for t in tahun_list[1:]:
        c, p = tot_adhk.get(t), tot_adhk.get(t - 1)
        tot_laju[t] = round(((c / p) - 1) * 100, 4) if c and p and p > 0 else None

    # Laju implisit total YoY
    tot_laju_imp: dict[int, Optional[float]] = {tahun_awal: None}
    for t in tahun_list[1:]:
        c, p = tot_indeks.get(t), tot_indeks.get(t - 1)
        tot_laju_imp[t] = round(((c / p) - 1) * 100, 4) if c and p and p > 0 else None

    def build_field(field: str) -> dict:
        out = {}
        for kat in all_kat:
            out[kat.kode] = {
                t: _f(getattr(rmap.get(kat.kode, {}).get(t), field, None))
                for t in tahun_list
            }
        return out

    # Kolom pertama = None untuk laju (tidak ada basis)
    laju_data = build_field("laju_pertumbuhan_pct")
    laju_imp_data = build_field("laju_implisit_pct")
    for kode in laju_data:
        laju_data[kode][tahun_awal] = None
    for kode in laju_imp_data:
        laju_imp_data[kode][tahun_awal] = None

    return {
        "wilayah_kode":  wilayah_kode,
        "tahun_list":    tahun_list,
        "kategori": [
            {
                "kode":        k.kode,
                "nama":        k.nama,
                "level":       k.level,
                "parent_kode": k.parent_kode,
                "urutan":      k.urutan,
                "kode_singkat": k.kode_singkat if k.level == 1 else None,
            }
            for k in all_kat
        ],
        "tabel": {
            "ntb_adhb":             build_field("ntb_adhb"),
            "ntb_adhk":             build_field("ntb_adhk"),
            "distribusi_pct":       build_field("distribusi_pct"),
            "laju_pertumbuhan_pct": laju_data,
            "indeks_implisit":      build_field("indeks_implisit"),
            "laju_implisit_pct":    laju_imp_data,
        },
        "total": {
            "ntb_adhb":             {str(t): tot_adhb[t] for t in tahun_list},
            "ntb_adhk":             {str(t): tot_adhk[t] for t in tahun_list},
            "indeks_implisit":      {str(t): tot_indeks[t] for t in tahun_list},
            "laju_pertumbuhan_pct": {str(t): tot_laju[t] for t in tahun_list},
            "laju_implisit_pct":    {str(t): tot_laju_imp[t] for t in tahun_list},
        },
    }


# ─── /api/s3/dashboard/kpi ────────────────────────────────────────────────────

@router.get("/dashboard/kpi", summary="4 KPI cards untuk Dashboard Ringkasan")
def get_kpi(
    wilayah_kode: str = Query("65"),
    tahun: Optional[int] = Query(None),
    db: Session = Depends(get_db),
):
    if tahun is None:
        _, tahun = _tahun_range(db, wilayah_kode)

    l1 = _level1_kodes(db)

    def total_adhb_adhk(t: int):
        rows = (
            db.query(PdrbRekap.ntb_adhb, PdrbRekap.ntb_adhk)
            .filter(
                PdrbRekap.kategori_kode.in_(l1),
                PdrbRekap.wilayah_kode == wilayah_kode,
                PdrbRekap.tahun == t,
                PdrbRekap.triwulan.is_(None),
            )
            .all()
        )
        adhb = sum(float(r[0]) for r in rows if r[0]) or None
        adhk = sum(float(r[1]) for r in rows if r[1]) or None
        return adhb, adhk

    adhb_now, adhk_now = total_adhb_adhk(tahun)
    adhb_prev, adhk_prev = total_adhb_adhk(tahun - 1)

    def pct_delta(c, p):
        return round(((c / p) - 1) * 100, 2) if c and p and p > 0 else None

    # Distribusi terbesar
    max_dist_row = (
        db.query(PdrbRekap.kategori_kode, PdrbRekap.distribusi_pct)
        .filter(
            PdrbRekap.kategori_kode.in_(l1),
            PdrbRekap.wilayah_kode == wilayah_kode,
            PdrbRekap.tahun == tahun,
            PdrbRekap.triwulan.is_(None),
            PdrbRekap.distribusi_pct.is_not(None),
        )
        .order_by(PdrbRekap.distribusi_pct.desc())
        .first()
    )
    dist_nama, dist_pct, dist_delta = None, None, None
    if max_dist_row:
        dist_pct = _f(max_dist_row[1])
        kat = db.query(KategoriPdrb).filter(KategoriPdrb.kode == max_dist_row[0]).first()
        dist_nama = kat.nama if kat else max_dist_row[0]
        prev = (
            db.query(PdrbRekap.distribusi_pct)
            .filter(
                PdrbRekap.kategori_kode == max_dist_row[0],
                PdrbRekap.wilayah_kode == wilayah_kode,
                PdrbRekap.tahun == tahun - 1,
                PdrbRekap.triwulan.is_(None),
            )
            .scalar()
        )
        if dist_pct and prev:
            dist_delta = round(dist_pct - float(prev), 2)

    return {
        "tahun":        tahun,
        "wilayah_kode": wilayah_kode,
        "pdrb_adhb": {
            "nilai": adhb_now, "delta_pct": pct_delta(adhb_now, adhb_prev),
        },
        "pdrb_adhk": {
            "nilai": adhk_now, "delta_pct": pct_delta(adhk_now, adhk_prev),
        },
        "laju_pertumbuhan": {
            "nilai": pct_delta(adhk_now, adhk_prev),
        },
        "distribusi_terbesar": {
            "kategori_nama": dist_nama,
            "nilai_pct":     dist_pct,
            "delta_pct":     dist_delta,
        },
    }


# ─── /api/s3/dashboard/tren ───────────────────────────────────────────────────

@router.get("/dashboard/tren", summary="Tren PDRB ADHB vs ADHK per tahun (line chart)")
def get_tren(
    wilayah_kode: str = Query("65"),
    db: Session = Depends(get_db),
):
    l1 = _level1_kodes(db)
    rows = (
        db.query(
            PdrbRekap.tahun,
            func.sum(PdrbRekap.ntb_adhb).label("adhb"),
            func.sum(PdrbRekap.ntb_adhk).label("adhk"),
        )
        .filter(
            PdrbRekap.kategori_kode.in_(l1),
            PdrbRekap.wilayah_kode == wilayah_kode,
            PdrbRekap.triwulan.is_(None),
        )
        .group_by(PdrbRekap.tahun)
        .order_by(PdrbRekap.tahun)
        .all()
    )
    data, prev_adhk = [], None
    for r in rows:
        adhk = _f(r.adhk)
        laju = round(((adhk / prev_adhk) - 1) * 100, 2) if adhk and prev_adhk and prev_adhk > 0 else None
        data.append({"tahun": r.tahun, "ntb_adhb": _f(r.adhb), "ntb_adhk": adhk, "laju": laju})
        prev_adhk = adhk
    return {"wilayah_kode": wilayah_kode, "data": data}


# ─── /api/s3/dashboard/distribusi ────────────────────────────────────────────

@router.get("/dashboard/distribusi", summary="Distribusi % 17 kategori (donut chart)")
def get_distribusi(
    wilayah_kode: str = Query("65"),
    tahun: Optional[int] = Query(None),
    db: Session = Depends(get_db),
):
    if tahun is None:
        _, tahun = _tahun_range(db, wilayah_kode)
    rows = (
        db.query(PdrbRekap, KategoriPdrb)
        .join(KategoriPdrb, PdrbRekap.kategori_kode == KategoriPdrb.kode)
        .filter(
            KategoriPdrb.level == 1,
            PdrbRekap.wilayah_kode == wilayah_kode,
            PdrbRekap.tahun == tahun,
            PdrbRekap.triwulan.is_(None),
        )
        .order_by(KategoriPdrb.urutan)
        .all()
    )
    return {
        "wilayah_kode": wilayah_kode,
        "tahun": tahun,
        "data": [
            {
                "kategori_kode":  kat.kode,
                "kategori_nama":  kat.nama,
                "kode_singkat":   kat.kode_singkat,
                "distribusi_pct": _f(rekap.distribusi_pct),
                "ntb_adhb":       _f(rekap.ntb_adhb),
                "ntb_adhk":       _f(rekap.ntb_adhk),
            }
            for rekap, kat in rows
        ],
    }


# ─── /api/s3/dashboard/laju-kategori ─────────────────────────────────────────

@router.get("/dashboard/laju-kategori", summary="Laju pertumbuhan per kategori (bar chart)")
def get_laju_kategori(
    wilayah_kode: str = Query("65"),
    tahun: Optional[int] = Query(None),
    db: Session = Depends(get_db),
):
    if tahun is None:
        _, tahun = _tahun_range(db, wilayah_kode)
    rows = (
        db.query(PdrbRekap, KategoriPdrb)
        .join(KategoriPdrb, PdrbRekap.kategori_kode == KategoriPdrb.kode)
        .filter(
            KategoriPdrb.level == 1,
            PdrbRekap.wilayah_kode == wilayah_kode,
            PdrbRekap.tahun == tahun,
            PdrbRekap.triwulan.is_(None),
        )
        .order_by(PdrbRekap.laju_pertumbuhan_pct.desc().nullslast())
        .all()
    )
    return {
        "wilayah_kode": wilayah_kode,
        "tahun": tahun,
        "data": [
            {
                "kategori_kode":        kat.kode,
                "kategori_nama":        kat.nama,
                "kode_singkat":         kat.kode_singkat,
                "laju_pertumbuhan_pct": _f(rekap.laju_pertumbuhan_pct),
                "ntb_adhk":             _f(rekap.ntb_adhk),
            }
            for rekap, kat in rows
        ],
    }


# ─── /api/s3/dashboard/triwulanan ────────────────────────────────────────────

@router.get("/dashboard/triwulanan", summary="Rekap triwulanan ADHK per kategori")
def get_triwulanan(
    wilayah_kode: str = Query("65"),
    tahun: Optional[int] = Query(None),
    db: Session = Depends(get_db),
):
    if tahun is None:
        _, tahun = _tahun_range(db, wilayah_kode)

    l1_kat = (
        db.query(KategoriPdrb)
        .filter(KategoriPdrb.level == 1)
        .order_by(KategoriPdrb.urutan)
        .all()
    )
    l1_kodes = [k.kode for k in l1_kat]

    rekap_all = (
        db.query(PdrbRekap)
        .filter(
            PdrbRekap.kategori_kode.in_(l1_kodes),
            PdrbRekap.wilayah_kode == wilayah_kode,
            PdrbRekap.tahun == tahun,
        )
        .all()
    )
    # Index [kode][triwulan|None]
    idx: dict[str, dict] = {}
    for r in rekap_all:
        idx.setdefault(r.kategori_kode, {})[r.triwulan] = r

    rows = []
    for kat in l1_kat:
        d = idx.get(kat.kode, {})
        tah = d.get(None)
        rows.append({
            "kategori_kode":        kat.kode,
            "kategori_nama":        kat.nama,
            "kode_singkat":         kat.kode_singkat,
            "tw1_adhk":             _f(d[1].ntb_adhk) if 1 in d else None,
            "tw2_adhk":             _f(d[2].ntb_adhk) if 2 in d else None,
            "tw3_adhk":             _f(d[3].ntb_adhk) if 3 in d else None,
            "tw4_adhk":             _f(d[4].ntb_adhk) if 4 in d else None,
            "tahunan_adhk":         _f(tah.ntb_adhk) if tah else None,
            "laju_pertumbuhan_pct": _f(tah.laju_pertumbuhan_pct) if tah else None,
        })

    def s(col):
        vs = [r[col] for r in rows if r[col] is not None]
        return sum(vs) if vs else None

    return {
        "wilayah_kode": wilayah_kode,
        "tahun": tahun,
        "rows": rows,
        "total": {
            "kategori_kode": "TOTAL", "kategori_nama": "PDRB",
            "tw1_adhk": s("tw1_adhk"), "tw2_adhk": s("tw2_adhk"),
            "tw3_adhk": s("tw3_adhk"), "tw4_adhk": s("tw4_adhk"),
            "tahunan_adhk": s("tahunan_adhk"), "laju_pertumbuhan_pct": None,
        },
    }


# ─── /api/s3/dashboard/kelengkapan ───────────────────────────────────────────

@router.get("/dashboard/kelengkapan", summary="Progress kelengkapan data input per wilayah (%)")
def get_kelengkapan(
    tahun: Optional[int] = Query(None),
    db: Session = Depends(get_db),
):
    if tahun is None:
        tahun = db.query(func.max(PdrbRekap.tahun)).filter(PdrbRekap.triwulan.is_(None)).scalar() or TAHUN_MIN

    wilayah_list = (
        db.query(Wilayah)
        .filter(Wilayah.level.in_(["kabupaten", "kota"]))
        .order_by(Wilayah.nama)
        .all()
    )
    total_kom = db.query(func.count(Komoditas.id)).filter(Komoditas.aktif.is_(True)).scalar() or 0

    hasil = []
    for w in wilayah_list:
        terisi = 0
        if total_kom > 0:
            terisi = (
                db.query(func.count(func.distinct(LkHasil.komoditas_id)))
                .filter(
                    LkHasil.wilayah_kode == w.kode,
                    LkHasil.tahun == tahun,
                    LkHasil.triwulan.is_(None),
                    LkHasil.ntb_adhb.is_not(None),
                    LkHasil.is_valid.is_(True),
                )
                .scalar() or 0
            )
        pct = round((terisi / total_kom) * 100, 1) if total_kom > 0 else 0.0
        hasil.append({
            "wilayah_kode":   w.kode,
            "wilayah_nama":   w.nama,
            "level":          w.level,
            "total_komoditas": total_kom,
            "terisi":         terisi,
            "pct":            pct,
            "lengkap":        pct >= 100.0,
        })

    return {"tahun": tahun, "wilayah": hasil}
