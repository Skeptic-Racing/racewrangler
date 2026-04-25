"""Camera registration, live preview, and role assignment for RaceSpy devices."""
import time
from uuid import uuid4
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from models import Camera, Event, CameraTelemetry

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


class TelemetryGPSPayload(BaseModel):
    pps_lock: Optional[bool] = None
    pps_offset_us: Optional[float] = None
    gps_lock: Optional[bool] = None
    ntp_lock: Optional[bool] = None
    stratum: Optional[int] = None


class TelemetryHealthPayload(BaseModel):
    temperature_c: Optional[float] = None
    wifi_signal_dbm: Optional[int] = None
    memory_usage_percent: Optional[float] = None
    disk_usage_percent: Optional[float] = None
    uptime_seconds: Optional[int] = None


class CameraTelemetryRequest(BaseModel):
    camera_id: str
    event_id: str
    timestamp_utc_ms: int
    gps: TelemetryGPSPayload
    health: TelemetryHealthPayload
    buffered_payloads: int = 0


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


def _telemetry_alerts(t: CameraTelemetry, age_seconds: Optional[float]) -> list[str]:
    alerts: list[str] = []
    if age_seconds is not None and age_seconds > 120:
        alerts.append("stale_telemetry")

    # Time lock health
    if not (t.pps_lock or t.gps_lock or t.ntp_lock):
        alerts.append("no_time_lock")

    # Hardware and network thresholds from telemetry spec
    if t.temperature_c is not None and t.temperature_c > 75:
        alerts.append("high_temperature")
    if t.wifi_signal_dbm is not None and t.wifi_signal_dbm < -80:
        alerts.append("weak_wifi")
    if t.memory_usage_percent is not None and t.memory_usage_percent > 90:
        alerts.append("high_memory")
    if t.disk_usage_percent is not None and t.disk_usage_percent > 85:
        alerts.append("low_disk")
    if t.buffered_payloads > 10:
        alerts.append("high_buffered_payloads")

    return alerts


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
# Telemetry ingestion / queries
# ---------------------------------------------------------------------------

@router.post("/{camera_id}/telemetry")
def ingest_telemetry(camera_id: str, payload: CameraTelemetryRequest, db: Session = Depends(get_db)):
    """Best-effort telemetry ingest used for RaceSpy health monitoring."""
    if payload.camera_id != camera_id:
        raise HTTPException(status_code=400, detail="camera_id mismatch between path and payload")

    cam = db.query(Camera).filter(Camera.id == camera_id).first()
    if not cam:
        raise HTTPException(status_code=404, detail="Camera not found")

    if cam.event_id and cam.event_id != payload.event_id:
        raise HTTPException(status_code=409, detail="Event mismatch")

    telemetry = CameraTelemetry(
        id=str(uuid4()),
        camera_id=camera_id,
        event_id=payload.event_id,
        timestamp_utc_ms=payload.timestamp_utc_ms,
        pps_lock=payload.gps.pps_lock,
        pps_offset_us=payload.gps.pps_offset_us,
        gps_lock=payload.gps.gps_lock,
        ntp_lock=payload.gps.ntp_lock,
        stratum=payload.gps.stratum,
        temperature_c=payload.health.temperature_c,
        wifi_signal_dbm=payload.health.wifi_signal_dbm,
        memory_usage_percent=payload.health.memory_usage_percent,
        disk_usage_percent=payload.health.disk_usage_percent,
        uptime_seconds=payload.health.uptime_seconds,
        buffered_payloads=payload.buffered_payloads,
    )
    db.add(telemetry)

    # Treat telemetry as proof-of-life even if preview frames are unavailable.
    cam.last_seen_at = datetime.utcnow()
    db.commit()

    return {
        "status": "acknowledged",
        "camera_id": camera_id,
        "server_time_utc_ms": int(time.time() * 1000),
    }


@router.get("/telemetry/latest")
def list_latest_telemetry(event_id: Optional[str] = None, db: Session = Depends(get_db)):
    """Return the newest telemetry row per camera for dashboard/health use."""
    cameras_q = db.query(Camera)
    if event_id:
        cameras_q = cameras_q.filter(Camera.event_id == event_id)

    cameras = cameras_q.order_by(Camera.created_at).all()
    now_ms = int(time.time() * 1000)
    items = []

    for cam in cameras:
        telemetry_q = db.query(CameraTelemetry).filter(CameraTelemetry.camera_id == cam.id)
        if event_id:
            telemetry_q = telemetry_q.filter(CameraTelemetry.event_id == event_id)
        latest = telemetry_q.order_by(CameraTelemetry.timestamp_utc_ms.desc()).first()

        age_seconds = None
        alerts: list[str] = []
        if latest:
            age_seconds = max(0.0, (now_ms - latest.timestamp_utc_ms) / 1000.0)
            alerts = _telemetry_alerts(latest, age_seconds)

        items.append({
            "camera_id": cam.id,
            "event_id": latest.event_id if latest else cam.event_id,
            "last_telemetry_at_ms": latest.timestamp_utc_ms if latest else None,
            "telemetry_age_seconds": age_seconds,
            "stale": bool(age_seconds is not None and age_seconds > 120),
            "alerts": alerts,
            "gps": {
                "pps_lock": latest.pps_lock if latest else None,
                "pps_offset_us": latest.pps_offset_us if latest else None,
                "gps_lock": latest.gps_lock if latest else None,
                "ntp_lock": latest.ntp_lock if latest else None,
                "stratum": latest.stratum if latest else None,
            },
            "health": {
                "temperature_c": latest.temperature_c if latest else None,
                "wifi_signal_dbm": latest.wifi_signal_dbm if latest else None,
                "memory_usage_percent": latest.memory_usage_percent if latest else None,
                "disk_usage_percent": latest.disk_usage_percent if latest else None,
                "uptime_seconds": latest.uptime_seconds if latest else None,
            },
            "buffered_payloads": latest.buffered_payloads if latest else None,
        })

    return {"success": True, "data": {"telemetry": items}}


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
