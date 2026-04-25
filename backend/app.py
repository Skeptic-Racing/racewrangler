from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import asyncio
import os
from database import init_db, engine
from models import Base
from routes.runs import router as runs_router
from routes.cameras import router as cameras_router
from routes.events import router as events_router
from routes.timing_events import router as timing_events_router
from routes.staged_runs import router as staged_runs_router
from ws import manager as ws_manager
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
app.include_router(
    staged_runs_router,
    prefix="/api/v1/events/{event_id}",
    tags=["staged_runs"],
)

# Serve photos statically
photos_dir = os.path.join(os.path.dirname(__file__), "..", "storage", "photos")
os.makedirs(photos_dir, exist_ok=True)
app.mount("/photos", StaticFiles(directory=photos_dir), name="photos")


@app.get("/api/active-event")
def get_active_event(db=None):
    """Return the currently active event for all clients."""
    from database import SessionLocal
    from models import SystemState, Event
    db = SessionLocal()
    try:
        state = db.query(SystemState).filter(SystemState.id == 1).first()
        if not state or not state.active_event_id:
            return {"success": True, "data": {"event": None}}
        event = db.query(Event).filter(Event.id == state.active_event_id).first()
        if not event:
            return {"success": True, "data": {"event": None}}
        from routes.events import _event_dict
        return {"success": True, "data": {"event": _event_dict(event)}}
    finally:
        db.close()


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await ws_manager.connect(websocket)
    try:
        while True:
            # Keep connection alive; client sends pings, we echo them
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text('{"type":"pong"}')
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)


@app.get("/health")
def health():
    """Health check endpoint."""
    return {"status": "ok"}


# Serve the React frontend — must be mounted last so API routes take priority.
# FRONTEND_DIR can be overridden via environment variable for dev vs production.
_default_frontend = os.path.join(os.path.dirname(__file__), "..", "frontend", "dist")
frontend_dir = os.environ.get("FRONTEND_DIR", _default_frontend)

if os.path.isdir(frontend_dir):
    app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")
else:
    @app.get("/")
    def read_root():
        return {"message": "RaceWrangler API — frontend not built. Run: cd frontend && npm run build"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
