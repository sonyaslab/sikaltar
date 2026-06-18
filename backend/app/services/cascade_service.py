"""
Service: CascadeService  (VERSI DIPERBAIKI)
Recalculation cascade: komoditas → subkategori → kategori → PDRB total.

PERUBAHAN UTAMA vs versi lama (cari penanda  # [FIX] ):
  [FIX-1a] Scope recalculation kini berbasis "kategori DAUN" (tidak punya child),
           sehingga kategori level-1 yang tidak punya subkategori (mis. 5, 6, 10,
           12, 13, 14, 15, 16, 17) IKUT terhitung. Versi lama hanya mengambil
           level>=3 / level==2, jadi kategori-kategori itu tidak pernah dihitung.
  [FIX-1b] Step 2 sekarang MEMILIH metode (dispatch) berdasarkan ada/tidaknya
           komoditas + kolom metode kategori:
              - ada komoditas              → hitung_subkategori (Produksi/Revaluasi)
              - metode 'Langsung'          → pertahankan NTB yang diinput langsung
              - selain itu                 → hitung_kategori_deflasi (Deflasi)
           Versi lama selalu memakai hitung_subkategori untuk semua kategori,
           sehingga ~12 kategori jasa tidak pernah terisi.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Literal, Optional

from sqlalchemy.orm import Session

from app.models.hasil import LkHasil, PdrbRekap
from app.models.komoditas import Komoditas
from app.models.kategori_pdrb import KategoriPdrb
from app.services.kalkulasi_service import (
    hitung_output_komoditas,
    hitung_subkategori,
    hitung_kategori_deflasi,
    simpan_lk_hasil,
)
from app.services.agregasi_service import (
    agregasi_tahunan,
    simpan_rekap_dari_hasil,
    hitung_indikator_turunan,
)

logger = logging.getLogger(__name__)

TriggerType = Literal["produksi", "harga", "deflator", "rasio_override", "ihp", "adjustment"]

KODE_PROVINSI = "65"
KODE_KABKOTA = ["6501", "6502", "6503", "6504", "6571"]

# [FIX-1b] Metode yang berbasis komoditas (produksi)
METODE_PRODUKSI = {"PRODUKSI", "REVALUASI"}
METODE_LANGSUNG = {"LANGSUNG", "PENDAPATAN", "PENGELUARAN"}  # NTB diinput langsung


@dataclass
class CascadeResult:
    trigger_type: str
    wilayah_kode: str
    tahun: int
    triwulan: Optional[int]
    komoditas_affected: list
    subkategori_affected: list
    kategori_affected: list
    started_at: datetime
    finished_at: Optional[datetime] = None
    errors: list = None
    warnings: list = None

    def __post_init__(self):
        if self.errors is None:
            self.errors = []
        if self.warnings is None:
            self.warnings = []

    @property
    def duration_seconds(self) -> Optional[float]:
        if self.finished_at:
            return (self.finished_at - self.started_at).total_seconds()
        return None


# ─────────────────────────────────────────────────────────────────────────────
# Helper hierarki
# ─────────────────────────────────────────────────────────────────────────────

def _get_kategori_kode(db: Session, komoditas_id: int) -> Optional[str]:
    kom = db.get(Komoditas, komoditas_id)
    return kom.kategori_kode if kom else None


def _get_parent_kode(kategori_kode: str) -> Optional[str]:
    parts = kategori_kode.split(".")
    if len(parts) <= 1:
        return None
    return ".".join(parts[:-1])


def _collect_ancestor_kodes(kategori_kode: str) -> list:
    ancestors = []
    parent = _get_parent_kode(kategori_kode)
    while parent:
        ancestors.append(parent)
        parent = _get_parent_kode(parent)
    return ancestors


def _semua_kode_set(db: Session) -> set:
    return {kode for (kode,) in db.query(KategoriPdrb.kode).all()}


def _kode_daun(db: Session) -> set:
    """
    [FIX-1a] Kategori DAUN = kode yang TIDAK menjadi parent bagi kode lain.
    Inilah titik di mana NTB dihitung (lalu di-roll-up ke atas).
    """
    semua = _semua_kode_set(db)
    parent_kodes = {
        p for (p,) in db.query(KategoriPdrb.parent_kode)
        .filter(KategoriPdrb.parent_kode.is_not(None)).distinct().all()
    }
    return {k for k in semua if k not in parent_kodes}


def _resolve_metode(db: Session, kategori_kode: str) -> str:
    kat = db.query(KategoriPdrb).filter(KategoriPdrb.kode == kategori_kode).first()
    if not kat:
        return ""
    metode = (kat.metode_adhk or kat.metode_adhb or "").strip().upper()
    return metode


def _punya_komoditas(db: Session, kategori_kode: str) -> bool:
    return (
        db.query(Komoditas)
        .filter(Komoditas.kategori_kode == kategori_kode, Komoditas.aktif.is_(True))
        .count() > 0
    )


def _invalidate_pdrb_rekap_indikator(
    db: Session, kategori_kode: str, wilayah_kode: str, tahun: int, triwulan: Optional[int]
) -> None:
    """Reset HANYA indikator turunan (nilai pokok & output ADHB input dipertahankan)."""
    rows = (
        db.query(PdrbRekap)
        .filter(
            PdrbRekap.kategori_kode == kategori_kode,
            PdrbRekap.wilayah_kode == wilayah_kode,
            PdrbRekap.tahun == tahun,
            PdrbRekap.triwulan == triwulan,
        )
        .all()
    )
    for row in rows:
        row.distribusi_pct = None
        row.laju_pertumbuhan_pct = None
        row.indeks_implisit = None
        row.laju_implisit_pct = None
    db.flush()


# ─────────────────────────────────────────────────────────────────────────────
# Recalculation utama
# ─────────────────────────────────────────────────────────────────────────────

def sync_recalculate(
    db: Session,
    trigger_type: TriggerType,
    wilayah_kode: str,
    tahun: int,
    triwulan: Optional[int] = None,
    komoditas_id: Optional[int] = None,
    kategori_kode_scope: Optional[str] = None,
) -> CascadeResult:
    result = CascadeResult(
        trigger_type=trigger_type, wilayah_kode=wilayah_kode, tahun=tahun,
        triwulan=triwulan, komoditas_affected=[], subkategori_affected=[],
        kategori_affected=[], started_at=datetime.now(),
    )

    logger.info(
        f"[CASCADE] Mulai: trigger={trigger_type}, wilayah={wilayah_kode}, "
        f"tahun={tahun}, tw={triwulan}, komoditas={komoditas_id}"
    )

    # ── Tentukan kategori DAUN yang akan dihitung ─────────────────────────
    if komoditas_id:
        subkat = _get_kategori_kode(db, komoditas_id)
        if not subkat:
            result.errors.append(f"Komoditas ID={komoditas_id} tidak ditemukan")
            result.finished_at = datetime.now()
            return result
        daun_to_recalc = {subkat}
    elif kategori_kode_scope:
        # Daun di bawah scope (atau scope itu sendiri jika ia daun)
        semua_daun = _kode_daun(db)
        daun_to_recalc = {
            k for k in semua_daun
            if k == kategori_kode_scope or k.startswith(kategori_kode_scope + ".")
        }
        if not daun_to_recalc:
            daun_to_recalc = {kategori_kode_scope}
    else:
        daun_to_recalc = _kode_daun(db)   # [FIX-1a] semua daun, termasuk level-1

    # ── Step 1: Recalculate komoditas (untuk daun berbasis produksi) ──────
    for daun in daun_to_recalc:
        if not _punya_komoditas(db, daun):
            continue
        komoditas_list = (
            db.query(Komoditas)
            .filter(Komoditas.kategori_kode == daun, Komoditas.aktif.is_(True))
            .all()
        )
        for kom in komoditas_list:
            if komoditas_id and kom.id != komoditas_id:
                continue
            h = hitung_output_komoditas(db, kom.id, wilayah_kode, tahun, triwulan)
            if h.error:
                result.warnings.append(h.error)
                continue
            simpan_lk_hasil(db, kom.id, wilayah_kode, tahun, triwulan, h, flush=False)
            result.komoditas_affected.append(kom.id)
    db.flush()

    # ── Step 2: Recalculate tiap daun dengan DISPATCH METODE ──────────────
    for daun in daun_to_recalc:
        _invalidate_pdrb_rekap_indikator(db, daun, wilayah_kode, tahun, triwulan)
        metode = _resolve_metode(db, daun)

        if _punya_komoditas(db, daun):
            # Produksi/Revaluasi — berbasis komoditas
            h_sub = hitung_subkategori(db, daun, wilayah_kode, tahun, triwulan)
            for w in h_sub.peringatan:
                result.warnings.append(w)
            simpan_rekap_dari_hasil(db, h_sub, flush=False)

        elif metode in METODE_LANGSUNG:
            # [FIX-1b] NTB diinput langsung → biarkan apa adanya di pdrb_rekap.
            exists = (
                db.query(PdrbRekap)
                .filter(
                    PdrbRekap.kategori_kode == daun,
                    PdrbRekap.wilayah_kode == wilayah_kode,
                    PdrbRekap.tahun == tahun,
                    PdrbRekap.triwulan == triwulan,
                )
                .first()
            )
            if not exists:
                result.warnings.append(
                    f"[Langsung] NTB belum diinput untuk {daun!r} {tahun} "
                    f"(isi pdrb_rekap.ntb_adhb/ntb_adhk)"
                )

        else:
            # Deflasi / DoubleDflasi / CommodityFlow → metode deflasi tunggal
            h_def = hitung_kategori_deflasi(db, daun, wilayah_kode, tahun, triwulan)
            for w in h_def.peringatan:
                result.warnings.append(w)
            simpan_rekap_dari_hasil(db, h_def, flush=False)

        result.subkategori_affected.append(daun)
    db.flush()

    # ── Step 3: Roll-up ke semua ancestor ─────────────────────────────────
    parent_kodes: set = set()
    for daun in daun_to_recalc:
        for anc in _collect_ancestor_kodes(daun):
            parent_kodes.add(anc)

    for parent_kode in sorted(parent_kodes, key=lambda x: x.count("."), reverse=True):
        children = (
            db.query(KategoriPdrb.kode)
            .filter(KategoriPdrb.parent_kode == parent_kode)
            .all()
        )
        child_kodes = [k for (k,) in children]
        total_b = _sum_komponen_children(db, child_kodes, wilayah_kode, tahun, triwulan, "adhb")
        total_k = _sum_komponen_children(db, child_kodes, wilayah_kode, tahun, triwulan, "adhk")
        _save_parent_rekap(db, parent_kode, wilayah_kode, tahun, triwulan, total_b, total_k)
        result.kategori_affected.append(parent_kode)
    db.flush()

    # ── Step 4: Indikator turunan (semua daun + parent) ───────────────────
    all_affected = list(daun_to_recalc) + list(parent_kodes)
    for kode in all_affected:
        hitung_indikator_turunan(db, kode, wilayah_kode, tahun, triwulan)

    # ── Step 5: Agregasi tahunan bila triwulanan ──────────────────────────
    if triwulan is not None:
        for kode in all_affected:
            agregasi_tahunan(db, kode, wilayah_kode, tahun)

    # ── Step 6: Roll-up provinsi (65) dari kab/kota ───────────────────────
    if wilayah_kode != KODE_PROVINSI:
        _recalculate_provinsi_agregat(db, tahun, triwulan, parent_kodes | daun_to_recalc)

    db.commit()
    result.finished_at = datetime.now()
    logger.info(
        f"[CASCADE] Selesai {result.duration_seconds:.2f}s. "
        f"Komoditas={len(result.komoditas_affected)}, "
        f"Daun={len(result.subkategori_affected)}, Parent={len(result.kategori_affected)}"
    )
    return result


def _sum_komponen_children(
    db: Session, child_kodes: list, wilayah_kode: str,
    tahun: int, triwulan: Optional[int], mode: str,
) -> dict:
    from decimal import Decimal as D
    totals = {
        "output_primer": D(0), "output_sekunder": D(0), "output_lainnya": D(0),
        "output_total": D(0), "ka": D(0), "ntb_sebelum_adj": D(0), 
        "adjustment": D(0), "ntb": D(0),
    }
    suffix = "_adhb" if mode == "adhb" else "_adhk"
    for kode in child_kodes:
        row = (
            db.query(PdrbRekap)
            .filter(
                PdrbRekap.kategori_kode == kode,
                PdrbRekap.wilayah_kode == wilayah_kode,
                PdrbRekap.tahun == tahun,
                PdrbRekap.triwulan == triwulan,
            )
            .first()
        )
        if row:
            for k in totals:
                val = getattr(row, f"{k}{suffix}", None)
                if val is not None:
                    totals[k] += D(str(val))
    return totals


def _save_parent_rekap(
    db: Session, parent_kode: str, wilayah_kode: str,
    tahun: int, triwulan: Optional[int], totals_b: dict, totals_k: dict,
) -> None:
    from app.services.kalkulasi_service import _round6

    row = (
        db.query(PdrbRekap)
        .filter(
            PdrbRekap.kategori_kode == parent_kode,
            PdrbRekap.wilayah_kode == wilayah_kode,
            PdrbRekap.tahun == tahun,
            PdrbRekap.triwulan == triwulan,
        )
        .first()
    )
    if not row:
        row = PdrbRekap(
            kategori_kode=parent_kode, wilayah_kode=wilayah_kode,
            tahun=tahun, triwulan=triwulan,
        )
        db.add(row)

    for k, v in totals_b.items():
        setattr(row, f"{k}_adhb", _round6(v))
    for k, v in totals_k.items():
        setattr(row, f"{k}_adhk", _round6(v))
    row.calculated_at = datetime.now()
    db.flush()


def _recalculate_provinsi_agregat(
    db: Session, tahun: int, triwulan: Optional[int], kategori_kodes: set,
) -> None:
    from app.services.kalkulasi_service import _round6
    from decimal import Decimal

    komponen = [
        "output_primer_adhb", "output_sekunder_adhb", "output_lainnya_adhb",
        "output_total_adhb", "ka_adhb", "ntb_sebelum_adj_adhb", "adjustment_adhb", "ntb_adhb",
        "output_primer_adhk", "output_sekunder_adhk", "output_lainnya_adhk",
        "output_total_adhk", "ka_adhk", "ntb_sebelum_adj_adhk", "adjustment_adhk", "ntb_adhk",
    ]
    for kat_kode in kategori_kodes:
        kabkota_rows = (
            db.query(PdrbRekap)
            .filter(
                PdrbRekap.kategori_kode == kat_kode,
                PdrbRekap.wilayah_kode.in_(KODE_KABKOTA),
                PdrbRekap.tahun == tahun,
                PdrbRekap.triwulan == triwulan,
            )
            .all()
        )
        if not kabkota_rows:
            continue

        totals = {k: Decimal(0) for k in komponen}
        for r in kabkota_rows:
            for k in komponen:
                v = getattr(r, k, None)
                if v is not None:
                    totals[k] += Decimal(str(v))

        prov_row = (
            db.query(PdrbRekap)
            .filter(
                PdrbRekap.kategori_kode == kat_kode,
                PdrbRekap.wilayah_kode == KODE_PROVINSI,
                PdrbRekap.tahun == tahun,
                PdrbRekap.triwulan == triwulan,
            )
            .first()
        )
        if not prov_row:
            prov_row = PdrbRekap(
                kategori_kode=kat_kode, wilayah_kode=KODE_PROVINSI,
                tahun=tahun, triwulan=triwulan,
            )
            db.add(prov_row)

        for k, v in totals.items():
            setattr(prov_row, k, _round6(v))
        prov_row.calculated_at = datetime.now()

    db.flush()


# ─────────────────────────────────────────────────────────────────────────────
# SSE + Celery enqueue (DIPERTAHANKAN dari versi lama — dipakai 5 router API)
# ─────────────────────────────────────────────────────────────────────────────

def _publish_cascade_sse(task_id, event_type, result=None, **extra):
    """Push event ke SSE in-memory queue agar frontend S2 auto-refresh."""
    try:
        from app.api.input_deflator_sse import publish_cascade_event
        payload = {"task_id": task_id, "type": event_type, **extra}
        if result:
            payload.update({
                "wilayah_kode": result.wilayah_kode,
                "tahun": result.tahun,
                "triwulan": result.triwulan,
                "komoditas_affected": result.komoditas_affected,
                "subkategori_affected": result.subkategori_affected,
                "duration_seconds": result.duration_seconds,
                "errors": result.errors,
            })
        publish_cascade_event(payload)
    except Exception as e:
        logger.warning(f"[CASCADE] SSE publish gagal (bukan critical): {e}")


def enqueue_cascade(
    trigger_type, wilayah_kode, tahun, triwulan=None,
    komoditas_id=None, kategori_kode_scope=None,
):
    """
    Kirim recalculate ke Celery (async). Jika Celery tak tersedia → jalankan
    synchronous di background thread. Kembalikan task_id untuk tracking SSE.
    """
    import uuid
    task_id = str(uuid.uuid4())

    _publish_cascade_sse(task_id, "cascade_start", trigger_type=trigger_type,
                         wilayah_kode=wilayah_kode, tahun=tahun, triwulan=triwulan)

    try:
        from app.celery_app import celery_app
        celery_task = celery_app.send_task(
            "app.tasks.cascade_task",
            kwargs={
                "trigger_type": trigger_type, "wilayah_kode": wilayah_kode,
                "tahun": tahun, "triwulan": triwulan, "komoditas_id": komoditas_id,
                "kategori_kode_scope": kategori_kode_scope, "task_id": task_id,
            },
        )
        logger.info(f"[CASCADE] Task di-enqueue: {celery_task.id}")
        return celery_task.id
    except ImportError:
        logger.warning("[CASCADE] Celery tidak tersedia, menjalankan synchronous")
        from app.database import SessionLocal
        import threading

        def _run_sync():
            db = SessionLocal()
            try:
                res = sync_recalculate(
                    db, trigger_type, wilayah_kode, tahun, triwulan,
                    komoditas_id=komoditas_id, kategori_kode_scope=kategori_kode_scope,
                )
                _publish_cascade_sse(
                    task_id, "cascade_error" if res.errors else "cascade_done", result=res
                )
            except Exception as e:
                logger.error(f"[CASCADE] Sync error: {e}", exc_info=True)
                _publish_cascade_sse(task_id, "cascade_error", error=str(e), task_id=task_id)
            finally:
                db.close()

        threading.Thread(target=_run_sync, daemon=True).start()
        return task_id