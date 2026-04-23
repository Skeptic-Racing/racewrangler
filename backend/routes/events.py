"""Event, RunGroup, and Competitor management."""
import csv
import io
import uuid
from datetime import datetime, date
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from models import Competitor, Event, RunGroup

router = APIRouter()


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class EventCreateRequest(BaseModel):
    name: str
    date: Optional[str] = None   # ISO date string "YYYY-MM-DD"; converted in handler
    timing_mode: str = "human"


class EventResponse(BaseModel):
    id: str
    name: str
    date: Optional[date]
    status: str
    created_at: datetime


class RunGroupCreateRequest(BaseModel):
    name: str
    order: Optional[int] = 0


class RunGroupResponse(BaseModel):
    id: str
    event_id: str
    name: str
    order: int
    competitor_count: int = 0


class BulkAssignRequest(BaseModel):
    assignments: list[dict]  # [{"class_code": str, "run_group_id": str}]


class CompetitorCreateRequest(BaseModel):
    number: str
    class_code: str
    driver_name: str
    car_description: Optional[str] = None
    run_group_id: Optional[str] = None


class CompetitorUpdateRequest(BaseModel):
    run_group_id: Optional[str] = None
    number: Optional[str] = None
    class_code: Optional[str] = None
    driver_name: Optional[str] = None


class CompetitorResponse(BaseModel):
    id: str
    event_id: str
    number: str
    class_code: str
    driver_name: str
    car_description: Optional[str]
    run_group_id: Optional[str]
    run_group_name: Optional[str] = None


# ---------------------------------------------------------------------------
# Event routes
# ---------------------------------------------------------------------------

@router.post("")
def create_event(payload: EventCreateRequest, db: Session = Depends(get_db)):
    event_date = None
    if payload.date:
        try:
            event_date = date.fromisoformat(payload.date)
        except ValueError:
            raise HTTPException(status_code=422, detail="date must be YYYY-MM-DD")

    event = Event(
        id=str(uuid.uuid4()),
        name=payload.name,
        date=event_date,
        status="setup",
        timing_mode=payload.timing_mode,
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return {"success": True, "data": _event_dict(event)}


@router.get("")
def list_events(db: Session = Depends(get_db)):
    events = db.query(Event).order_by(Event.created_at.desc()).all()
    return {"success": True, "data": {"events": [_event_dict(e) for e in events]}}


@router.get("/{event_id}")
def get_event(event_id: str, db: Session = Depends(get_db)):
    event = _get_event_or_404(event_id, db)
    return {"success": True, "data": _event_dict(event)}


@router.patch("/{event_id}")
def update_event(event_id: str, payload: dict, db: Session = Depends(get_db)):
    event = _get_event_or_404(event_id, db)
    if "status" in payload:
        if payload["status"] not in ("setup", "active", "complete"):
            raise HTTPException(status_code=422, detail="status must be setup, active, or complete")
        event.status = payload["status"]
    if "timing_mode" in payload:
        if payload["timing_mode"] not in ("human", "racespy"):
            raise HTTPException(status_code=422, detail="timing_mode must be human or racespy")
        event.timing_mode = payload["timing_mode"]
    if "name" in payload:
        event.name = payload["name"]
    db.commit()
    return {"success": True, "data": _event_dict(event)}


@router.patch("/{event_id}/status")
def update_event_status(event_id: str, payload: dict, db: Session = Depends(get_db)):
    event = _get_event_or_404(event_id, db)
    new_status = payload.get("status")
    if new_status not in ("setup", "active", "complete"):
        raise HTTPException(status_code=422, detail="status must be setup, active, or complete")
    event.status = new_status
    db.commit()
    return {"success": True, "data": _event_dict(event)}


# ---------------------------------------------------------------------------
# Run group routes
# ---------------------------------------------------------------------------

@router.post("/{event_id}/run-groups")
def create_run_group(event_id: str, payload: RunGroupCreateRequest, db: Session = Depends(get_db)):
    _get_event_or_404(event_id, db)
    rg = RunGroup(
        id=str(uuid.uuid4()),
        event_id=event_id,
        name=payload.name,
        order=payload.order or 0,
    )
    db.add(rg)
    db.commit()
    db.refresh(rg)
    return {"success": True, "data": _run_group_dict(rg, db)}


@router.get("/{event_id}/run-groups")
def list_run_groups(event_id: str, db: Session = Depends(get_db)):
    _get_event_or_404(event_id, db)
    groups = (
        db.query(RunGroup)
        .filter(RunGroup.event_id == event_id)
        .order_by(RunGroup.order)
        .all()
    )
    return {"success": True, "data": {"run_groups": [_run_group_dict(rg, db) for rg in groups]}}


@router.patch("/{event_id}/run-groups/{group_id}")
def update_run_group(
    event_id: str, group_id: str, payload: dict, db: Session = Depends(get_db)
):
    rg = _get_run_group_or_404(event_id, group_id, db)
    if "name" in payload:
        rg.name = payload["name"]
    if "order" in payload:
        rg.order = payload["order"]
    db.commit()
    return {"success": True, "data": _run_group_dict(rg, db)}


@router.delete("/{event_id}/run-groups/{group_id}")
def delete_run_group(event_id: str, group_id: str, db: Session = Depends(get_db)):
    rg = _get_run_group_or_404(event_id, group_id, db)
    count = db.query(Competitor).filter(Competitor.run_group_id == group_id).count()
    if count > 0:
        raise HTTPException(
            status_code=409,
            detail=f"Cannot delete run group with {count} assigned competitors. Move them first.",
        )
    db.delete(rg)
    db.commit()
    return {"success": True, "data": {"deleted_id": group_id}}


@router.post("/{event_id}/run-groups/bulk-assign")
def bulk_assign(event_id: str, payload: BulkAssignRequest, db: Session = Depends(get_db)):
    """Assign all competitors of each listed class to the specified run group."""
    _get_event_or_404(event_id, db)
    total_updated = 0
    for item in payload.assignments:
        class_code = item.get("class_code")
        run_group_id = item.get("run_group_id")
        if not class_code or not run_group_id:
            continue
        _get_run_group_or_404(event_id, run_group_id, db)
        updated = (
            db.query(Competitor)
            .filter(Competitor.event_id == event_id, Competitor.class_code == class_code)
            .update({"run_group_id": run_group_id})
        )
        total_updated += updated
    db.commit()
    return {"success": True, "data": {"competitors_updated": total_updated}}


@router.get("/{event_id}/run-groups/assignment-summary")
def assignment_summary(event_id: str, db: Session = Depends(get_db)):
    """Per-class summary used by the bulk assignment UI table."""
    _get_event_or_404(event_id, db)
    competitors = db.query(Competitor).filter(Competitor.event_id == event_id).all()

    summary: dict[str, dict] = {}
    for c in competitors:
        if c.class_code not in summary:
            summary[c.class_code] = {
                "class_code": c.class_code,
                "competitor_count": 0,
                "group_ids": set(),
            }
        summary[c.class_code]["competitor_count"] += 1
        if c.run_group_id:
            summary[c.class_code]["group_ids"].add(c.run_group_id)

    result = []
    for entry in sorted(summary.values(), key=lambda x: x["class_code"]):
        group_ids = entry.pop("group_ids")
        entry["assigned_group_id"] = next(iter(group_ids)) if len(group_ids) == 1 else None
        entry["split"] = len(group_ids) > 1
        result.append(entry)

    return {"success": True, "data": {"classes": result}}


# ---------------------------------------------------------------------------
# Competitor routes
# ---------------------------------------------------------------------------

@router.post("/{event_id}/competitors")
def create_competitor(event_id: str, payload: CompetitorCreateRequest, db: Session = Depends(get_db)):
    _get_event_or_404(event_id, db)
    if payload.run_group_id:
        _get_run_group_or_404(event_id, payload.run_group_id, db)
    comp = Competitor(
        id=str(uuid.uuid4()),
        event_id=event_id,
        number=payload.number,
        class_code=payload.class_code,
        driver_name=payload.driver_name,
        car_description=payload.car_description,
        run_group_id=payload.run_group_id,
    )
    db.add(comp)
    db.commit()
    db.refresh(comp)
    return {"success": True, "data": _competitor_dict(comp)}


@router.get("/{event_id}/competitors")
def list_competitors(
    event_id: str,
    run_group_id: Optional[str] = None,
    db: Session = Depends(get_db),
):
    _get_event_or_404(event_id, db)
    query = db.query(Competitor).filter(Competitor.event_id == event_id)
    if run_group_id:
        query = query.filter(Competitor.run_group_id == run_group_id)
    competitors = query.order_by(Competitor.class_code, Competitor.number).all()
    return {
        "success": True,
        "data": {"competitors": [_competitor_dict(c) for c in competitors]},
    }


@router.patch("/{event_id}/competitors/{competitor_id}")
def update_competitor(
    event_id: str,
    competitor_id: str,
    payload: CompetitorUpdateRequest,
    db: Session = Depends(get_db),
):
    comp = _get_competitor_or_404(event_id, competitor_id, db)
    if payload.run_group_id is not None:
        if payload.run_group_id:
            _get_run_group_or_404(event_id, payload.run_group_id, db)
        comp.run_group_id = payload.run_group_id or None
    if payload.number is not None:
        comp.number = payload.number
    if payload.class_code is not None:
        comp.class_code = payload.class_code
    if payload.driver_name is not None:
        comp.driver_name = payload.driver_name
    db.commit()
    db.refresh(comp)
    return {"success": True, "data": _competitor_dict(comp)}


@router.post("/{event_id}/competitors/import")
async def import_competitors_csv(
    event_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """Import competitors from a MotorsportsReg CSV export."""
    _get_event_or_404(event_id, db)

    content = await file.read()
    try:
        text = content.decode("utf-8-sig")  # strip BOM if present
    except UnicodeDecodeError:
        text = content.decode("latin-1")

    reader = csv.DictReader(io.StringIO(text))
    rows = list(reader)

    imported = 0
    skipped = 0
    errors = []

    for i, row in enumerate(rows):
        try:
            number = (row.get("No.") or "").strip()
            class_code = (row.get("Class") or "").strip()
            first = (row.get("First Name") or "").strip()
            last = (row.get("Last Name") or "").strip()
            driver_name = f"{first} {last}".strip() if first or last else "Unknown"
            car_desc = (row.get("Vehicle Year/Make/Model") or "").strip()

            if not number or not class_code:
                skipped += 1
                continue

            # Idempotent: skip if same number+class already exists for this event
            existing = db.query(Competitor).filter(
                Competitor.event_id == event_id,
                Competitor.number == number,
                Competitor.class_code == class_code,
            ).first()
            if existing:
                skipped += 1
                continue

            comp = Competitor(
                id=str(uuid.uuid4()),
                event_id=event_id,
                number=number,
                class_code=class_code,
                driver_name=driver_name,
                car_description=car_desc or None,
            )
            db.add(comp)
            imported += 1
        except Exception as e:
            errors.append(f"Row {i + 2}: {e}")

    db.commit()
    return {
        "success": True,
        "data": {"imported": imported, "skipped": skipped, "errors": errors},
    }


@router.delete("/{event_id}/competitors/{competitor_id}")
def delete_competitor(event_id: str, competitor_id: str, db: Session = Depends(get_db)):
    comp = _get_competitor_or_404(event_id, competitor_id, db)
    db.delete(comp)
    db.commit()
    return {"success": True, "data": {"deleted_id": competitor_id}}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_event_or_404(event_id: str, db: Session) -> Event:
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail=f"Event {event_id} not found")
    return event


def _get_run_group_or_404(event_id: str, group_id: str, db: Session) -> RunGroup:
    rg = db.query(RunGroup).filter(
        RunGroup.id == group_id, RunGroup.event_id == event_id
    ).first()
    if not rg:
        raise HTTPException(status_code=404, detail=f"RunGroup {group_id} not found")
    return rg


def _get_competitor_or_404(event_id: str, competitor_id: str, db: Session) -> Competitor:
    comp = db.query(Competitor).filter(
        Competitor.id == competitor_id, Competitor.event_id == event_id
    ).first()
    if not comp:
        raise HTTPException(status_code=404, detail=f"Competitor {competitor_id} not found")
    return comp


def _event_dict(e: Event) -> dict:
    return {
        "id": e.id,
        "name": e.name,
        "date": e.date.isoformat() if e.date else None,
        "status": e.status,
        "timing_mode": e.timing_mode,
        "created_at": e.created_at.isoformat() if e.created_at else None,
    }


def _run_group_dict(rg: RunGroup, db: Session) -> dict:
    count = db.query(Competitor).filter(Competitor.run_group_id == rg.id).count()
    return {
        "id": rg.id,
        "event_id": rg.event_id,
        "name": rg.name,
        "order": rg.order,
        "competitor_count": count,
    }


def _competitor_dict(c: Competitor) -> dict:
    rg_name = c.run_group.name if c.run_group else None
    return {
        "id": c.id,
        "event_id": c.event_id,
        "number": c.number,
        "class_code": c.class_code,
        "driver_name": c.driver_name,
        "car_description": c.car_description,
        "run_group_id": c.run_group_id,
        "run_group_name": rg_name,
    }
