import os
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, File, Form, UploadFile, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc, text
from models import Car, Run, SystemState
from schemas import (
    RunStartResponse,
    RunFinishResponse,
    RunResponse,
    RunUpdateRequest,
    CarResponse,
)
from database import get_db

router = APIRouter()

# Create storage directories if they don't exist
STORAGE_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "storage", "photos")
os.makedirs(os.path.join(STORAGE_DIR, "start"), exist_ok=True)
os.makedirs(os.path.join(STORAGE_DIR, "finish"), exist_ok=True)


def count_and_delete_photos(folder_name: str) -> int:
    """Delete all files in a photo folder and return count deleted."""
    folder_path = os.path.join(STORAGE_DIR, folder_name)
    deleted = 0
    if not os.path.isdir(folder_path):
        return deleted

    for name in os.listdir(folder_path):
        file_path = os.path.join(folder_path, name)
        if os.path.isfile(file_path):
            os.remove(file_path)
            deleted += 1
    return deleted


def delete_photo_by_url(photo_url: Optional[str]) -> None:
    """Delete a stored photo file if it exists."""
    if not photo_url or not photo_url.startswith("/photos/"):
        return

    relative_path = photo_url.removeprefix("/photos/")
    file_path = os.path.join(STORAGE_DIR, relative_path)
    if os.path.isfile(file_path):
        os.remove(file_path)


def save_photo(photo: UploadFile, photo_type: str) -> str:
    """Save an uploaded photo and return its relative path."""
    try:
        # Read the file content
        contents = photo.file.read()
        
        # Generate filename
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S_%f")
        filename = f"photo_{timestamp}.jpg"
        filepath = os.path.join(STORAGE_DIR, photo_type, filename)
        
        # Save file
        with open(filepath, "wb") as f:
            f.write(contents)
        
        # Return relative path for the API
        return f"/photos/{photo_type}/{filename}"
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save photo: {str(e)}")


def get_system_state(db: Session) -> SystemState:
    """Get or create the singleton system state row."""
    state = db.query(SystemState).filter(SystemState.id == 1).first()
    if state is None:
        state = SystemState(id=1, is_start_held=False, finish_triggered_at=None)
        db.add(state)
        db.flush()
    return state


def is_finish_trigger_active(state: SystemState) -> bool:
    """True when the finish trigger was raised in the last 5 seconds."""
    if not state.finish_triggered_at:
        return False
    return (datetime.utcnow() - state.finish_triggered_at).total_seconds() < 5


@router.get("/cars", response_model=list[CarResponse])
def get_cars(db: Session = Depends(get_db)):
    """Get all available cars."""
    cars = db.query(Car).order_by(Car.id).all()
    return cars


@router.post("/start", response_model=dict)
def start_run(
    car_id: int = Form(...),
    photo: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    Start a new run with a car and initial photo.
    
    Returns: { success: bool, data: RunStartResponse, error?: {...} }
    """
    try:
        # Verify car exists
        car = db.query(Car).filter(Car.id == car_id).first()
        if not car:
            return {
                "success": False,
                "error": {
                    "code": "NOT_FOUND",
                    "message": f"Car with id {car_id} not found"
                }
            }
        
        # Save photo
        photo_url = save_photo(photo, "start")
        
        # Create run
        run = Run(
            car_id=car_id,
            start_time=datetime.utcnow(),
            start_photo_url=photo_url,
            penalties=0,
            is_dnf=False,
            is_aborted=False,
            is_missed_trip=False,
            finish_confirmed=False
        )
        db.add(run)
        db.commit()
        db.refresh(run)
        
        return {
            "success": True,
            "data": RunStartResponse.model_validate(run).model_dump()
        }
    except Exception as e:
        db.rollback()
        return {
            "success": False,
            "error": {
                "code": "INTERNAL_ERROR",
                "message": str(e)
            }
        }


@router.post("/finish", response_model=dict)
def finish_run(
    run_id: int = Form(...),
    photo: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    Complete a run with finish photo and compute times.
    
    Returns: { success: bool, data: RunFinishResponse, error?: {...} }
    """
    try:
        state = get_system_state(db)

        # Find the run
        run = db.query(Run).filter(Run.id == run_id).first()
        if not run:
            return {
                "success": False,
                "error": {
                    "code": "NOT_FOUND",
                    "message": f"Run with id {run_id} not found"
                }
            }
        
        # Save photo
        photo_url = save_photo(photo, "finish")
        
        # Update run
        run.finish_time = state.finish_triggered_at or datetime.utcnow()
        run.finish_photo_url = photo_url
        run.finish_confirmed = True

        # Consume trigger after one confirmation.
        state.finish_triggered_at = None
        
        # Compute times
        run.compute_times()

        db.commit()
        db.refresh(run)
        
        return {
            "success": True,
            "data": RunFinishResponse.model_validate(run).model_dump()
        }
    except Exception as e:
        db.rollback()
        return {
            "success": False,
            "error": {
                "code": "INTERNAL_ERROR",
                "message": str(e)
            }
        }


@router.get("/runs", response_model=dict)
def list_runs(
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Get all runs, optionally filtered by status.
    Status options:
    - "active": not finished, not DNF, not aborted
    - "completed": finished OR DNF OR aborted
    
    Returns: { success: bool, data: { runs: [...] }, error?: {...} }
    """
    try:
        query = db.query(Run).options()
        
        # Filter by status
        if status == "active":
            query = query.filter(
                Run.finish_time == None,
                Run.is_dnf == False,
                Run.is_aborted == False,
            )
        elif status == "completed":
            query = query.filter(
                (Run.finish_time != None) |
                (Run.is_dnf == True) |
                (Run.is_aborted == True)
            )
        
        # Order by most recent first
        runs = query.order_by(desc(Run.created_at)).all()
        
        # Eager load car data
        for run in runs:
            _ = run.car  # Force load
        
        run_responses = [RunResponse.model_validate(run).model_dump() for run in runs]
        
        return {
            "success": True,
            "data": {
                "runs": run_responses
            }
        }
    except Exception as e:
        return {
            "success": False,
            "error": {
                "code": "INTERNAL_ERROR",
                "message": str(e)
            }
        }


@router.post("/runs/{run_id}/update", response_model=dict)
def update_run(
    run_id: int,
    update_data: RunUpdateRequest,
    db: Session = Depends(get_db)
):
    """
    Update run properties (penalties, DNF status, abort status).
    
    Returns: { success: bool, data: RunResponse, error?: {...} }
    """
    try:
        # Find the run
        run = db.query(Run).filter(Run.id == run_id).first()
        if not run:
            return {
                "success": False,
                "error": {
                    "code": "NOT_FOUND",
                    "message": f"Run with id {run_id} not found"
                }
            }
        
        # Update fields (only those provided)
        if update_data.penalties is not None:
            run.penalties = update_data.penalties
        if update_data.is_dnf is not None:
            run.is_dnf = update_data.is_dnf
        if update_data.is_aborted is not None:
            run.is_aborted = update_data.is_aborted
        if update_data.is_missed_trip is not None:
            run.is_missed_trip = update_data.is_missed_trip

        # Recompute times after penalties change
        run.compute_times()
        
        db.commit()
        db.refresh(run)
        
        return {
            "success": True,
            "data": RunResponse.model_validate(run).model_dump()
        }
    except Exception as e:
        db.rollback()
        return {
            "success": False,
            "error": {
                "code": "INTERNAL_ERROR",
                "message": str(e)
            }
        }


@router.post("/runs/release-start", response_model=dict)
def release_start_hold(db: Session = Depends(get_db)):
    """Release the global hold-start state so starts may resume."""
    try:
        state = get_system_state(db)
        state.is_start_held = False

        db.commit()

        return {
            "success": True,
            "data": {
                "is_start_held": state.is_start_held,
            }
        }
    except Exception as e:
        db.rollback()
        return {
            "success": False,
            "error": {
                "code": "INTERNAL_ERROR",
                "message": str(e)
            }
        }


@router.post("/runs/hold-start", response_model=dict)
def hold_start(db: Session = Depends(get_db)):
    """Set the global hold-start state so starters are blocked."""
    try:
        state = get_system_state(db)
        state.is_start_held = True

        db.commit()

        return {
            "success": True,
            "data": {
                "is_start_held": state.is_start_held,
            }
        }
    except Exception as e:
        db.rollback()
        return {
            "success": False,
            "error": {
                "code": "INTERNAL_ERROR",
                "message": str(e)
            }
        }


@router.get("/runs/hold-status", response_model=dict)
def hold_status(db: Session = Depends(get_db)):
    """Return the global hold-start state."""
    try:
        state = get_system_state(db)
        db.commit()

        return {
            "success": True,
            "data": {
                "is_start_held": state.is_start_held,
            }
        }
    except Exception as e:
        db.rollback()
        return {
            "success": False,
            "error": {
                "code": "INTERNAL_ERROR",
                "message": str(e)
            }
        }


@router.post("/runs/trigger-finish", response_model=dict)
def trigger_finish(db: Session = Depends(get_db)):
    """Raise a finish trigger event shared across devices."""
    try:
        state = get_system_state(db)
        state.finish_triggered_at = datetime.utcnow()

        db.commit()

        return {
            "success": True,
            "data": {
                "is_finish_triggered": True,
                "finish_triggered_at": state.finish_triggered_at.isoformat(),
            }
        }
    except Exception as e:
        db.rollback()
        return {
            "success": False,
            "error": {
                "code": "INTERNAL_ERROR",
                "message": str(e)
            }
        }


@router.get("/runs/finish-trigger-status", response_model=dict)
def finish_trigger_status(db: Session = Depends(get_db)):
    """Return whether the shared finish trigger is currently active."""
    try:
        state = get_system_state(db)
        active = is_finish_trigger_active(state)

        db.commit()

        return {
            "success": True,
            "data": {
                "is_finish_triggered": active,
                "finish_triggered_at": state.finish_triggered_at.isoformat() if state.finish_triggered_at else None,
            }
        }
    except Exception as e:
        db.rollback()
        return {
            "success": False,
            "error": {
                "code": "INTERNAL_ERROR",
                "message": str(e)
            }
        }


@router.delete("/runs/{run_id}", response_model=dict)
def delete_run(
    run_id: int,
    db: Session = Depends(get_db)
):
    """Delete a run and any stored photos for it."""
    try:
        run = db.query(Run).filter(Run.id == run_id).first()
        if not run:
            return {
                "success": False,
                "error": {
                    "code": "NOT_FOUND",
                    "message": f"Run with id {run_id} not found"
                }
            }

        delete_photo_by_url(run.start_photo_url)
        delete_photo_by_url(run.finish_photo_url)

        db.delete(run)
        db.commit()

        return {
            "success": True,
            "data": {
                "run_id": run_id,
            }
        }
    except Exception as e:
        db.rollback()
        return {
            "success": False,
            "error": {
                "code": "INTERNAL_ERROR",
                "message": str(e)
            }
        }


@router.post("/admin/reset", response_model=dict)
def admin_reset_data(db: Session = Depends(get_db)):
    """
    Reset run/event data for demos.

    - Deletes all runs
    - Deletes all start/finish photos
    - Resets run numbering sequence
    """
    try:
        state = get_system_state(db)
        runs_deleted = db.query(Run).delete(synchronize_session=False)
        photos_deleted = count_and_delete_photos("start") + count_and_delete_photos("finish")
        state.is_start_held = False
        state.finish_triggered_at = None

        # Best-effort sequence reset for SQLite when sequence tracking exists.
        try:
            db.execute(text("DELETE FROM sqlite_sequence WHERE name = 'runs'"))
        except Exception:
            # sqlite_sequence only exists when AUTOINCREMENT is used.
            pass

        db.commit()

        return {
            "success": True,
            "data": {
                "runs_deleted": runs_deleted,
                "photos_deleted": photos_deleted,
            }
        }
    except Exception as e:
        db.rollback()
        return {
            "success": False,
            "error": {
                "code": "INTERNAL_ERROR",
                "message": str(e)
            }
        }
