"""
Tests for patient API endpoints
"""
import pytest
from uuid import uuid4
import json


class TestPatientAPI:
    """Test patient API endpoints"""
    
    def test_create_patient_success(self, client, sample_patient_data):
        """Test successful patient creation via API"""
        response = client.post("/api/v1/patients/", json=sample_patient_data)
        
        assert response.status_code == 201
        data = response.json()
        assert data["success"] is True
        assert data["message"] == "Patient created successfully"
        assert data["patient"]["first_name"] == "John"
        assert data["patient"]["last_name"] == "Doe"
        assert data["patient"]["email"] == "john.doe@example.com"
        assert "patient_id" in data["patient"]
    
    def test_create_patient_invalid_data(self, client):
        """Test patient creation with invalid data"""
        invalid_data = {
            "first_name": "John",
            # Missing required last_name and date_of_birth
            "email": "invalid-email"  # Invalid email format
        }
        
        response = client.post("/api/v1/patients/", json=invalid_data)
        assert response.status_code == 422
    
    def test_create_patient_duplicate_email(self, client, sample_patient_data, create_test_patient, db_session):
        """Test creating patient with duplicate email"""
        # Create first patient
        create_test_patient(email="john.doe@example.com")
        
        # Try to create second patient with same email
        response = client.post("/api/v1/patients/", json=sample_patient_data)
        assert response.status_code == 422
        assert "already exists" in response.json()["detail"]
    
    def test_get_patient_success(self, client, create_test_patient, db_session):
        """Test successful patient retrieval by ID"""
        created_patient = create_test_patient()
        
        response = client.get(f"/api/v1/patients/{created_patient.patient_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["patient_id"] == str(created_patient.patient_id)
        assert data["first_name"] == created_patient.first_name
        assert data["last_name"] == created_patient.last_name
    
    def test_get_patient_not_found(self, client):
        """Test getting non-existent patient"""
        non_existent_id = uuid4()
        response = client.get(f"/api/v1/patients/{non_existent_id}")
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"]
    
    def test_get_patient_invalid_uuid(self, client):
        """Test getting patient with invalid UUID"""
        response = client.get("/api/v1/patients/invalid-uuid")
        assert response.status_code == 422
    
    def test_update_patient_success(self, client, create_test_patient, sample_patient_update_data, db_session):
        """Test successful patient update"""
        created_patient = create_test_patient()
        
        response = client.put(
            f"/api/v1/patients/{created_patient.patient_id}",
            json=sample_patient_update_data
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["first_name"] == "Jane"
        assert data["email"] == "jane.doe@example.com"
        assert data["patient_id"] == str(created_patient.patient_id)
    
    def test_update_patient_not_found(self, client, sample_patient_update_data):
        """Test updating non-existent patient"""
        non_existent_id = uuid4()
        response = client.put(
            f"/api/v1/patients/{non_existent_id}",
            json=sample_patient_update_data
        )
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"]
    
    def test_update_patient_invalid_data(self, client, create_test_patient, db_session):
        """Test updating patient with invalid data"""
        created_patient = create_test_patient()
        
        invalid_update = {
            "email": "invalid-email",
            "gender": "InvalidGender"
        }
        
        response = client.put(
            f"/api/v1/patients/{created_patient.patient_id}",
            json=invalid_update
        )
        
        assert response.status_code == 422
    
    def test_search_patients_no_criteria(self, client, create_test_patient, db_session):
        """Test searching patients with no criteria"""
        # Create test patients
        create_test_patient(first_name="John", last_name="Doe")
        create_test_patient(first_name="Jane", last_name="Smith")
        create_test_patient(first_name="Bob", last_name="Johnson", is_active=False)
        
        response = client.get("/api/v1/patients/search")
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["total"] == 2  # Only active patients
        assert len(data["patients"]) == 2
        assert data["page"] == 1
        assert data["size"] == 10
    
    def test_search_patients_by_name(self, client, create_test_patient, db_session):
        """Test searching patients by name"""
        create_test_patient(first_name="John", last_name="Doe")
        create_test_patient(first_name="Jane", last_name="Doe")
        create_test_patient(first_name="Bob", last_name="Smith")
        
        # Search by first name
        response = client.get("/api/v1/patients/search?first_name=John")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["patients"][0]["first_name"] == "John"
        
        # Search by last name
        response = client.get("/api/v1/patients/search?last_name=Doe")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert all(p["last_name"] == "Doe" for p in data["patients"])
    
    def test_search_patients_pagination(self, client, create_test_patient, db_session):
        """Test patient search pagination"""
        # Create 5 test patients
        for i in range(5):
            create_test_patient(first_name=f"Patient{i}")
        
        # Test first page
        response = client.get("/api/v1/patients/search?page=1&size=2")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 5
        assert len(data["patients"]) == 2
        assert data["page"] == 1
        assert data["pages"] == 3
        
        # Test second page
        response = client.get("/api/v1/patients/search?page=2&size=2")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 5
        assert len(data["patients"]) == 2
        assert data["page"] == 2
    
    def test_search_patients_invalid_pagination(self, client):
        """Test search with invalid pagination parameters"""
        # Invalid page (less than 1)
        response = client.get("/api/v1/patients/search?page=0")
        assert response.status_code == 422
        
        # Invalid size (greater than 100)
        response = client.get("/api/v1/patients/search?size=101")
        assert response.status_code == 422
    
    def test_deactivate_patient_success(self, client, create_test_patient, db_session):
        """Test successful patient deactivation"""
        created_patient = create_test_patient()
        
        response = client.delete(f"/api/v1/patients/{created_patient.patient_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "deactivated successfully" in data["message"]
        
        # Verify patient is deactivated
        get_response = client.get(f"/api/v1/patients/{created_patient.patient_id}")
        assert get_response.status_code == 404
    
    def test_deactivate_patient_not_found(self, client):
        """Test deactivating non-existent patient"""
        non_existent_id = uuid4()
        response = client.delete(f"/api/v1/patients/{non_existent_id}")
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"]
    
    def test_list_patients_success(self, client, create_test_patient, db_session):
        """Test listing all active patients"""
        # Create test patients
        create_test_patient(first_name="John", last_name="Doe")
        create_test_patient(first_name="Jane", last_name="Smith")
        create_test_patient(first_name="Bob", last_name="Johnson", is_active=False)
        
        response = client.get("/api/v1/patients/")
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["total"] == 2  # Only active patients
        assert len(data["patients"]) == 2
        assert all(p["is_active"] for p in data["patients"])
    
    def test_list_patients_pagination(self, client, create_test_patient, db_session):
        """Test listing patients with pagination"""
        # Create 3 test patients
        for i in range(3):
            create_test_patient(first_name=f"Patient{i}")
        
        response = client.get("/api/v1/patients/?page=1&size=2")
        
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 3
        assert len(data["patients"]) == 2
        assert data["page"] == 1
        assert data["pages"] == 2
    
    def test_api_root(self, client):
        """Test API root endpoint"""
        response = client.get("/api/v1/")
        assert response.status_code == 200
        data = response.json()
        assert "Hospital Management System API v1" in data["message"]


class TestPatientAPIErrorHandling:
    """Test error handling in patient API"""
    
    def test_internal_server_error_handling(self, client, monkeypatch):
        """Test handling of internal server errors"""
        # Mock the service to raise an exception
        def mock_create_patient(*args, **kwargs):
            raise Exception("Database connection failed")
        
        from app.services import patient
        monkeypatch.setattr(patient.PatientService, "create_patient", mock_create_patient)
        
        response = client.post("/api/v1/patients/", json={
            "first_name": "John",
            "last_name": "Doe",
            "date_of_birth": "1990-01-01"
        })
        
        assert response.status_code == 500
        assert "Internal server error" in response.json()["detail"]
    
    def test_validation_error_details(self, client):
        """Test that validation errors provide detailed information"""
        invalid_data = {
            "first_name": "",  # Too short
            "last_name": "Doe",
            "date_of_birth": "2030-01-01",  # Future date
            "email": "invalid-email",  # Invalid format
            "gender": "InvalidGender"  # Invalid value
        }
        
        response = client.post("/api/v1/patients/", json=invalid_data)
        assert response.status_code == 422
        
        # Should contain validation error details
        error_detail = response.json()["detail"]
        assert isinstance(error_detail, (str, list))  # FastAPI returns validation errors