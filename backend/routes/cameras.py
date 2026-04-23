"""Camera registration, live preview, and role assignment for RaceSpy devices."""
import time
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from models import Camera, Event

router = APIRouter()

# ---------------------------------------------------------------------------
# In-memory frame store
# Each entry: {"bytes": bytes, "timestamp": float (epoch seconds)}
# Ephemeral — lost on server restart. Only the latest frame per camera is kept.
# ---------------------------------------------------------------------------
_frames: dict[str, dict] = {}

_FRAME_TTL = 30.0   # seconds before a camera is considered offline


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class CameraRegisterRequest(BaseModel):
    camera_id: str
    firmware_version: Optional[str] = None
    # role and event_id are no longer set at boot — assigned by admin via /assign


class AssignRequest(BaseModel):
    role: str       # "start" | "finish"
    event_id: str


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _camera_to_response(cam: Camera) -> dict:
    return {
        "camera_id": cam.id,
        "role": cam.role,
        "event_id": cam.event_id,
        "status": cam.status,
        "firmware_version": cam.firmware_version,
        "last_seen_at": cam.last_seen_at.isoformat() if cam.last_seen_at else None,
        "has_preview": cam.id in _frames and (time.time() - _frames[cam.id]["timestamp"]) < _FRAME_TTL,
    }


def _get_cam_or_404(camera_id: str, db: Session) -> Camera:
    cam = db.query(Camera).filter(Camera.id == camera_id).first()
    if not cam:
        raise HTTPException(status_code=404, detail="Camera not found")
    return cam


# ---------------------------------------------------------------------------
# List / register
# ---------------------------------------------------------------------------

@router.get("")
def list_cameras(db: Session = Depends(get_db)):
    """List all cameras, including those seen in the last 30 seconds."""
    cameras = db.query(Camera).order_by(Camera.created_at).all()
    return {"success": True, "data": {"cameras": [_camera_to_response(c) for c in cameras]}}


@router.post("/register")
def register_camera(payload: CameraRegisterRequest, db: Session = Depends(get_db)):
    """
    Called by a RaceSpy at boot. Creates or updates the camera record.
    Role and event are assigned later via /assign — not at boot.
    """
    cam = db.query(Camera).filter(Camera.id == payload.camera_id).first()
    if cam is None:
        cam = Camera(id=payload.camera_id, status="pending")
        db.add(cam)

    cam.firmware_version = payload.firmware_version
    cam.last_seen_at = datetime.utcnow()
    # Only reset to pending if not already assigned
    if cam.status not in ("assigned", "active"):
        cam.status = "pending"

    db.commit()
    db.refresh(cam)

    return {
        "success": True,
        "data": {
            "status": cam.status,
            "role": cam.role,
            "event_id": cam.event_id,
        },
    }


# ---------------------------------------------------------------------------
# Frame push / preview (setup flow)
# ---------------------------------------------------------------------------

@router.post("/{camera_id}/frame")
async def push_frame(
    camera_id: str,
    image: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """
    Called repeatedly by the RaceSpy in preview mode.
    Stores the latest JPEG in memory and returns the camera's current assignment.
    """
    cam = db.query(Camera).filter(Camera.id == camera_id).first()
    if cam is None:
        # Auto-create on first frame so cameras don't need to register first
        cam = Camera(id=camera_id, status="pending")
        db.add(cam)

    frame_bytes = await image.read()
    _frames[camera_id] = {"bytes": frame_bytes, "timestamp": time.time()}

    cam.last_seen_at = datetime.utcnow()
    db.commit()

    if cam.status == "assigned" and cam.role and cam.event_id:
        return {"status": "assigned", "role": cam.role, "event_id": cam.event_id}

    return {"status": "pending", "role": None, "event_id": None}


@router.get("/{camera_id}/preview")
def get_preview(camera_id: str):
    """Return the latest JPEG frame for a camera. 404 if no frame received yet."""
    entry = _frames.get(camera_id)
    if not entry:
        raise HTTPException(status_code=404, detail="No preview available")
    return Response(content=entry["bytes"], media_type="image/jpeg")


# ---------------------------------------------------------------------------
# Admin assignment
# ---------------------------------------------------------------------------

@router.post("/{camera_id}/assign")
def assign_camera(
    camera_id: str,
    payload: AssignRequest,
    db: Session = Depends(get_db),
):
    """
    Admin assigns a role and event to a camera.
    The next /frame response will return status=assigned.
    """
    if payload.role not in ("start", "finish"):
        raise HTTPException(status_code=422, detail="role must be 'start' or 'finish'")

    event = db.query(Event).filter(Event.id == payload.event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail=f"Event {payload.event_id} not found")

    cam = db.query(Camera).filter(Camera.id == camera_id).first()
    if cam is None:
        cam = Camera(id=camera_id)
        db.add(cam)

    cam.event_id = payload.event_id
    cam.role = payload.role
    cam.status = "assigned"
    cam.last_seen_at = datetime.utcnow()

    db.commit()
    db.refresh(cam)

    return {"success": True, "data": _camera_to_response(cam)}


# ---------------------------------------------------------------------------
# Get / reset / keepalive (unchanged)
# ---------------------------------------------------------------------------

@router.get("/{camera_id}")
def get_camera(camera_id: str, db: Session = Depends(get_db)):
    cam = _get_cam_or_404(camera_id, db)
    return {"success": True, "data": _camera_to_response(cam)}


@router.post("/{camera_id}/reset")
def reset_camera(camera_id: str, db: Session = Depends(get_db)):
    """Reset camera back to pending so it re-enters preview mode."""
    cam = _get_cam_or_404(camera_id, db)
    cam.status = "pending"
    cam.role = None
    cam.event_id = None
    db.commit()
    db.refresh(cam)
    _frames.pop(camera_id, None)
    return {"success": True, "data": _camera_to_response(cam)}


@router.get("/{camera_id}/keepalive")
def camera_keepalive(camera_id: str, db: Session = Depends(get_db)):
    """Called by armed RaceSpies every 10s. Returns current status."""
    cam = _get_cam_or_404(camera_id, db)
    cam.last_seen_at = datetime.utcnow()
    db.commit()
    return {"success": True, "data": {"status": cam.status, "role": cam.role}}
