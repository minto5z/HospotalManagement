"""
Patient schemas for request/response validation
"""
from datetime import date
from typing import Optional, List
from uuid import UUID
from pydantic import BaseModel, Field, validator
try:
    from pydantic import EmailStr
except ImportError:
    # Fallback if email-validator is not installed
    EmailStr = str
import re

from .base import BaseResponse, IDResponse


class PatientBase(BaseModel):
    """Base patient schema with common fields"""
    first_name: str = Field(..., min_length=1, max_length=50, description="Patient's first name")
    last_name: str = Field(..., min_length=1, max_length=50, description="Patient's last name")
    date_of_birth: date = Field(..., description="Patient's date of birth")
    gender: Optional[str] = Field(None, max_length=10, description="Patient's gender")
    phone_number: Optional[str] = Field(None, max_length=20, description="Patient's phone number")
    email: Optional[str] = Field(None, description="Patient's email address")
    address: Optional[str] = Field(None, max_length=500, description="Patient's address")
    emergency_contact: Optional[str] = Field(None, max_length=200, description="Emergency contact information")

    @validator('gender')
    def validate_gender(cls, v):
        if v is not None:
            valid_genders = ['Male', 'Female', 'Other', 'M', 'F']
            if v not in valid_genders:
                raise ValueError('Gender must be one of: Male, Female, Other, M, F')
        return v

    @validator('phone_number')
    def validate_phone_number(cls, v):
        if v is not None:
            # Basic phone number validation - allows various formats
            phone_pattern = re.compile(r'^[\+]?[1-9][\d\s\-\(\)]{7,15}$')
            if not phone_pattern.match(v.replace(' ', '').replace('-', '').replace('(', '').replace(')', '')):
                raise ValueError('Invalid phone number format')
        return v

    @validator('email')
    def validate_email(cls, v):
        if v is not None:
            import re
            email_pattern = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
            if not email_pattern.match(v):
                raise ValueError('Invalid email format')
        return v

    @validator('date_of_birth')
    def validate_date_of_birth(cls, v):
        from datetime import date
        if v > date.today():
            raise ValueError('Date of birth cannot be in the future')
        # Check if age is reasonable (not older than 150 years)
        age_years = (date.today() - v).days / 365.25
        if age_years > 150:
            raise ValueError('Date of birth indicates unrealistic age')
        return v


class PatientCreate(PatientBase):
    """Schema for creating a new patient"""
    pass


class PatientUpdate(BaseModel):
    """Schema for updating patient information"""
    first_name: Optional[str] = Field(None, min_length=1, max_length=50)
    last_name: Optional[str] = Field(None, min_length=1, max_length=50)
    date_of_birth: Optional[date] = None
    gender: Optional[str] = Field(None, max_length=10)
    phone_number: Optional[str] = Field(None, max_length=20)
    email: Optional[str] = None
    address: Optional[str] = Field(None, max_length=500)
    emergency_contact: Optional[str] = Field(None, max_length=200)
    is_active: Optional[bool] = None

    @validator('gender')
    def validate_gender(cls, v):
        if v is not None:
            valid_genders = ['Male', 'Female', 'Other', 'M', 'F']
            if v not in valid_genders:
                raise ValueError('Gender must be one of: Male, Female, Other, M, F')
        return v

    @validator('phone_number')
    def validate_phone_number(cls, v):
        if v is not None:
            phone_pattern = re.compile(r'^[\+]?[1-9][\d\s\-\(\)]{7,15}$')
            if not phone_pattern.match(v.replace(' ', '').replace('-', '').replace('(', '').replace(')', '')):
                raise ValueError('Invalid phone number format')
        return v

    @validator('email')
    def validate_email(cls, v):
        if v is not None:
            import re
            email_pattern = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
            if not email_pattern.match(v):
                raise ValueError('Invalid email format')
        return v

    @validator('date_of_birth')
    def validate_date_of_birth(cls, v):
        if v is not None:
            from datetime import date
            if v > date.today():
                raise ValueError('Date of birth cannot be in the future')
            age_years = (date.today() - v).days / 365.25
            if age_years > 150:
                raise ValueError('Date of birth indicates unrealistic age')
        return v


class PatientResponse(PatientBase):
    """Schema for patient response"""
    patient_id: UUID
    full_name: str
    is_active: bool
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    class Config:
        from_attributes = True


class PatientSearchCriteria(BaseModel):
    """Schema for patient search criteria"""
    patient_id: Optional[UUID] = None
    first_name: Optional[str] = Field(None, min_length=1, max_length=50)
    last_name: Optional[str] = Field(None, min_length=1, max_length=50)
    email: Optional[str] = None
    phone_number: Optional[str] = Field(None, max_length=20)
    is_active: Optional[bool] = True
    page: int = Field(1, ge=1, description="Page number")
    size: int = Field(10, ge=1, le=100, description="Page size")


class PatientCreateResponse(BaseResponse):
    """Response for patient creation"""
    patient: PatientResponse


class PatientListResponse(BaseResponse):
    """Response for patient list/search"""
    patients: List[PatientResponse]
    total: int
    page: int
    size: int
    pages: int