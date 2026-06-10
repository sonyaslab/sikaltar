"""API Router — Indeks Deflator (S1.I) & SSE Cascade Events."""
from __future__ import annotations

import asyncio
import json
from decimal import Decimal
from typing import Optional, AsyncGenerator

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.input_data import InputIndeksDeflator
from app.models.kategori_pdrb import KategoriPdrb
from app.schemas.rasio_deflator import DeflatorPatch
from app.services.cascade_service import enqueue_cascade
from app.dependencies.auth_sse import require_sse_token
from app.models.user import User

deflator_router = APIRouter()
sse_router = APIRouter()

# In-memory event queue for SSE (per-request broadcast)
# In production, gunakan Redis pub/sub
_cascade_events: list[dict] = []


@deflator_router.get("", summary="Data indeks deflator")
def get_deflator(
    wilayah_kode: str = Query("65"),
    tahun: int = Query(..., ge=2008),
    triwulan: Optional[int] = Query(None, ge=1, le=4),
    db: Session = Depends(get_db),
):
    """
    Kembalikan list indeks deflator per kategori.
    Hanya kategori dengan metode_adhk='Deflasi' yang bisa diisi.
    Sertakan nilai tahun lalu dan perubahan (%).
    """
    kategori_list = (
        db.query(KategoriPdrb)
        .filter(KategoriPdrb.level.in_([1, 2]))
        .order_by(KategoriPdrb.urutan)
        .all()
    )

    result = []
    for kat in kategori_list:
        is_editable = kat.metode_adhk == "Deflasi"

        # Nilai tahun ini
        row = (
            db.query(InputIndeksDeflator)
            .filter(
                InputIndeksDeflator.kategori_kode == kat.kode,
                InputIndeksDeflator.wilayah_kode == wilayah_kode,
                InputIndeksDeflator.tahun == tahun,
                InputIndeksDeflator.triwulan == triwulan,
            )
            .first()
        )

        # Nilai tahun lalu
        row_prev = (
            db.query(InputIndeksDeflator)
            .filter(
                InputIndeksDeflator.kategori_kode == kat.kode,
                InputIndeksDeflator.wilayah_kode == wilayah_kode,
                InputIndeksDeflator.tahun == tahun - 1,
                InputIndeksDeflator.triwulan == triwulan,
            )
            .first()
        )

        nilai = Decimal(str(row.nilai_indeks)) if row else None
        nilai_prev = Decimal(str(row_prev.nilai_indeks)) if row_prev else None
        perubahan_pct = None
        if nilai and nilai_prev and nilai_prev != 0:
            perubahan_pct = round(float((nilai - nilai_prev) / nilai_prev * 100), 4)

        result.append({
            "kategori_kode": kat.kode,
            "kategori_nama": kat.nama,
            "metode_adhb": kat.metode_adhb,
            "metode_adhk": kat.metode_adhk,
            "wilayah_kode": wilayah_kode,
            "tahun": tahun,
            "triwulan": triwulan,
            "nilai_indeks": str(nilai) if nilai else None,
            "nilai_indeks_tahun_lalu": str(nilai_prev) if nilai_prev else None,
            "perubahan_pct": perubahan_pct,
            "is_editable": is_editable,
        })

    return result


@deflator_router.patch("/{kategori_kode}", summary="Update indeks deflator")
def patch_deflator(
    kategori_kode: str,
    body: DeflatorPatch,
    wilayah_kode: str = Query("65"),
    tahun: int = Query(..., ge=2008),
    triwulan: Optional[int] = Query(None, ge=1, le=4),
    db: Session = Depends(get_db),
):
    from fastapi import HTTPException
    # Cek metode kategori
    kat = db.query(KategoriPdrb).filter(KategoriPdrb.kode == kategori_kode).first()
    if not kat:
        raise HTTPException(status_code=404, detail=f"Kategori {kategori_kode!r} tidak ditemukan")
    if kat.metode_adhk != "Deflasi":
        raise HTTPException(
            status_code=400,
            detail=f"Kategori {kategori_kode!r} menggunakan metode {kat.metode_adhk!r}, bukan Deflasi. Indeks tidak dapat diisi.",
        )

    row = (
        db.query(InputIndeksDeflator)
        .filter(
            InputIndeksDeflator.kategori_kode == kategori_kode,
            InputIndeksDeflator.wilayah_kode == wilayah_kode,
            InputIndeksDeflator.tahun == tahun,
            InputIndeksDeflator.triwulan == triwulan,
        )
        .first()
    )
    if not row:
        row = InputIndeksDeflator(
            kategori_kode=kategori_kode,
            wilayah_kode=wilayah_kode,
            tahun=tahun,
            triwulan=triwulan,
        )
        db.add(row)

    row.nilai_indeks = body.nilai_indeks
    db.commit()

    task_id = enqueue_cascade(
        trigger_type="deflator",
        wilayah_kode=wilayah_kode,
        tahun=tahun,
        triwulan=triwulan,
        kategori_kode_scope=kategori_kode,
    )

    return {"status": "ok", "task_id": task_id}


# ── SSE Endpoint ──────────────────────────────────────────────────────────────

def publish_cascade_event(event: dict) -> None:
    """Called by cascade tasks to broadcast progress."""
    global _cascade_events
    _cascade_events.append(event)
    # Keep only last 100 events
    if len(_cascade_events) > 100:
        _cascade_events = _cascade_events[-100:]


async def _event_generator(task_id: Optional[str]) -> AsyncGenerator[str, None]:
    """SSE generator — stream cascade events as they arrive."""
    sent_count = 0
    idle_ticks = 0

    # Send initial connection event
    yield f"event: connected\ndata: {json.dumps({'status': 'connected', 'task_id': task_id})}\n\n"

    while True:
        await asyncio.sleep(0.5)

        # Check for new events
        if len(_cascade_events) > sent_count:
            new_events = _cascade_events[sent_count:]
            for ev in new_events:
                # Filter by task_id if provided
                if task_id and ev.get("task_id") and ev["task_id"] != task_id:
                    continue
                data = json.dumps(ev)
                yield f"event: cascade\ndata: {data}\n\n"
            sent_count = len(_cascade_events)
            idle_ticks = 0
        else:
            idle_ticks += 1
            if idle_ticks % 20 == 0:  # Heartbeat every ~10 seconds
                yield f"event: heartbeat\ndata: {json.dumps({'ts': idle_ticks})}\n\n"

        # Auto-close after 5 minutes of no activity
        if idle_ticks > 600:
            yield f"event: timeout\ndata: {json.dumps({'message': 'Connection timed out'})}\n\n"
            break


@sse_router.get("/events", summary="SSE stream — cascade status real-time")
async def sse_events(task_id: Optional[str] = Query(None),
                    _user: User = Depends(require_sse_token),):
    """
    Server-Sent Events untuk status cascade recalculation.
    Frontend connect ke endpoint ini dan dengarkan event 'cascade'.
    """
    return StreamingResponse(
        _event_generator(task_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # Disable Nginx buffering
        },
    )
