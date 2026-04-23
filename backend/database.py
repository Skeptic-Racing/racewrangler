import os
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker, declarative_base

# Create database URL
DATABASE_URL = "sqlite:///./race_wrangler.db"
if os.getenv("TEST_MODE"):
    DATABASE_URL = "sqlite:///:memory:"

# Create engine
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {},
    echo=False
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base for declarative models
Base = declarative_base()


def get_db():
    """Dependency for FastAPI to provide database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Initialize database tables."""
    Base.metadata.create_all(bind=engine)

    # Lightweight migration for existing local DBs.
    inspector = inspect(engine)
    if "runs" in inspector.get_table_names():
        run_columns = {col["name"] for col in inspector.get_columns("runs")}
        if "is_missed_trip" not in run_columns:
            with engine.begin() as conn:
                conn.execute(text("ALTER TABLE runs ADD COLUMN is_missed_trip BOOLEAN DEFAULT 0"))

    if "system_state" in inspector.get_table_names():
        state_columns = {col["name"] for col in inspector.get_columns("system_state")}
        if "finish_triggered_at" not in state_columns:
            with engine.begin() as conn:
                conn.execute(text("ALTER TABLE system_state ADD COLUMN finish_triggered_at DATETIME"))

    if "events" in inspector.get_table_names():
        event_columns = {col["name"] for col in inspector.get_columns("events")}
        if "timing_mode" not in event_columns:
            with engine.begin() as conn:
                conn.execute(text("ALTER TABLE events ADD COLUMN timing_mode VARCHAR(20) NOT NULL DEFAULT 'human'"))
