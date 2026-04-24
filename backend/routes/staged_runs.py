"""
Staged run management — for RaceSpy timing mode.

Workflow:
  1. Staging worker POSTs a photo → server runs OCR → returns candidates
  2. Worker confirms competitor → staged run created (status=staged)
  3. Start RaceSpy fires → server pops oldest staged run → status=running
  4. Finish RaceSpy fires → server finds running run → status=finished
"""
import base64
import io
import json
import os
import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from models import Competitor, StagedRun, TimingEvent

router = APIRouter()

_DATA_DIR = os.environ.get("DATA_DIR", os.path.join(os.path.dirname(__file__), "..", "..", "storage"))


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class StageRequest(BaseModel):
    competitor_id: str
    image_base64: Optional[str] = None   # JPEG from staging worker's device


class OCRScanRequest(BaseModel):
    image_base64: str                    # Scan only — returns candidates without creating a run


class PenaltyRequest(BaseModel):
    penalties: int


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.post("/staged-runs/ocr-scan")
async def ocr_scan(
    event_id: str,
    payload: OCRScanRequest,
    db: Session = Depends(get_db),
):
    """Run OCR on an image and return candidates without creating a staged run."""
    from services.ocr_service import run_ocr

    _MAX_IMAGE_BYTES = 4 * 1024 * 1024
    if len(payload.image_base64) > (_MAX_IMAGE_BYTES * 4 // 3 + 64):
        raise HTTPException(status_code=422, detail="image_base64 exceeds 4 MB limit")
    image_bytes = base64.b64decode(payload.image_base64)

    # Restrict OCR candidates to the active run group if one is set
    from models import Event as EventModel
    event = db.query(EventModel).filter(EventModel.id == event_id).first()
    comp_query = db.query(Competitor).filter(Competitor.event_id == event_id)
    if event and event.active_run_group_id:
        comp_query = comp_query.filter(Competitor.run_group_id == event.active_run_group_id)
    competitors = comp_query.all()

    candidates = [
        {"competitor_id": c.id, "number": c.number, "class_code": c.class_code}
        for c in competitors
    ]
    ocr_output = run_ocr(image_bytes, candidates)

    # Enrich candidates with full competitor info
    comp_map = {c.id: c for c in competitors}
    enriched = []
    for cand in ocr_output.get("ocr_result", {}).get("candidates", []):
        cid = cand.get("competitor_id")
        comp = comp_map.get(cid)
        if comp:
            enriched.append({
                **cand,
                "driver_name": comp.driver_name,
                "car_description": comp.car_description,
                "run_group_id": comp.run_group_id,
            })

    return {
        "success": True,
        "data": {
            "match_status": ocr_output.get("match_status"),
            "matched_competitor_id": ocr_output.get("matched_competitor_id"),
            "candidates": enriched,
            "raw_text": ocr_output.get("ocr_result", {}).get("raw_text"),
        },
    }


@router.post("/staged-runs")
def create_staged_run(
    event_id: str,
    payload: StageRequest,
    db: Session = Depends(get_db),
):
    """Create a staged run for a confirmed competitor."""
    comp = db.query(Competitor).filter(
        Competitor.id == payload.competitor_id,
        Competitor.event_id == event_id,
    ).first()
    if not comp:
        raise HTTPException(status_code=404, detail="Competitor not found")

    _MAX_IMAGE_BYTES = 4 * 1024 * 1024
    image_path = None
    if payload.image_base64:
        if len(payload.image_base64) > (_MAX_IMAGE_BYTES * 4 // 3 + 64):
            raise HTTPException(status_code=422, detail="image_base64 exceeds 4 MB limit")
        try:
            image_bytes = base64.b64decode(payload.image_base64)
            image_path = _save_staging_image(event_id, image_bytes)
        except Exception as exc:
            print(f"Warning: failed to save staging image: {exc}")

    run = StagedRun(
        id=str(uuid.uuid4()),
        event_id=event_id,
        competitor_id=payload.competitor_id,
        status="staged",
        image_path=image_path,
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    return {"success": True, "data": _run_dict(run, db)}


@router.get("/staged-runs")
def list_staged_runs(
    event_id: str,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """List staged runs for an event, optionally filtered by status."""
    query = db.query(StagedRun).filter(StagedRun.event_id == event_id)
    if status:
        query = query.filter(StagedRun.status == status)
    runs = query.order_by(StagedRun.staged_at).all()
    return {"success": True, "data": {"staged_runs": [_run_dict(r, db) for r in runs]}}


@router.get("/staged-runs/{run_id}")
def get_staged_run(event_id: str, run_id: str, db: Session = Depends(get_db)):
    run = _get_run_or_404(event_id, run_id, db)
    return {"success": True, "data": _run_dict(run, db)}


@router.post("/staged-runs/{run_id}/penalties")
def set_penalties(
    event_id: str,
    run_id: str,
    payload: PenaltyRequest,
    db: Session = Depends(get_db),
):
    run = _get_run_or_404(event_id, run_id, db)
    run.penalties = payload.penalties
    if run.raw_time_ms is not None:
        # Recompute adjusted not stored separately — caller reads raw_time_ms + penalties
        pass
    db.commit()
    return {"success": True, "data": _run_dict(run, db)}


@router.post("/staged-runs/{run_id}/dnf")
def mark_dnf(event_id: str, run_id: str, db: Session = Depends(get_db)):
    run = _get_run_or_404(event_id, run_id, db)
    if run.status not in ("staged", "running"):
        raise HTTPException(status_code=409, detail="Run is not in a DNF-able state")
    run.status = "dnf"
    db.commit()
    return {"success": True, "data": _run_dict(run, db)}


@router.delete("/staged-runs/{run_id}")
def delete_staged_run(event_id: str, run_id: str, db: Session = Depends(get_db)):
    run = _get_run_or_404(event_id, run_id, db)
    db.delete(run)
    db.commit()
    return {"success": True, "data": {"deleted_id": run_id}}


# ---------------------------------------------------------------------------
# Internal: called by timing_events when a RaceSpy fires
# ---------------------------------------------------------------------------

def handle_start_timing_event(event_id: str, timing_event_id: str, timestamp_utc_ms: int, db: Session):
    """Link the oldest staged run to this start timing event."""
    run = (
        db.query(StagedRun)
        .filter(StagedRun.event_id == event_id, StagedRun.status == "staged")
        .order_by(StagedRun.staged_at)
        .first()
    )
    if not run:
        return
    run.status = "running"
    run.start_timing_event_id = timing_event_id
    run.start_time_utc_ms = timestamp_utc_ms
    db.commit()


def handle_finish_timing_event(event_id: str, timing_event_id: str, timestamp_utc_ms: int, db: Session):
    """Link the oldest running staged run to this finish timing event."""
    run = (
        db.query(StagedRun)
        .filter(StagedRun.event_id == event_id, StagedRun.status == "running")
        .order_by(StagedRun.staged_at)
        .first()
    )
    if not run:
        return
    run.status = "finished"
    run.finish_timing_event_id = timing_event_id
    run.finish_time_utc_ms = timestamp_utc_ms
    if run.start_time_utc_ms:
        run.raw_time_ms = timestamp_utc_ms - run.start_time_utc_ms
    db.commit()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_run_or_404(event_id: str, run_id: str, db: Session) -> StagedRun:
    run = db.query(StagedRun).filter(
        StagedRun.id == run_id, StagedRun.event_id == event_id
    ).first()
    if not run:
        raise HTTPException(status_code=404, detail="Staged run not found")
    return run


def _save_staging_image(event_id: str, data: bytes) -> str:
    directory = os.path.join(_DATA_DIR, "events", event_id, "staging")
    os.makedirs(directory, exist_ok=True)
    filename = f"{uuid.uuid4()}.jpg"
    path = os.path.join(directory, filename)
    with open(path, "wb") as f:
        f.write(data)
    return path


def _run_dict(run: StagedRun, db: Session) -> dict:
    comp = db.query(Competitor).filter(Competitor.id == run.competitor_id).first() if run.competitor_id else None
    raw_time_s = run.raw_time_ms / 1000.0 if run.raw_time_ms is not None else None
    adjusted_time_s = (raw_time_s + run.penalties * 2.0) if raw_time_s is not None else None
    return {
        "id": run.id,
        "event_id": run.event_id,
        "status": run.status,
        "competitor": {
            "id": comp.id,
            "number": comp.number,
            "class_code": comp.class_code,
            "driver_name": comp.driver_name,
            "car_description": comp.car_description,
        } if comp else None,
        "start_time_utc_ms": run.start_time_utc_ms,
        "finish_time_utc_ms": run.finish_time_utc_ms,
        "raw_time_s": raw_time_s,
        "adjusted_time_s": adjusted_time_s,
        "penalties": run.penalties,
        "image_path": run.image_path,
        "staged_at": run.staged_at.isoformat() if run.staged_at else None,
    }
