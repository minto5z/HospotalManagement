"""
Patient model for hospital management system.
"""
from datetime import date
from typing import Optional, List
from uuid import UUID, uuid4
from sqlalchemy import String, Date, Boolean, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.mssql import UNIQUEIDENTIFIER

from .base import Base, TimestampMixin
from app.core.security import data_encryption


class Patient(Base, TimestampMixin):
    """Patient model representing hospital patients."""
    
    __tablename__ = "patients"
    
    # Primary key
    patient_id: Mapped[UUID] = mapped_column(
        UNIQUEIDENTIFIER,
        primary_key=True,
        default=uuid4,
        nullable=False
    )
    
    # Personal information
    first_name: Mapped[str] = mapped_column(String(50), nullable=False)
    last_name: Mapped[str] = mapped_column(String(50), nullable=False)
    date_of_birth: Mapped[date] = mapped_column(Date, nullable=False)
    gender: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    
    # Contact information
    phone_number: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    address: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    emergency_contact: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    
    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    
    # Relationships
    appointments: Mapped[List["Appointment"]] = relationship(
        "Appointment", 
        back_populates="patient",
        cascade="all, delete-orphan"
    )
    assigned_resources: Mapped[List["HospitalResource"]] = relationship(
        "HospitalResource",
        back_populates="assigned_patient"
    )
    
    def __repr__(self) -> str:
        return f"<Patient(id={self.patient_id}, name='{self.first_name} {self.last_name}')>"
    
    @property
    def full_name(self) -> str:
        """Return the patient's full name."""
        return f"{self.first_name} {self.last_name}"
    
    def encrypt_sensitive_data(self):
        """Encrypt sensitive patient data before storing in database."""
        try:
            if self.email:
                self.email = data_encryption.encrypt(self.email)
            if self.phone_number:
                self.phone_number = data_encryption.encrypt(self.phone_number)
            if self.address:
                self.address = data_encryption.encrypt(self.address)
            if self.emergency_contact:
                self.emergency_contact = data_encryption.encrypt(self.emergency_contact)
        except Exception as e:
            # Log error but don't fail the operation
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error encrypting patient data: {e}")
    
    def decrypt_sensitive_data(self):
        """Decrypt sensitive patient data after retrieving from database."""
        try:
            if self.email:
                self.email = data_encryption.decrypt(self.email)
            if self.phone_number:
                self.phone_number = data_encryption.decrypt(self.phone_number)
            if self.address:
                self.address = data_encryption.decrypt(self.address)
            if self.emergency_contact:
                self.emergency_contact = data_encryption.decrypt(self.emergency_contact)
        except Exception as e:
            # Log error but don't fail the operation
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error decrypting patient data: {e}")
    
    def to_dict(self) -> dict:
        """Convert patient to dictionary for serialization."""
        return {
            "patient_id": str(self.patient_id),
            "first_name": self.first_name,
            "last_name": self.last_name,
            "full_name": self.full_name,
            "date_of_birth": self.date_of_birth.isoformat() if self.date_of_birth else None,
            "gender": self.gender,
            "phone_number": self.phone_number,
            "email": self.email,
            "address": self.address,
            "emergency_contact": self.emergency_contact,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }