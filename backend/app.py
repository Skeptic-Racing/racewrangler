from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os
from database import init_db, engine
from models import Base
from routes.runs import router as runs_router
from routes.cameras import router as cameras_router
from routes.events import router as events_router
from routes.timing_events import router as timing_events_router
from seed_data import seed_database

# Create FastAPI app
app = FastAPI(
    title="Race Wrangler API",
    description="Timing and scoring system for motorsports events",
    version="0.1.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for POC
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize database and OCR
@app.on_event("startup")
def startup_event():
    """Initialize database on startup."""
    init_db()
    seed_database()
    print("✓ Database initialized and seeded")

    from services.ocr_service import initialize_ocr
    initialize_ocr()


# Phase 0 POC routes (existing frontend)
app.include_router(runs_router, prefix="/api", tags=["runs"])

# Phase 1 hardware routes
app.include_router(cameras_router, prefix="/api/cameras", tags=["cameras"])
app.include_router(events_router, prefix="/api/v1/events", tags=["events"])

# Timing events are nested under /api/v1/events/{event_id}.
# FastAPI passes {event_id} from the prefix path into each handler automatically.
app.include_router(
    timing_events_router,
    prefix="/api/v1/events/{event_id}",
    tags=["timing"],
)

# Serve photos statically
photos_dir = os.path.join(os.path.dirname(__file__), "..", "storage", "photos")
os.makedirs(photos_dir, exist_ok=True)
app.mount("/photos", StaticFiles(directory=photos_dir), name="photos")


@app.get("/")
def read_root():
    """Root endpoint."""
    return {
        "message": "Race Wrangler API",
        "docs": "/docs",
        "endpoints": {
            "cars": "GET /api/cars",
            "start_run": "POST /api/start",
            "finish_run": "POST /api/finish",
            "list_runs": "GET /api/runs",
            "update_run": "POST /api/runs/{run_id}/update"
        }
    }


@app.get("/health")
def health():
    """Health check endpoint."""
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
