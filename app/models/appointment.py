"""
Appointment model for hospital management system.
"""
from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4
from sqlalchemy import String, Integer, DateTime, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.mssql import UNIQUEIDENTIFIER

from .base import Base, TimestampMixin


class Appointment(Base, TimestampMixin):
    """Appointment model representing patient-doctor appointments."""
    
    __tablename__ = "appointments"
    
    # Primary key
    appointment_id: Mapped[UUID] = mapped_column(
        UNIQUEIDENTIFIER,
        primary_key=True,
        default=uuid4,
        nullable=False
    )
    
    # Foreign keys
    patient_id: Mapped[UUID] = mapped_column(
        UNIQUEIDENTIFIER,
        ForeignKey("patients.patient_id"),
        nullable=False
    )
    doctor_id: Mapped[UUID] = mapped_column(
        UNIQUEIDENTIFIER,
        ForeignKey("doctors.doctor_id"),
        nullable=False
    )
    
    # Appointment details
    appointment_datetime: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    duration: Mapped[int] = mapped_column(Integer, default=30, nullable=False)  # minutes
    status: Mapped[str] = mapped_column(String(20), default="Scheduled", nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Relationships
    patient: Mapped["Patient"] = relationship("Patient", back_populates="appointments")
    doctor: Mapped["Doctor"] = relationship("Doctor", back_populates="appointments")
    
    def __repr__(self) -> str:
        return f"<Appointment(id={self.appointment_id}, patient_id={self.patient_id}, doctor_id={self.doctor_id}, datetime={self.appointment_datetime})>"
    
    @property
    def end_datetime(self) -> datetime:
        """Calculate the end datetime of the appointment."""
        from datetime import timedelta
        return self.appointment_datetime + timedelta(minutes=self.duration)
    
    def is_conflicting_with(self, other_datetime: datetime, other_duration: int = 30) -> bool:
        """Check if this appointment conflicts with another datetime and duration."""
        from datetime import timedelta
        
        other_end = other_datetime + timedelta(minutes=other_duration)
        
        # Check for overlap
        return not (self.end_datetime <= other_datetime or self.appointment_datetime >= other_end)
    
    def to_dict(self) -> dict:
        """Convert appointment to dictionary for serialization."""
        return {
            "appointment_id": str(self.appointment_id),
            "patient_id": str(self.patient_id),
            "doctor_id": str(self.doctor_id),
            "appointment_datetime": self.appointment_datetime.isoformat() if self.appointment_datetime else None,
            "end_datetime": self.end_datetime.isoformat(),
            "duration": self.duration,
            "status": self.status,
            "notes": self.notes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }