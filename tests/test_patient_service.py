"""
Tests for patient service layer
"""
import pytest
from datetime import date
from uuid import uuid4

from app.services.patient import PatientService
from app.schemas.patient import PatientCreate, PatientUpdate, PatientSearchCriteria
from app.models.patient import Patient


class TestPatientService:
    """Test PatientService methods"""
    
    def test_create_patient_success(self, db_session, sample_patient_data):
        """Test successful patient creation"""
        patient_data = PatientCreate(**sample_patient_data)
        patient = PatientService.create_patient(db_session, patient_data, "test_user", "127.0.0.1")
        
        assert patient.first_name == "John"
        assert patient.last_name == "Doe"
        assert patient.email == "john.doe@example.com"
        assert patient.is_active is True
        assert patient.patient_id is not None
    
    def test_create_patient_duplicate_email(self, db_session, sample_patient_data, create_test_patient):
        """Test creating patient with duplicate email"""
        # Create first patient
        create_test_patient(email="john.doe@example.com")
        
        # Try to create second patient with same email
        patient_data = PatientCreate(**sample_patient_data)
        with pytest.raises(ValueError, match="already exists"):
            PatientService.create_patient(db_session, patient_data, "test_user", "127.0.0.1")
    
    def test_get_patient_by_id_success(self, db_session, create_test_patient):
        """Test successful patient retrieval by ID"""
        created_patient = create_test_patient()
        
        retrieved_patient = PatientService.get_patient_by_id(
            db_session, created_patient.patient_id, "test_user", "127.0.0.1"
        )
        
        assert retrieved_patient is not None
        assert retrieved_patient.patient_id == created_patient.patient_id
        assert retrieved_patient.first_name == created_patient.first_name
    
    def test_get_patient_by_id_not_found(self, db_session):
        """Test patient retrieval with non-existent ID"""
        non_existent_id = uuid4()
        patient = PatientService.get_patient_by_id(
            db_session, non_existent_id, "test_user", "127.0.0.1"
        )
        assert patient is None
    
    def test_get_patient_by_id_inactive(self, db_session, create_test_patient):
        """Test that inactive patients are not retrieved"""
        created_patient = create_test_patient(is_active=False)
        
        retrieved_patient = PatientService.get_patient_by_id(
            db_session, created_patient.patient_id, "test_user", "127.0.0.1"
        )
        assert retrieved_patient is None
    
    def test_update_patient_success(self, db_session, create_test_patient, sample_patient_update_data):
        """Test successful patient update"""
        created_patient = create_test_patient()
        original_last_name = created_patient.last_name
        
        update_data = PatientUpdate(**sample_patient_update_data)
        updated_patient = PatientService.update_patient(
            db_session, created_patient.patient_id, update_data, "test_user", "127.0.0.1"
        )
        
        assert updated_patient is not None
        assert updated_patient.first_name == "Jane"  # Updated
        assert updated_patient.last_name == original_last_name  # Unchanged
        assert updated_patient.email == "jane.doe@example.com"  # Updated
    
    def test_update_patient_not_found(self, db_session, sample_patient_update_data):
        """Test updating non-existent patient"""
        non_existent_id = uuid4()
        update_data = PatientUpdate(**sample_patient_update_data)
        
        updated_patient = PatientService.update_patient(
            db_session, non_existent_id, update_data, "test_user", "127.0.0.1"
        )
        assert updated_patient is None
    
    def test_update_patient_duplicate_email(self, db_session, create_test_patient):
        """Test updating patient with duplicate email"""
        # Create two patients
        patient1 = create_test_patient(email="patient1@example.com")
        patient2 = create_test_patient(email="patient2@example.com")
        
        # Try to update patient2 with patient1's email
        update_data = PatientUpdate(email="patient1@example.com")
        with pytest.raises(ValueError, match="already exists"):
            PatientService.update_patient(
                db_session, patient2.patient_id, update_data, "test_user", "127.0.0.1"
            )
    
    def test_search_patients_no_criteria(self, db_session, create_test_patient):
        """Test searching patients with no specific criteria"""
        # Create test patients
        create_test_patient(first_name="John", last_name="Doe")
        create_test_patient(first_name="Jane", last_name="Smith")
        create_test_patient(first_name="Bob", last_name="Johnson", is_active=False)
        
        criteria = PatientSearchCriteria()
        patients, total = PatientService.search_patients(
            db_session, criteria, "test_user", "127.0.0.1"
        )
        
        # Should return only active patients
        assert total == 2
        assert len(patients) == 2
        assert all(p.is_active for p in patients)
    
    def test_search_patients_by_name(self, db_session, create_test_patient):
        """Test searching patients by name"""
        create_test_patient(first_name="John", last_name="Doe")
        create_test_patient(first_name="Jane", last_name="Doe")
        create_test_patient(first_name="Bob", last_name="Smith")
        
        # Search by first name
        criteria = PatientSearchCriteria(first_name="John")
        patients, total = PatientService.search_patients(
            db_session, criteria, "test_user", "127.0.0.1"
        )
        assert total == 1
        assert patients[0].first_name == "John"
        
        # Search by last name
        criteria = PatientSearchCriteria(last_name="Doe")
        patients, total = PatientService.search_patients(
            db_session, criteria, "test_user", "127.0.0.1"
        )
        assert total == 2
        assert all(p.last_name == "Doe" for p in patients)
    
    def test_search_patients_pagination(self, db_session, create_test_patient):
        """Test patient search pagination"""
        # Create 5 test patients
        for i in range(5):
            create_test_patient(first_name=f"Patient{i}")
        
        # Test first page
        criteria = PatientSearchCriteria(page=1, size=2)
        patients, total = PatientService.search_patients(
            db_session, criteria, "test_user", "127.0.0.1"
        )
        assert total == 5
        assert len(patients) == 2
        
        # Test second page
        criteria = PatientSearchCriteria(page=2, size=2)
        patients, total = PatientService.search_patients(
            db_session, criteria, "test_user", "127.0.0.1"
        )
        assert total == 5
        assert len(patients) == 2
        
        # Test last page
        criteria = PatientSearchCriteria(page=3, size=2)
        patients, total = PatientService.search_patients(
            db_session, criteria, "test_user", "127.0.0.1"
        )
        assert total == 5
        assert len(patients) == 1
    
    def test_search_patients_include_inactive(self, db_session, create_test_patient):
        """Test searching including inactive patients"""
        create_test_patient(first_name="Active", is_active=True)
        create_test_patient(first_name="Inactive", is_active=False)
        
        # Search only active (default)
        criteria = PatientSearchCriteria(is_active=True)
        patients, total = PatientService.search_patients(
            db_session, criteria, "test_user", "127.0.0.1"
        )
        assert total == 1
        assert patients[0].first_name == "Active"
        
        # Search only inactive
        criteria = PatientSearchCriteria(is_active=False)
        patients, total = PatientService.search_patients(
            db_session, criteria, "test_user", "127.0.0.1"
        )
        assert total == 1
        assert patients[0].first_name == "Inactive"
    
    def test_deactivate_patient_success(self, db_session, create_test_patient):
        """Test successful patient deactivation"""
        created_patient = create_test_patient()
        assert created_patient.is_active is True
        
        deactivated_patient = PatientService.deactivate_patient(
            db_session, created_patient.patient_id, "test_user", "127.0.0.1"
        )
        
        assert deactivated_patient is not None
        assert deactivated_patient.is_active is False
        assert deactivated_patient.patient_id == created_patient.patient_id
    
    def test_deactivate_patient_not_found(self, db_session):
        """Test deactivating non-existent patient"""
        non_existent_id = uuid4()
        result = PatientService.deactivate_patient(
            db_session, non_existent_id, "test_user", "127.0.0.1"
        )
        assert result is None
    
    def test_deactivate_already_inactive_patient(self, db_session, create_test_patient):
        """Test deactivating already inactive patient"""
        created_patient = create_test_patient(is_active=False)
        
        result = PatientService.deactivate_patient(
            db_session, created_patient.patient_id, "test_user", "127.0.0.1"
        )
        assert result is None
    
    def test_get_patient_by_email(self, db_session, create_test_patient):
        """Test getting patient by email"""
        created_patient = create_test_patient(email="test@example.com")
        
        retrieved_patient = PatientService.get_patient_by_email(db_session, "test@example.com")
        
        assert retrieved_patient is not None
        assert retrieved_patient.patient_id == created_patient.patient_id
        assert retrieved_patient.email == "test@example.com"
    
    def test_get_patient_by_email_not_found(self, db_session):
        """Test getting patient by non-existent email"""
        patient = PatientService.get_patient_by_email(db_session, "nonexistent@example.com")
        assert patient is None
    
    def test_get_patient_by_email_inactive(self, db_session, create_test_patient):
        """Test that inactive patients are not retrieved by email"""
        create_test_patient(email="inactive@example.com", is_active=False)
        
        patient = PatientService.get_patient_by_email(db_session, "inactive@example.com")
        assert patient is None