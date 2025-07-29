"""
Analytics data models for Azure Synapse integration.
These models represent the transformed data structures for analytics and reporting.
"""
from datetime import datetime, date
from typing import Optional, List, Dict, Any
from uuid import UUID
from pydantic import BaseModel, Field
from enum import Enum


class AppointmentStatus(str, Enum):
    """Appointment status enumeration."""
    SCHEDULED = "Scheduled"
    COMPLETED = "Completed"
    CANCELLED = "Cancelled"
    NO_SHOW = "No-Show"


class ResourceType(str, Enum):
    """Resource type enumeration."""
    ROOM = "Room"
    EQUIPMENT = "Equipment"
    BED = "Bed"


class ResourceStatus(str, Enum):
    """Resource status enumeration."""
    AVAILABLE = "Available"
    OCCUPIED = "Occupied"
    MAINTENANCE = "Maintenance"


# Fact Table Models for Analytics

class FactAppointment(BaseModel):
    """Fact table model for appointment analytics."""
    appointment_key: Optional[int] = None
    patient_key: Optional[int] = None
    doctor_key: Optional[int] = None
    date_key: int
    time_key: int
    appointment_id: UUID
    patient_id: UUID
    doctor_id: UUID
    appointment_datetime: datetime
    duration: int
    status: AppointmentStatus
    wait_time: Optional[int] = None  # minutes
    show_status: str
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        use_enum_values = True


class FactResourceUtilization(BaseModel):
    """Fact table model for resource utilization analytics."""
    utilization_key: Optional[int] = None
    resource_key: Optional[int] = None
    date_key: int
    resource_id: UUID
    resource_type: ResourceType
    utilization_hours: float
    occupancy_rate: float
    total_assignments: int
    average_assignment_duration: Optional[float] = None  # hours

    class Config:
        use_enum_values = True


class FactDoctorUtilization(BaseModel):
    """Fact table model for doctor utilization analytics."""
    utilization_key: Optional[int] = None
    doctor_key: Optional[int] = None
    date_key: int
    doctor_id: UUID
    total_appointments: int
    completed_appointments: int
    cancelled_appointments: int
    no_show_appointments: int
    total_scheduled_hours: float
    actual_worked_hours: float
    utilization_rate: float
    patient_satisfaction_score: Optional[float] = None

    class Config:
        use_enum_values = True


# Dimension Table Models

class DimDoctor(BaseModel):
    """Dimension table model for doctor analytics."""
    doctor_key: Optional[int] = None
    doctor_id: UUID
    full_name: str
    first_name: str
    last_name: str
    specialization: str
    department: Optional[str] = None
    license_number: str
    is_active: bool
    created_at: datetime


class DimPatient(BaseModel):
    """Dimension table model for patient analytics."""
    patient_key: Optional[int] = None
    patient_id: UUID
    age_group: str  # "0-18", "19-35", "36-50", "51-65", "65+"
    gender: Optional[str] = None
    is_active: bool
    created_at: datetime


class DimResource(BaseModel):
    """Dimension table model for resource analytics."""
    resource_key: Optional[int] = None
    resource_id: UUID
    resource_name: str
    resource_type: ResourceType
    location: Optional[str] = None
    created_at: datetime

    class Config:
        use_enum_values = True


class DimDate(BaseModel):
    """Dimension table model for date analytics."""
    date_key: int
    full_date: date
    year: int
    quarter: int
    month: int
    month_name: str
    day: int
    day_of_week: int
    day_name: str
    is_weekend: bool
    is_holiday: bool


class DimTime(BaseModel):
    """Dimension table model for time analytics."""
    time_key: int
    hour: int
    minute: int
    time_period: str  # "Morning", "Afternoon", "Evening", "Night"
    is_business_hours: bool


# Aggregated Analytics Models

class DoctorUtilizationReport(BaseModel):
    """Doctor utilization analytics report model."""
    doctor_id: UUID
    doctor_name: str
    specialization: str
    department: Optional[str] = None
    period_start: date
    period_end: date
    total_appointments: int
    completed_appointments: int
    cancelled_appointments: int
    no_show_appointments: int
    completion_rate: float
    no_show_rate: float
    average_appointments_per_day: float
    total_scheduled_hours: float
    actual_worked_hours: float
    utilization_rate: float
    revenue_generated: Optional[float] = None


class AppointmentTrendsReport(BaseModel):
    """Appointment trends analytics report model."""
    period_start: date
    period_end: date
    total_appointments: int
    appointments_by_status: Dict[str, int]
    appointments_by_specialization: Dict[str, int]
    appointments_by_day_of_week: Dict[str, int]
    appointments_by_time_period: Dict[str, int]
    average_wait_time: Optional[float] = None
    peak_hours: List[int]
    busiest_days: List[str]
    growth_rate: Optional[float] = None  # compared to previous period


class ResourceUsageReport(BaseModel):
    """Resource usage analytics report model."""
    period_start: date
    period_end: date
    resources_by_type: Dict[str, int]
    total_utilization_hours: float
    average_occupancy_rate: float
    utilization_by_resource_type: Dict[str, float]
    peak_usage_hours: List[int]
    underutilized_resources: List[Dict[str, Any]]
    overutilized_resources: List[Dict[str, Any]]
    maintenance_hours: float
    availability_rate: float


# ETL Data Export Models

class AppointmentExport(BaseModel):
    """Model for exporting appointment data to Synapse."""
    appointment_id: UUID
    patient_id: UUID
    doctor_id: UUID
    appointment_datetime: datetime
    duration: int
    status: str
    notes: Optional[str] = None
    patient_age_group: str
    patient_gender: Optional[str] = None
    doctor_specialization: str
    doctor_department: Optional[str] = None
    wait_time: Optional[int] = None
    show_status: str
    created_at: datetime
    updated_at: Optional[datetime] = None


class ResourceUtilizationExport(BaseModel):
    """Model for exporting resource utilization data to Synapse."""
    resource_id: UUID
    resource_name: str
    resource_type: str
    location: Optional[str] = None
    date: date
    total_assignments: int
    total_occupied_hours: float
    occupancy_rate: float
    maintenance_hours: float
    availability_rate: float
    created_at: datetime


class DoctorPerformanceExport(BaseModel):
    """Model for exporting doctor performance data to Synapse."""
    doctor_id: UUID
    doctor_name: str
    specialization: str
    department: Optional[str] = None
    date: date
    total_appointments: int
    completed_appointments: int
    cancelled_appointments: int
    no_show_appointments: int
    total_scheduled_minutes: int
    actual_worked_minutes: int
    utilization_rate: float
    created_at: datetime


# Data Transformation Models

class PatientAgeGroup(BaseModel):
    """Model for patient age group calculation."""
    patient_id: UUID
    date_of_birth: date
    current_date: date = Field(default_factory=date.today)
    
    @property
    def age(self) -> int:
        """Calculate patient age."""
        return (self.current_date - self.date_of_birth).days // 365
    
    @property
    def age_group(self) -> str:
        """Determine age group category."""
        age = self.age
        if age <= 18:
            return "0-18"
        elif age <= 35:
            return "19-35"
        elif age <= 50:
            return "36-50"
        elif age <= 65:
            return "51-65"
        else:
            return "65+"


class TimeSlotAnalysis(BaseModel):
    """Model for time slot analysis."""
    hour: int
    minute: int
    
    @property
    def time_key(self) -> int:
        """Generate time key for dimension table."""
        return self.hour * 100 + self.minute
    
    @property
    def time_period(self) -> str:
        """Determine time period category."""
        if 6 <= self.hour < 12:
            return "Morning"
        elif 12 <= self.hour < 17:
            return "Afternoon"
        elif 17 <= self.hour < 21:
            return "Evening"
        else:
            return "Night"
    
    @property
    def is_business_hours(self) -> bool:
        """Check if time is within business hours (8 AM - 6 PM)."""
        return 8 <= self.hour < 18


class DateAnalysis(BaseModel):
    """Model for date analysis."""
    date: date
    
    @property
    def date_key(self) -> int:
        """Generate date key for dimension table."""
        return int(self.date.strftime("%Y%m%d"))
    
    @property
    def quarter(self) -> int:
        """Determine quarter of the year."""
        return (self.date.month - 1) // 3 + 1
    
    @property
    def is_weekend(self) -> bool:
        """Check if date is weekend."""
        return self.date.weekday() >= 5
    
    @property
    def day_name(self) -> str:
        """Get day name."""
        return self.date.strftime("%A")
    
    @property
    def month_name(self) -> str:
        """Get month name."""
        return self.date.strftime("%B")