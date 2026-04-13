from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey
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
