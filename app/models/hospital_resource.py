"""
Hospital Resource model for hospital management system.
"""
from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4
from sqlalchemy import String, ForeignKey, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.mssql import UNIQUEIDENTIFIER

from .base import Base, TimestampMixin


class HospitalResource(Base, TimestampMixin):
    """Hospital Resource model representing rooms, equipment, and beds."""
    
    __tablename__ = "hospital_resources"
    
    # Primary key
    resource_id: Mapped[UUID] = mapped_column(
        UNIQUEIDENTIFIER,
        primary_key=True,
        default=uuid4,
        nullable=False
    )
    
    # Resource information
    resource_name: Mapped[str] = mapped_column(String(100), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(50), nullable=False)  # 'Room', 'Equipment', 'Bed'
    location: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    # Status and assignment
    status: Mapped[str] = mapped_column(String(20), default="Available", nullable=False)  # 'Available', 'Occupied', 'Maintenance'
    assigned_to_patient_id: Mapped[Optional[UUID]] = mapped_column(
        UNIQUEIDENTIFIER,
        ForeignKey("patients.patient_id"),
        nullable=True
    )
    assigned_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # Relationships
    assigned_patient: Mapped[Optional["Patient"]] = relationship(
        "Patient",
        back_populates="assigned_resources"
    )
    
    def __repr__(self) -> str:
        return f"<HospitalResource(id={self.resource_id}, name='{self.resource_name}', type='{self.resource_type}', status='{self.status}')>"
    
    def assign_to_patient(self, patient_id: UUID) -> None:
        """Assign this resource to a patient."""
        self.assigned_to_patient_id = patient_id
        self.assigned_at = datetime.utcnow()
        self.status = "Occupied"
    
    def release_from_patient(self) -> None:
        """Release this resource from patient assignment."""
        self.assigned_to_patient_id = None
        self.assigned_at = None
        self.status = "Available"
    
    @property
    def is_available(self) -> bool:
        """Check if the resource is available for assignment."""
        return self.status == "Available"
    
    def to_dict(self) -> dict:
        """Convert hospital resource to dictionary for serialization."""
        return {
            "resource_id": str(self.resource_id),
            "resource_name": self.resource_name,
            "resource_type": self.resource_type,
            "location": self.location,
            "status": self.status,
            "assigned_to_patient_id": str(self.assigned_to_patient_id) if self.assigned_to_patient_id else None,
            "assigned_at": self.assigned_at.isoformat() if self.assigned_at else None,
            "is_available": self.is_available,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }