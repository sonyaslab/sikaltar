"""
Service: CascadeService
Sistem update otomatis — dipanggil setiap kali input berubah.
Menjalankan recalculation cascade dari level komoditas → subkategori → kategori → PDRB total.

Alur:
  Input berubah → invalidate cache → antrian Celery → recalculate → simpan → notifikasi

Mendukung dua mode:
  1. Synchronous (sync_recalculate)  : untuk testing / perubahan batch offline
  2. Asynchronous via Celery (enqueue): untuk production, agar UI tidak freeze
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Literal, Optional

from sqlalchemy.orm import Session

from app.models.hasil import LkHasil, PdrbRekap
from app.models.komoditas import Komoditas
from app.services.kalkulasi_service import (
    HasilSubkategori,
    hitung_output_komoditas,
    hitung_subkategori,
    hitung_kategori_deflasi,
    simpan_lk_hasil,
)
from app.services.agregasi_service import (
    agregasi_tahunan,
    simpan_rekap_dari_hasil,
    hitung_indikator_turunan,
    hitung_semua_indikator_wilayah,
)

logger = logging.getLogger(__name__)

TriggerType = Literal["produksi", "harga", "deflator", "rasio_override"]

KODE_PROVINSI = "65"
KODE_KABKOTA = ["6501", "6502", "6503", "6504", "6571"]


@dataclass
class CascadeResult:
    """Ringkasan hasil cascade recalculation."""
    trigger_type: str
    wilayah_kode: str
    tahun: int
    triwulan: Optional[int]
    komoditas_affected: list[int]
    subkategori_affected: list[str]
    kategori_affected: list[str]
    started_at: datetime
    finished_at: Optional[datetime] = None
    errors: list[str] = None
    warnings: list[str] = None

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


def _get_kategori_kode(db: Session, komoditas_id: int) -> Optional[str]:
    """Ambil kode subkategori dari komoditas."""
    kom = db.get(Komoditas, komoditas_id)
    return kom.kategori_kode if kom else None


def _get_parent_kode(kategori_kode: str) -> Optional[str]:
    """
    Ambil kode parent dari kode kategori hierarkis.
    '1.1.a' → '1.1', '1.1' → '1', '1' → None
    """
    parts = kategori_kode.split(".")
    if len(parts) <= 1:
        return None
    return ".".join(parts[:-1])


def _collect_ancestor_kodes(kategori_kode: str) -> list[str]:
    """
    Kumpulkan semua ancestor dari subkategori ke atas.
    '1.1.a' → ['1.1', '1']
    """
    ancestors = []
    parent = _get_parent_kode(kategori_kode)
    while parent:
        ancestors.append(parent)
        parent = _get_parent_kode(parent)
    return ancestors


def _invalidate_lk_hasil(
    db: Session, komoditas_id: int, wilayah_kode: str, tahun: int, triwulan: Optional[int]
) -> None:
    """Tandai cache lk_hasil sebagai tidak valid."""
    row = (
        db.query(LkHasil)
        .filter(
            LkHasil.komoditas_id == komoditas_id,
            LkHasil.wilayah_kode == wilayah_kode,
            LkHasil.tahun == tahun,
            LkHasil.triwulan == triwulan,
        )
        .first()
    )
    if row:
        row.is_valid = False
        db.flush()


def _invalidate_pdrb_rekap(
    db: Session, kategori_kode: str, wilayah_kode: str, tahun: int, triwulan: Optional[int]
) -> None:
    """Tandai rekap subkategori sebagai tidak valid (menghapus calculated_at lama)."""
    # Tidak delete — cukup set semua komponen ke None untuk menandai stale
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
        # Hanya reset indikator turunan, bukan nilai pokok
        row.distribusi_pct = None
        row.laju_pertumbuhan_pct = None
        row.indeks_implisit = None
        row.laju_implisit_pct = None
    db.flush()


def sync_recalculate(
    db: Session,
    trigger_type: TriggerType,
    wilayah_kode: str,
    tahun: int,
    triwulan: Optional[int] = None,
    komoditas_id: Optional[int] = None,
    kategori_kode_scope: Optional[str] = None,
) -> CascadeResult:
    """
    Jalankan recalculation cascade secara SYNCHRONOUS.
    Gunakan untuk: testing, batch update, atau trigger dari CLI.

    Untuk production dengan banyak data, gunakan enqueue_cascade() + Celery.

    Args:
        db: Database session
        trigger_type: Jenis perubahan yang memicu recalculation
        wilayah_kode: Wilayah yang terdampak
        tahun: Tahun kalkulasi
        triwulan: Triwulan (None = tahunan)
        komoditas_id: ID komoditas spesifik (jika trigger dari perubahan satu komoditas)
        kategori_kode_scope: Override scope recalculation ke satu subkategori

    Returns:
        CascadeResult: Ringkasan hasil
    """
    result = CascadeResult(
        trigger_type=trigger_type,
        wilayah_kode=wilayah_kode,
        tahun=tahun,
        triwulan=triwulan,
        komoditas_affected=[],
        subkategori_affected=[],
        kategori_affected=[],
        started_at=datetime.now(),
    )

    logger.info(
        f"[CASCADE] Mulai: trigger={trigger_type}, wilayah={wilayah_kode}, "
        f"tahun={tahun}, tw={triwulan}, komoditas={komoditas_id}"
    )

    # ── Tentukan scope recalculation ──────────────────────────────────────
    if komoditas_id:
        subkategori_kode = _get_kategori_kode(db, komoditas_id)
        if not subkategori_kode:
            result.errors.append(f"Komoditas ID={komoditas_id} tidak ditemukan")
            result.finished_at = datetime.now()
            return result
        subkategori_to_recalc = {subkategori_kode}

    elif kategori_kode_scope:
        # Recalculate seluruh subkategori tertentu
        subkategori_to_recalc = {kategori_kode_scope}
        # Tambahkan semua sub-subkategori di bawahnya
        from app.models.kategori_pdrb import KategoriPdrb
        children = (
            db.query(KategoriPdrb.kode)
            .filter(KategoriPdrb.parent_kode == kategori_kode_scope)
            .all()
        )
        for (child_kode,) in children:
            subkategori_to_recalc.add(child_kode)

    else:
        # Recalculate SEMUA subkategori di wilayah ini
        from app.models.kategori_pdrb import KategoriPdrb
        subkategori_to_recalc = set(
            kode
            for (kode,) in db.query(KategoriPdrb.kode)
            .filter(KategoriPdrb.level >= 3)  # level 3 = sub-subkategori yang punya komoditas
            .all()
        )
        if not subkategori_to_recalc:
            # Fallback ke level 2
            subkategori_to_recalc = set(
                kode
                for (kode,) in db.query(KategoriPdrb.kode)
                .filter(KategoriPdrb.level == 2)
                .all()
            )

    # ── Step 1: Recalculate setiap komoditas dalam scope ─────────────────
    for subkat_kode in subkategori_to_recalc:
        komoditas_list = (
            db.query(Komoditas)
            .filter(Komoditas.kategori_kode == subkat_kode, Komoditas.aktif.is_(True))
            .all()
        )
        for kom in komoditas_list:
            if komoditas_id and kom.id != komoditas_id:
                continue   # Jika trigger spesifik komoditas, skip yang lain

            _invalidate_lk_hasil(db, kom.id, wilayah_kode, tahun, triwulan)
            h = hitung_output_komoditas(db, kom.id, wilayah_kode, tahun, triwulan)
            if h.error:
                result.warnings.append(h.error)
                logger.warning(f"[CASCADE] Komoditas {kom.id}: {h.error}")
                continue

            simpan_lk_hasil(db, kom.id, wilayah_kode, tahun, triwulan, h, flush=False)
            result.komoditas_affected.append(kom.id)

    db.flush()
    logger.info(f"[CASCADE] Step 1 selesai: {len(result.komoditas_affected)} komoditas")

    # ── Step 2: Recalculate subkategori (agregasi komoditas) ─────────────
    for subkat_kode in subkategori_to_recalc:
        _invalidate_pdrb_rekap(db, subkat_kode, wilayah_kode, tahun, triwulan)
        h_sub = hitung_subkategori(db, subkat_kode, wilayah_kode, tahun, triwulan)
        for w in h_sub.peringatan:
            result.warnings.append(w)

        simpan_rekap_dari_hasil(db, h_sub, flush=False)
        result.subkategori_affected.append(subkat_kode)

    db.flush()
    logger.info(f"[CASCADE] Step 2 selesai: {len(result.subkategori_affected)} subkategori")

    # ── Step 3: Roll-up ke kategori parent ────────────────────────────────
    parent_kodes: set[str] = set()
    for subkat_kode in subkategori_to_recalc:
        for ancestor in _collect_ancestor_kodes(subkat_kode):
            parent_kodes.add(ancestor)

    for parent_kode in sorted(parent_kodes, key=lambda x: x.count("."), reverse=True):
        # Jumlahkan semua child yang langsung di bawah parent ini
        from app.models.kategori_pdrb import KategoriPdrb
        children = (
            db.query(KategoriPdrb.kode)
            .filter(KategoriPdrb.parent_kode == parent_kode)
            .all()
        )
        total_b = __class__._sum_ntb_children(db, [k for (k,) in children], wilayah_kode, tahun, triwulan, "adhb")
        total_k = __class__._sum_ntb_children(db, [k for (k,) in children], wilayah_kode, tahun, triwulan, "adhk")

        # Simpan rekap parent
        _save_parent_rekap(db, parent_kode, wilayah_kode, tahun, triwulan, total_b, total_k)
        result.kategori_affected.append(parent_kode)

    db.flush()

    # ── Step 4: Hitung indikator turunan ─────────────────────────────────
    all_affected = list(subkategori_to_recalc) + list(parent_kodes)
    for kode in all_affected:
        hitung_indikator_turunan(db, kode, wilayah_kode, tahun, triwulan)

    # ── Step 5: Agregasi tahunan jika ada triwulan ────────────────────────
    if triwulan is not None:
        for kode in all_affected:
            agregasi_tahunan(db, kode, wilayah_kode, tahun)

    # ── Step 6: Jika kabupaten/kota, recalculate provinsi (65) ───────────
    if wilayah_kode != KODE_PROVINSI:
        _recalculate_provinsi_agregat(db, tahun, triwulan, parent_kodes | subkategori_to_recalc)

    db.commit()
    result.finished_at = datetime.now()
    logger.info(
        f"[CASCADE] Selesai dalam {result.duration_seconds:.2f}s. "
        f"Komoditas={len(result.komoditas_affected)}, "
        f"Subkategori={len(result.subkategori_affected)}, "
        f"Parent={len(result.kategori_affected)}"
    )
    return result

    @staticmethod
    def _sum_ntb_children(
        db: Session, child_kodes: list[str], wilayah_kode: str,
        tahun: int, triwulan: Optional[int], mode: str
    ) -> dict:
        """Sum NTB dan komponen dari semua child rekap."""
        from decimal import Decimal as D
        totals = {
            "output_primer": D(0), "output_sekunder": D(0), "output_lainnya": D(0),
            "output_total": D(0), "ka": D(0), "ntb": D(0),
        }
        suffix = f"_adhb" if mode == "adhb" else "_adhk"
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
    tahun: int, triwulan: Optional[int],
    totals_b: dict, totals_k: dict,
) -> None:
    """Simpan roll-up rekap untuk kategori parent."""
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
    db: Session, tahun: int, triwulan: Optional[int], kategori_kodes: set[str],
) -> None:
    """
    Rekap provinsi (65) = SUM semua kabupaten/kota untuk kategori yang terdampak.
    """
    from app.services.kalkulasi_service import _round6
    from decimal import Decimal

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

        komponen = [
            "output_primer_adhb", "output_sekunder_adhb", "output_lainnya_adhb",
            "output_total_adhb", "ka_adhb", "ntb_adhb",
            "output_primer_adhk", "output_sekunder_adhk", "output_lainnya_adhk",
            "output_total_adhk", "ka_adhk", "ntb_adhk",
        ]
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


def _publish_cascade_sse(
    task_id: str,
    event_type: str,
    result: Optional[CascadeResult] = None,
    **extra,
) -> None:
    """
    Push event ke SSE in-memory queue.
    Dipanggil setelah cascade sync selesai agar S2 frontend bisa auto-refresh.
    """
    try:
        from app.api.input_deflator_sse import publish_cascade_event
        payload = {
            "task_id":  task_id,
            "type":     event_type,
            **extra,
        }
        if result:
            payload.update({
                "wilayah_kode":         result.wilayah_kode,
                "tahun":                result.tahun,
                "triwulan":             result.triwulan,
                "komoditas_affected":   result.komoditas_affected,
                "subkategori_affected": result.subkategori_affected,
                "duration_seconds":     result.duration_seconds,
                "errors":               result.errors,
            })
        publish_cascade_event(payload)
    except Exception as e:
        logger.warning(f"[CASCADE] SSE publish gagal (bukan critical): {e}")


def enqueue_cascade(
    trigger_type: TriggerType,
    wilayah_kode: str,
    tahun: int,
    triwulan: Optional[int] = None,
    komoditas_id: Optional[int] = None,
    kategori_kode_scope: Optional[str] = None,
) -> str:
    """
    Kirim recalculate_cascade ke antrian Celery (async).
    Kembalikan task_id untuk status tracking via SSE/WebSocket.

    Jika Celery tidak tersedia, jalankan synchronous sebagai fallback.
    Setelah selesai, publish event ke SSE queue agar S2 frontend auto-refresh.
    """
    import uuid
    task_id = str(uuid.uuid4())

    # Publish 'start' event
    _publish_cascade_sse(task_id, "cascade_start", trigger_type=trigger_type,
                         wilayah_kode=wilayah_kode, tahun=tahun, triwulan=triwulan)

    try:
        from app.celery_app import celery_app
        celery_task = celery_app.send_task(
            "app.tasks.cascade_task",
            kwargs={
                "trigger_type": trigger_type,
                "wilayah_kode": wilayah_kode,
                "tahun": tahun,
                "triwulan": triwulan,
                "komoditas_id": komoditas_id,
                "kategori_kode_scope": kategori_kode_scope,
                "task_id": task_id,
            },
        )
        logger.info(f"[CASCADE] Task di-enqueue: {celery_task.id}")
        return celery_task.id
    except ImportError:
        logger.warning("[CASCADE] Celery tidak tersedia, menjalankan synchronous")
        # Buat session baru untuk fallback sync
        from app.database import SessionLocal
        import threading

        def _run_sync():
            db = SessionLocal()
            try:
                result = sync_recalculate(
                    db, trigger_type, wilayah_kode, tahun, triwulan,
                    komoditas_id=komoditas_id,
                    kategori_kode_scope=kategori_kode_scope,
                )
                if result.errors:
                    _publish_cascade_sse(task_id, "cascade_error", result=result)
                else:
                    _publish_cascade_sse(task_id, "cascade_done", result=result)
            except Exception as e:
                logger.error(f"[CASCADE] Sync error: {e}", exc_info=True)
                _publish_cascade_sse(task_id, "cascade_error",
                                     error=str(e), task_id=task_id)
            finally:
                db.close()

        # Jalankan di background thread agar tidak blocking HTTP response
        t = threading.Thread(target=_run_sync, daemon=True)
        t.start()

        return task_id
