"""
Doctor Schedule model for hospital management system.
"""
from datetime import time
from typing import Optional
from uuid import UUID, uuid4
from sqlalchemy import Integer, Time, Boolean, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.mssql import UNIQUEIDENTIFIER

from .base import Base


class DoctorSchedule(Base):
    """Doctor Schedule model representing doctor availability."""
    
    __tablename__ = "doctor_schedules"
    
    # Primary key
    schedule_id: Mapped[UUID] = mapped_column(
        UNIQUEIDENTIFIER,
        primary_key=True,
        default=uuid4,
        nullable=False
    )
    
    # Foreign key
    doctor_id: Mapped[UUID] = mapped_column(
        UNIQUEIDENTIFIER,
        ForeignKey("doctors.doctor_id"),
        nullable=False
    )
    
    # Schedule details
    day_of_week: Mapped[int] = mapped_column(Integer, nullable=False)  # 0=Sunday, 1=Monday, etc.
    start_time: Mapped[time] = mapped_column(Time, nullable=False)
    end_time: Mapped[time] = mapped_column(Time, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    
    # Relationships
    doctor: Mapped["Doctor"] = relationship("Doctor", back_populates="schedules")
    
    def __repr__(self) -> str:
        days = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
        day_name = days[self.day_of_week] if 0 <= self.day_of_week <= 6 else "Unknown"
        return f"<DoctorSchedule(id={self.schedule_id}, doctor_id={self.doctor_id}, {day_name} {self.start_time}-{self.end_time})>"
    
    @property
    def day_name(self) -> str:
        """Return the name of the day of the week."""
        days = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
        return days[self.day_of_week] if 0 <= self.day_of_week <= 6 else "Unknown"
    
    def is_time_within_schedule(self, check_time: time) -> bool:
        """Check if a given time falls within this schedule."""
        return self.start_time <= check_time <= self.end_time
    
    def to_dict(self) -> dict:
        """Convert doctor schedule to dictionary for serialization."""
        return {
            "schedule_id": str(self.schedule_id),
            "doctor_id": str(self.doctor_id),
            "day_of_week": self.day_of_week,
            "day_name": self.day_name,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "is_active": self.is_active,
        }