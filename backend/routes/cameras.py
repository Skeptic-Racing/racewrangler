"""Camera registration and state management for RaceSpy devices."""
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional

from database import get_db
from models import Camera, Event

router = APIRouter()


class CameraRegisterRequest(BaseModel):
    camera_id: str
    role: str           # "start" | "finish"
    event_id: str
    firmware_version: Optional[str] = None


class CameraResponse(BaseModel):
    camera_id: str
    role: Optional[str]
    event_id: Optional[str]
    status: str
    firmware_version: Optional[str]
    last_seen_at: Optional[datetime]

    class Config:
        from_attributes = True


def _camera_to_response(cam: Camera) -> dict:
    return {
        "camera_id": cam.id,
        "role": cam.role,
        "event_id": cam.event_id,
        "status": cam.status,
        "firmware_version": cam.firmware_version,
        "last_seen_at": cam.last_seen_at.isoformat() if cam.last_seen_at else None,
    }


@router.get("")
def list_cameras(db: Session = Depends(get_db)):
    """List all registered cameras."""
    cameras = db.query(Camera).order_by(Camera.created_at).all()
    return {"success": True, "data": {"cameras": [_camera_to_response(c) for c in cameras]}}


@router.post("/register")
def register_camera(payload: CameraRegisterRequest, db: Session = Depends(get_db)):
    """
    Called by a RaceSpy at boot after scanning a role QR code.
    Idempotent: re-registering the same camera_id for the same event updates its role.
    Warns if camera is already active on a different event.
    """
    if payload.role not in ("start", "finish"):
        raise HTTPException(status_code=422, detail="role must be 'start' or 'finish'")

    event = db.query(Event).filter(Event.id == payload.event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail=f"Event {payload.event_id} not found")

    cam = db.query(Camera).filter(Camera.id == payload.camera_id).first()
    if cam is None:
        cam = Camera(id=payload.camera_id)
        db.add(cam)
    elif cam.event_id and cam.event_id != payload.event_id and cam.status == "active":
        # Camera is live on a different event — allow reassignment but flag it
        print(f"Warning: camera {payload.camera_id} reassigned from event {cam.event_id} to {payload.event_id}")

    cam.event_id = payload.event_id
    cam.role = payload.role
    cam.status = "registered"
    cam.firmware_version = payload.firmware_version
    cam.last_seen_at = datetime.utcnow()

    db.commit()
    db.refresh(cam)

    return {"success": True, "data": _camera_to_response(cam)}


@router.get("/{camera_id}")
def get_camera(camera_id: str, db: Session = Depends(get_db)):
    """Return current state of a RaceSpy camera."""
    cam = db.query(Camera).filter(Camera.id == camera_id).first()
    if not cam:
        raise HTTPException(status_code=404, detail="Camera not found")
    return {"success": True, "data": _camera_to_response(cam)}


@router.post("/{camera_id}/reset")
def reset_camera(camera_id: str, db: Session = Depends(get_db)):
    """
    Reset camera to Setup Mode (status=pending). The RaceSpy polls its own state
    on a keepalive; on next poll it will detect pending and re-enter QR scan mode.
    """
    cam = db.query(Camera).filter(Camera.id == camera_id).first()
    if not cam:
        raise HTTPException(status_code=404, detail="Camera not found")

    cam.status = "pending"
    cam.role = None
    db.commit()
    db.refresh(cam)

    return {"success": True, "data": _camera_to_response(cam)}


@router.get("/{camera_id}/keepalive")
def camera_keepalive(camera_id: str, db: Session = Depends(get_db)):
    """
    Called by armed RaceSpies every 10 seconds to update last_seen_at and check
    for remote reset. Returns current status so the firmware can act on pending.
    """
    cam = db.query(Camera).filter(Camera.id == camera_id).first()
    if not cam:
        raise HTTPException(status_code=404, detail="Camera not found")

    cam.last_seen_at = datetime.utcnow()
    db.commit()
    db.refresh(cam)

    return {"success": True, "data": {"status": cam.status, "role": cam.role}}
