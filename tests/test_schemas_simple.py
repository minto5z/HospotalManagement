"""
Simple tests for patient schemas without database dependencies
"""
import pytest
from datetime import date
from pydantic import ValidationError

from app.schemas.patient import PatientCreate, PatientUpdate, PatientSearchCriteria


def test_patient_create_valid():
    """Test creating patient with valid data"""
    patient_data = {
        "first_name": "John",
        "last_name": "Doe",
        "date_of_birth": date(1990, 1, 1),
        "email": "john.doe@example.com"
    }
    patient = PatientCreate(**patient_data)
    assert patient.first_name == "John"
    assert patient.last_name == "Doe"
    assert patient.email == "john.doe@example.com"


def test_patient_create_required_fields():
    """Test that required fields are validated"""
    with pytest.raises(ValidationError):
        PatientCreate()


def test_patient_create_invalid_email():
    """Test email validation"""
    with pytest.raises(ValidationError):
        PatientCreate(
            first_name="John",
            last_name="Doe",
            date_of_birth=date(1990, 1, 1),
            email="invalid-email"
        )


def test_patient_create_future_birth_date():
    """Test future birth date validation"""
    with pytest.raises(ValidationError):
        PatientCreate(
            first_name="John",
            last_name="Doe",
            date_of_birth=date(2030, 1, 1)
        )


def test_patient_create_invalid_gender():
    """Test gender validation"""
    with pytest.raises(ValidationError):
        PatientCreate(
            first_name="John",
            last_name="Doe",
            date_of_birth=date(1990, 1, 1),
            gender="InvalidGender"
        )


def test_patient_update_partial():
    """Test partial patient update"""
    update_data = {
        "first_name": "Jane",
        "email": "jane.doe@example.com"
    }
    patient_update = PatientUpdate(**update_data)
    assert patient_update.first_name == "Jane"
    assert patient_update.email == "jane.doe@example.com"
    assert patient_update.last_name is None


def test_patient_search_criteria_defaults():
    """Test default search criteria values"""
    criteria = PatientSearchCriteria()
    assert criteria.is_active is True
    assert criteria.page == 1
    assert criteria.size == 10


def test_patient_search_criteria_pagination_validation():
    """Test pagination validation"""
    # Valid pagination
    criteria = PatientSearchCriteria(page=2, size=20)
    assert criteria.page == 2
    assert criteria.size == 20
    
    # Invalid page
    with pytest.raises(ValidationError):
        PatientSearchCriteria(page=0)
    
    # Invalid size
    with pytest.raises(ValidationError):
        PatientSearchCriteria(size=101)


if __name__ == "__main__":
    # Run tests directly
    test_patient_create_valid()
    test_patient_create_required_fields()
    test_patient_create_invalid_email()
    test_patient_create_future_birth_date()
    test_patient_create_invalid_gender()
    test_patient_update_partial()
    test_patient_search_criteria_defaults()
    test_patient_search_criteria_pagination_validation()
    print("All schema tests passed!")