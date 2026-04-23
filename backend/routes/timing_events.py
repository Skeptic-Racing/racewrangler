"""
Timing event intake (RaceSpy → server) and ambiguity resolution queue.

RaceSpies POST to /api/v1/events/{event_id}/timing-events.
The server persists immediately, returns 200, then runs OCR in the background.
"""
import base64
import json
import os
import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from models import Camera, Competitor, Event, RunGroup, TimingEvent
from services.ocr_service import run_ocr

router = APIRouter()

# Images are stored at DATA_DIR/events/{event_id}/timing-events/{sequence_number}.jpg
_DATA_DIR = os.environ.get("DATA_DIR", os.path.join(os.path.dirname(__file__), "..", "..", "storage"))


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class TimingEventIngestRequest(BaseModel):
    camera_id: str
    role: str                        # "start" | "finish"
    timestamp_utc_ms: int
    timestamp_monotonic_ns: int
    sequence_number: int
    image_base64: Optional[str] = None  # Base64-encoded JPEG; optional for manual entries


class ResolveRequest(BaseModel):
    action: str                          # "select" | "skip" | "unknown"
    competitor_id: Optional[str] = None  # Required when action == "select"


# ---------------------------------------------------------------------------
# Timing event intake
# ---------------------------------------------------------------------------

@router.post("/timing-events")
def ingest_timing_event(
    event_id: str,
    payload: TimingEventIngestRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """Receive a trigger event from a RaceSpy camera."""
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail=f"Event {event_id} not found")

    if payload.role not in ("start", "finish"):
        raise HTTPException(status_code=422, detail="role must be 'start' or 'finish'")

    # Save image to disk.
    _MAX_IMAGE_BYTES = 4 * 1024 * 1024  # 4 MB decoded ceiling
    image_path: Optional[str] = None
    image_bytes: Optional[bytes] = None
    if payload.image_base64:
        if len(payload.image_base64) > (_MAX_IMAGE_BYTES * 4 // 3 + 64):
            print(f"Warning: image_base64 too large ({len(payload.image_base64)} chars), skipping")
        else:
            try:
                image_bytes = base64.b64decode(payload.image_base64)
                image_path = _save_image(event_id, payload.sequence_number, payload.camera_id, image_bytes)
            except Exception as exc:
                print(f"Warning: failed to save timing event image: {exc}")

    # Persist the TimingEvent immediately so the RaceSpy gets a fast 200 OK.
    te = TimingEvent(
        id=str(uuid.uuid4()),
        event_id=event_id,
        camera_id=payload.camera_id,
        role=payload.role,
        timestamp_utc_ms=payload.timestamp_utc_ms,
        timestamp_monotonic_ns=payload.timestamp_monotonic_ns,
        sequence_number=payload.sequence_number,
        image_path=image_path,
        match_status=None,
    )
    db.add(te)

    # Update camera last_seen_at.
    cam = db.query(Camera).filter(Camera.id == payload.camera_id).first()
    if cam:
        cam.last_seen_at = datetime.utcnow()

    db.commit()
    db.refresh(te)

    # In racespy mode, advance the staging queue immediately.
    if event.timing_mode == "racespy":
        from routes.staged_runs import handle_start_timing_event, handle_finish_timing_event
        if payload.role == "start":
            handle_start_timing_event(event_id, te.id, payload.timestamp_utc_ms, db)
        elif payload.role == "finish":
            handle_finish_timing_event(event_id, te.id, payload.timestamp_utc_ms, db)

    # Run OCR in the background — does not block the response.
    if image_bytes:
        background_tasks.add_task(_process_ocr, te.id, event_id, image_bytes)
    else:
        # No image: send straight to review queue.
        te.match_status = "needs_review"
        db.commit()

    return {"success": True, "data": {"timing_event_id": te.id}}


@router.get("/timing-events")
def list_timing_events(event_id: str, db: Session = Depends(get_db)):
    """List all timing events for an event."""
    events = (
        db.query(TimingEvent)
        .filter(TimingEvent.event_id == event_id)
        .order_by(TimingEvent.timestamp_utc_ms)
        .all()
    )
    return {"success": True, "data": {"timing_events": [_te_dict(te) for te in events]}}


# ---------------------------------------------------------------------------
# Ambiguity queue
# ---------------------------------------------------------------------------

@router.get("/ambiguity-queue/count")
def ambiguity_count(event_id: str, db: Session = Depends(get_db)):
    """Pending ambiguity count — used for the notification badge."""
    count = (
        db.query(TimingEvent)
        .filter(
            TimingEvent.event_id == event_id,
            TimingEvent.match_status == "needs_review",
            TimingEvent.resolved_by == None,
        )
        .count()
    )
    return {"success": True, "data": {"pending": count}}


@router.get("/ambiguity-queue")
def get_ambiguity_queue(event_id: str, db: Session = Depends(get_db)):
    """Return all timing events pending human identification, with OCR candidates."""
    pending = (
        db.query(TimingEvent)
        .filter(
            TimingEvent.event_id == event_id,
            TimingEvent.match_status.in_(["needs_review", "tentative"]),
            TimingEvent.resolved_by == None,
        )
        .order_by(TimingEvent.created_at)
        .all()
    )

    # Fetch run group competitors for context (OCR candidate display).
    all_competitors = (
        db.query(Competitor).filter(Competitor.event_id == event_id).all()
    )
    comp_by_id = {c.id: c for c in all_competitors}

    items = []
    for te in pending:
        ocr = json.loads(te.ocr_result_json) if te.ocr_result_json else None
        items.append({
            **_te_dict(te),
            "ocr_detail": ocr,
            "suggested_competitor": _competitor_summary(comp_by_id.get(te.matched_competitor_id))
            if te.matched_competitor_id
            else None,
        })

    return {"success": True, "data": {"queue": items, "count": len(items)}}


@router.post("/ambiguity-queue/{timing_event_id}/resolve")
def resolve_ambiguity(
    event_id: str,
    timing_event_id: str,
    payload: ResolveRequest,
    db: Session = Depends(get_db),
):
    """Resolve or defer a queued timing event."""
    te = db.query(TimingEvent).filter(
        TimingEvent.id == timing_event_id,
        TimingEvent.event_id == event_id,
    ).first()
    if not te:
        raise HTTPException(status_code=404, detail="Timing event not found")

    if payload.action == "select":
        if not payload.competitor_id:
            raise HTTPException(status_code=422, detail="competitor_id required for action=select")
        comp = db.query(Competitor).filter(
            Competitor.id == payload.competitor_id,
            Competitor.event_id == event_id,
        ).first()
        if not comp:
            raise HTTPException(status_code=404, detail="Competitor not found")
        te.matched_competitor_id = payload.competitor_id
        te.match_status = "human"
        te.resolved_by = "human"
        te.resolved_at = datetime.utcnow()

    elif payload.action == "unknown":
        te.match_status = "unidentified"
        te.resolved_by = "human"
        te.resolved_at = datetime.utcnow()

    elif payload.action == "skip":
        # Move to the back of the queue by bumping created_at.
        te.created_at = datetime.utcnow()

    else:
        raise HTTPException(status_code=422, detail="action must be select, skip, or unknown")

    db.commit()
    db.refresh(te)
    return {"success": True, "data": _te_dict(te)}


# ---------------------------------------------------------------------------
# Background OCR task
# ---------------------------------------------------------------------------

def _process_ocr(timing_event_id: str, event_id: str, image_bytes: bytes) -> None:
    """Runs in a background task after the RaceSpy has already received its 200 OK."""
    from database import SessionLocal

    db = SessionLocal()
    try:
        te = db.query(TimingEvent).filter(TimingEvent.id == timing_event_id).first()
        if not te:
            return

        # Build run group candidate list — restrict to active run group if possible.
        competitors = (
            db.query(Competitor).filter(Competitor.event_id == event_id).all()
        )
        candidates = [
            {"competitor_id": c.id, "number": c.number, "class_code": c.class_code}
            for c in competitors
        ]

        ocr_output = run_ocr(image_bytes, candidates)

        te.ocr_result_json = json.dumps(ocr_output.get("ocr_result", {}))
        te.match_status = ocr_output["match_status"]
        te.matched_competitor_id = ocr_output.get("matched_competitor_id")
        if ocr_output["match_status"] == "auto":
            te.resolved_by = "ocr"
            te.resolved_at = datetime.utcnow()

        db.commit()
    except Exception as exc:
        print(f"OCR background task failed for {timing_event_id}: {exc}")
        try:
            te = db.query(TimingEvent).filter(TimingEvent.id == timing_event_id).first()
            if te:
                te.match_status = "needs_review"
                db.commit()
        except Exception:
            pass
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _save_image(event_id: str, sequence_number: int, camera_id: str, data: bytes) -> str:
    directory = os.path.join(_DATA_DIR, "events", event_id, "timing-events")
    os.makedirs(directory, exist_ok=True)
    filename = f"{sequence_number:06d}_{camera_id[:8]}.jpg"
    path = os.path.join(directory, filename)
    with open(path, "wb") as f:
        f.write(data)
    return path


def _te_dict(te: TimingEvent) -> dict:
    return {
        "id": te.id,
        "event_id": te.event_id,
        "camera_id": te.camera_id,
        "role": te.role,
        "timestamp_utc_ms": te.timestamp_utc_ms,
        "timestamp_monotonic_ns": te.timestamp_monotonic_ns,
        "sequence_number": te.sequence_number,
        "image_path": te.image_path,
        "match_status": te.match_status,
        "matched_competitor_id": te.matched_competitor_id,
        "resolved_by": te.resolved_by,
        "resolved_at": te.resolved_at.isoformat() if te.resolved_at else None,
        "created_at": te.created_at.isoformat() if te.created_at else None,
    }


def _competitor_summary(comp: Optional[Competitor]) -> Optional[dict]:
    if not comp:
        return None
    return {
        "id": comp.id,
        "number": comp.number,
        "class_code": comp.class_code,
        "driver_name": comp.driver_name,
    }
