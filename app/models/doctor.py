"""
Doctor model for hospital management system.
"""
from typing import Optional, List
from uuid import UUID, uuid4
from sqlalchemy import String, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.mssql import UNIQUEIDENTIFIER

from .base import Base, TimestampMixin


class Doctor(Base, TimestampMixin):
    """Doctor model representing hospital doctors."""
    
    __tablename__ = "doctors"
    
    # Primary key
    doctor_id: Mapped[UUID] = mapped_column(
        UNIQUEIDENTIFIER,
        primary_key=True,
        default=uuid4,
        nullable=False
    )
    
    # Personal information
    first_name: Mapped[str] = mapped_column(String(50), nullable=False)
    last_name: Mapped[str] = mapped_column(String(50), nullable=False)
    
    # Professional information
    specialization: Mapped[str] = mapped_column(String(100), nullable=False)
    license_number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    department: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    # Contact information
    phone_number: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    
    # Relationships
    appointments: Mapped[List["Appointment"]] = relationship(
        "Appointment",
        back_populates="doctor",
        cascade="all, delete-orphan"
    )
    schedules: Mapped[List["DoctorSchedule"]] = relationship(
        "DoctorSchedule",
        back_populates="doctor",
        cascade="all, delete-orphan"
    )
    
    def __repr__(self) -> str:
        return f"<Doctor(id={self.doctor_id}, name='{self.first_name} {self.last_name}', specialization='{self.specialization}')>"
    
    @property
    def full_name(self) -> str:
        """Return the doctor's full name."""
        return f"{self.first_name} {self.last_name}"
    
    def to_dict(self) -> dict:
        """Convert doctor to dictionary for serialization."""
        return {
            "doctor_id": str(self.doctor_id),
            "first_name": self.first_name,
            "last_name": self.last_name,
            "full_name": self.full_name,
            "specialization": self.specialization,
            "license_number": self.license_number,
            "department": self.department,
            "phone_number": self.phone_number,
            "email": self.email,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }