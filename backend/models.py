from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text, BigInteger, Date
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base


class Car(Base):
    """Car model - represents a competitor vehicle."""
    __tablename__ = "cars"

    id = Column(Integer, primary_key=True, index=True)
    number = Column(String(10), index=True, nullable=False)
    class_name = Column(String(50), nullable=False)
    model = Column(String(100), nullable=False)

    runs = relationship("Run", back_populates="car")


class Run(Base):
    """Run model - represents a single competitive attempt."""
    __tablename__ = "runs"

    id = Column(Integer, primary_key=True, index=True)
    car_id = Column(Integer, ForeignKey("cars.id"), nullable=False, index=True)
    
    # Timing
    start_time = Column(DateTime, nullable=False, default=datetime.utcnow)
    finish_time = Column(DateTime, nullable=True)
    raw_time = Column(Float, nullable=True)  # Computed: finish_time - start_time in seconds
    
    # Photos
    start_photo_url = Column(String(255), nullable=True)
    finish_photo_url = Column(String(255), nullable=True)
    
    # Penalties and status
    penalties = Column(Integer, default=0)  # Number of penalty units (e.g., cones)
    adjusted_time = Column(Float, nullable=True)  # Computed: raw_time + (penalties * 2.0)
    is_dnf = Column(Boolean, default=False)  # Did Not Finish
    is_aborted = Column(Boolean, default=False)  # Run aborted
    is_missed_trip = Column(Boolean, default=False)  # Finish lights missed/failed trip signal
    finish_confirmed = Column(Boolean, default=False)  # Finish has been confirmed by worker
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    car = relationship("Car", back_populates="runs")

    def compute_times(self):
        """Compute raw_time and adjusted_time based on start/finish times and penalties."""
        if self.finish_time and self.start_time:
            self.raw_time = (self.finish_time - self.start_time).total_seconds()
            self.adjusted_time = self.raw_time + (self.penalties * 2.0)
        return self


class SystemState(Base):
    """Singleton application state shared across devices."""
    __tablename__ = "system_state"

    id = Column(Integer, primary_key=True, default=1)
    is_start_held = Column(Boolean, default=False, nullable=False)
    finish_triggered_at = Column(DateTime, nullable=True)


# ---------------------------------------------------------------------------
# Phase 1 models
# ---------------------------------------------------------------------------

class Event(Base):
    """A timed motorsport event."""
    __tablename__ = "events"

    id = Column(String(36), primary_key=True)
    name = Column(String(200), nullable=False)
    date = Column(Date, nullable=True)
    status = Column(String(20), default="setup", nullable=False)  # setup | active | complete
    # human = manual start/finish buttons; racespy = RaceSpy triggers + staging worker
    timing_mode = Column(String(20), default="human", nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    run_groups = relationship("RunGroup", back_populates="event", cascade="all, delete-orphan")
    competitors = relationship("Competitor", back_populates="event", cascade="all, delete-orphan")
    timing_events = relationship("TimingEvent", back_populates="event", cascade="all, delete-orphan")
    staged_runs = relationship("StagedRun", back_populates="event", cascade="all, delete-orphan")


class RunGroup(Base):
    """A named group of competitors who run together in sequence."""
    __tablename__ = "run_groups"

    id = Column(String(36), primary_key=True)
    event_id = Column(String(36), ForeignKey("events.id"), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    order = Column(Integer, default=0, nullable=False)

    event = relationship("Event", back_populates="run_groups")
    competitors = relationship("Competitor", back_populates="run_group")


class Competitor(Base):
    """A driver+car combination entered in an event."""
    __tablename__ = "competitors"

    id = Column(String(36), primary_key=True)
    event_id = Column(String(36), ForeignKey("events.id"), nullable=False, index=True)
    number = Column(String(10), nullable=False)      # Preserves leading zeros (e.g. "007")
    class_code = Column(String(20), nullable=False)  # Normalized class code (e.g. "STR")
    driver_name = Column(String(200), nullable=False)
    car_description = Column(String(200), nullable=True)
    run_group_id = Column(String(36), ForeignKey("run_groups.id"), nullable=True, index=True)

    event = relationship("Event", back_populates="competitors")
    run_group = relationship("RunGroup", back_populates="competitors")


class Camera(Base):
    """A registered RaceSpy camera unit."""
    __tablename__ = "cameras"

    id = Column(String(36), primary_key=True)  # UUID from firmware config, stable across reboots
    event_id = Column(String(36), ForeignKey("events.id"), nullable=True, index=True)
    role = Column(String(10), nullable=True)    # start | finish | null
    # pending = waiting for QR scan; registered = QR scanned, not yet armed; armed = active
    status = Column(String(20), default="pending", nullable=False)
    firmware_version = Column(String(50), nullable=True)
    last_seen_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class TimingEvent(Base):
    """A raw timing capture POSTed by a RaceSpy camera."""
    __tablename__ = "timing_events"

    id = Column(String(36), primary_key=True)
    event_id = Column(String(36), ForeignKey("events.id"), nullable=False, index=True)
    camera_id = Column(String(36), ForeignKey("cameras.id"), nullable=False)
    role = Column(String(10), nullable=False)            # start | finish
    timestamp_utc_ms = Column(BigInteger, nullable=False)
    timestamp_monotonic_ns = Column(BigInteger, nullable=False)
    sequence_number = Column(Integer, nullable=False)
    image_path = Column(String(500), nullable=True)      # Path on disk; not stored as blob
    ocr_result_json = Column(Text, nullable=True)        # Full OCR output as JSON
    # auto = OCR matched; tentative = low confidence match; needs_review = human required
    match_status = Column(String(20), nullable=True)
    matched_competitor_id = Column(String(36), ForeignKey("competitors.id"), nullable=True)
    resolved_by = Column(String(10), nullable=True)      # ocr | human
    resolved_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    event = relationship("Event", back_populates="timing_events")


class StagedRun(Base):
    """A run created by the staging worker before the car enters the start gate."""
    __tablename__ = "staged_runs"

    id = Column(String(36), primary_key=True)
    event_id = Column(String(36), ForeignKey("events.id"), nullable=False, index=True)
    competitor_id = Column(String(36), ForeignKey("competitors.id"), nullable=True, index=True)
    # staged = waiting at start; running = start fired; finished = complete; dnf = did not finish
    status = Column(String(20), default="staged", nullable=False)
    image_path = Column(String(500), nullable=True)
    ocr_result_json = Column(Text, nullable=True)
    start_timing_event_id = Column(String(36), ForeignKey("timing_events.id"), nullable=True)
    finish_timing_event_id = Column(String(36), ForeignKey("timing_events.id"), nullable=True)
    start_time_utc_ms = Column(BigInteger, nullable=True)
    finish_time_utc_ms = Column(BigInteger, nullable=True)
    raw_time_ms = Column(BigInteger, nullable=True)   # finish - start in ms
    penalties = Column(Integer, default=0)
    staged_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    event = relationship("Event", back_populates="staged_runs")
    competitor = relationship("Competitor")
