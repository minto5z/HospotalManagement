"""
Tests for patient schemas
"""
import pytest
from datetime import date
from pydantic import ValidationError

from app.schemas.patient import PatientCreate, PatientUpdate, PatientResponse, PatientSearchCriteria


class TestPatientCreate:
    """Test PatientCreate schema validation"""
    
    def test_valid_patient_creation(self, sample_patient_data):
        """Test creating patient with valid data"""
        patient = PatientCreate(**sample_patient_data)
        assert patient.first_name == "John"
        assert patient.last_name == "Doe"
        assert patient.email == "john.doe@example.com"
        assert patient.date_of_birth == date(1990, 1, 1)
    
    def test_required_fields_validation(self):
        """Test that required fields are validated"""
        with pytest.raises(ValidationError) as exc_info:
            PatientCreate()
        
        errors = exc_info.value.errors()
        required_fields = {'first_name', 'last_name', 'date_of_birth'}
        error_fields = {error['loc'][0] for error in errors}
        assert required_fields.issubset(error_fields)
    
    def test_email_validation(self):
        """Test email format validation"""
        # Valid email
        valid_data = {
            "first_name": "John",
            "last_name": "Doe",
            "date_of_birth": date(1990, 1, 1),
            "email": "john.doe@example.com"
        }
        patient = PatientCreate(**valid_data)
        assert patient.email == "john.doe@example.com"
        
        # Invalid email
        invalid_data = valid_data.copy()
        invalid_data["email"] = "invalid-email"
        with pytest.raises(ValidationError):
            PatientCreate(**invalid_data)
    
    def test_phone_number_validation(self):
        """Test phone number format validation"""
        base_data = {
            "first_name": "John",
            "last_name": "Doe",
            "date_of_birth": date(1990, 1, 1)
        }
        
        # Valid phone numbers
        valid_phones = ["+1234567890", "1234567890", "+1-234-567-8900", "(123) 456-7890"]
        for phone in valid_phones:
            data = base_data.copy()
            data["phone_number"] = phone
            patient = PatientCreate(**data)
            assert patient.phone_number == phone
        
        # Invalid phone numbers
        invalid_phones = ["123", "abc123", "123-abc-7890"]
        for phone in invalid_phones:
            data = base_data.copy()
            data["phone_number"] = phone
            with pytest.raises(ValidationError):
                PatientCreate(**data)
    
    def test_gender_validation(self):
        """Test gender field validation"""
        base_data = {
            "first_name": "John",
            "last_name": "Doe",
            "date_of_birth": date(1990, 1, 1)
        }
        
        # Valid genders
        valid_genders = ["Male", "Female", "Other", "M", "F"]
        for gender in valid_genders:
            data = base_data.copy()
            data["gender"] = gender
            patient = PatientCreate(**data)
            assert patient.gender == gender
        
        # Invalid gender
        data = base_data.copy()
        data["gender"] = "Invalid"
        with pytest.raises(ValidationError):
            PatientCreate(**data)
    
    def test_date_of_birth_validation(self):
        """Test date of birth validation"""
        base_data = {
            "first_name": "John",
            "last_name": "Doe"
        }
        
        # Valid date of birth
        data = base_data.copy()
        data["date_of_birth"] = date(1990, 1, 1)
        patient = PatientCreate(**data)
        assert patient.date_of_birth == date(1990, 1, 1)
        
        # Future date of birth (invalid)
        data = base_data.copy()
        data["date_of_birth"] = date(2030, 1, 1)
        with pytest.raises(ValidationError):
            PatientCreate(**data)
        
        # Very old date of birth (invalid)
        data = base_data.copy()
        data["date_of_birth"] = date(1800, 1, 1)
        with pytest.raises(ValidationError):
            PatientCreate(**data)


class TestPatientUpdate:
    """Test PatientUpdate schema validation"""
    
    def test_partial_update(self):
        """Test updating only some fields"""
        update_data = {
            "first_name": "Jane",
            "email": "jane.doe@example.com"
        }
        patient_update = PatientUpdate(**update_data)
        assert patient_update.first_name == "Jane"
        assert patient_update.email == "jane.doe@example.com"
        assert patient_update.last_name is None
    
    def test_empty_update(self):
        """Test empty update (should be valid)"""
        patient_update = PatientUpdate()
        assert patient_update.first_name is None
        assert patient_update.last_name is None
    
    def test_validation_on_provided_fields(self):
        """Test that validation applies to provided fields"""
        # Invalid email
        with pytest.raises(ValidationError):
            PatientUpdate(email="invalid-email")
        
        # Invalid gender
        with pytest.raises(ValidationError):
            PatientUpdate(gender="Invalid")
        
        # Future date of birth
        with pytest.raises(ValidationError):
            PatientUpdate(date_of_birth=date(2030, 1, 1))


class TestPatientSearchCriteria:
    """Test PatientSearchCriteria schema validation"""
    
    def test_default_values(self):
        """Test default search criteria values"""
        criteria = PatientSearchCriteria()
        assert criteria.is_active is True
        assert criteria.page == 1
        assert criteria.size == 10
    
    def test_pagination_validation(self):
        """Test pagination parameter validation"""
        # Valid pagination
        criteria = PatientSearchCriteria(page=2, size=20)
        assert criteria.page == 2
        assert criteria.size == 20
        
        # Invalid page (less than 1)
        with pytest.raises(ValidationError):
            PatientSearchCriteria(page=0)
        
        # Invalid size (greater than 100)
        with pytest.raises(ValidationError):
            PatientSearchCriteria(size=101)
        
        # Invalid size (less than 1)
        with pytest.raises(ValidationError):
            PatientSearchCriteria(size=0)
    
    def test_search_fields(self):
        """Test search field validation"""
        criteria = PatientSearchCriteria(
            first_name="John",
            last_name="Doe",
            email="john@example.com"
        )
        assert criteria.first_name == "John"
        assert criteria.last_name == "Doe"
        assert criteria.email == "john@example.com"


class TestPatientResponse:
    """Test PatientResponse schema"""
    
    def test_patient_response_creation(self):
        """Test creating patient response from model"""
        from uuid import uuid4
        
        # Mock patient data
        patient_data = {
            "patient_id": uuid4(),
            "first_name": "John",
            "last_name": "Doe",
            "full_name": "John Doe",
            "date_of_birth": date(1990, 1, 1),
            "gender": "Male",
            "phone_number": "+1234567890",
            "email": "john.doe@example.com",
            "address": "123 Main St",
            "emergency_contact": "Jane Doe",
            "is_active": True,
            "created_at": "2023-01-01T00:00:00",
            "updated_at": "2023-01-01T00:00:00"
        }
        
        response = PatientResponse(**patient_data)
        assert response.first_name == "John"
        assert response.last_name == "Doe"
        assert response.full_name == "John Doe"
        assert response.is_active is True