"""
Database models for the hospital management system.
"""
from .base import Base, TimestampMixin
from .patient import Patient
from .doctor import Doctor
from .appointment import Appointment
from .hospital_resource import HospitalResource
from .doctor_schedule import DoctorSchedule
from .user import User, UserRole
from .analytics import (
    FactAppointment, FactResourceUtilization, FactDoctorUtilization,
    DimDoctor, DimPatient, DimResource, DimDate, DimTime,
    DoctorUtilizationReport, AppointmentTrendsReport, ResourceUsageReport,
    AppointmentExport, ResourceUtilizationExport, DoctorPerformanceExport,
    PatientAgeGroup, TimeSlotAnalysis, DateAnalysis
)

__all__ = [
    "Base",
    "TimestampMixin",
    "Patient",
    "Doctor",
    "Appointment",
    "HospitalResource",
    "DoctorSchedule",
    "User",
    "UserRole",
    # Analytics models
    "FactAppointment",
    "FactResourceUtilization", 
    "FactDoctorUtilization",
    "DimDoctor",
    "DimPatient",
    "DimResource",
    "DimDate",
    "DimTime",
    "DoctorUtilizationReport",
    "AppointmentTrendsReport",
    "ResourceUsageReport",
    "AppointmentExport",
    "ResourceUtilizationExport",
    "DoctorPerformanceExport",
    "PatientAgeGroup",
    "TimeSlotAnalysis",
    "DateAnalysis",
]