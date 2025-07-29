"""
Integration tests for the complete patient workflow.
Tests the entire flow from API endpoints to database operations.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
import uuid
from datetime import datetime, timedelta

from app.main import app
from app.db.database import get_db
from app.models.patient import Patient
from app.models.user import User
from app.core.security import create_access_token
from tests.conftest import override_get_db


@pytest.fixture
def client():
    """Test client with database dependency override"""
    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app)


@pytest.fixture
def test_db():
    """Get test database session"""
    return next(override_get_db())


@pytest.fixture
def admin_token(test_db: Session):
    """Create admin user and generate token"""
    # Create admin user if not exists
    admin_user = test_db.query(User).filter(User.username == "admin_test").first()
    if not admin_user:
        admin_user = User(
            user_id=uuid.uuid4(),
            username="admin_test",
            email="admin@test.com",
            hashed_password="$2b$12$CwIlIVhkwGnH.HL5K9vHieuQB96XKR5L1UT9bZAQB7LAKbC2Kl9Uy",  # hashed "password"
            role="admin",
            is_active=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        test_db.add(admin_user)
        test_db.commit()
        test_db.refresh(admin_user)
    
    # Generate token
    access_token = create_access_token(
        data={"sub": admin_user.username, "user_id": str(admin_user.user_id), "role": admin_user.role}
    )
    return access_token


@pytest.fixture
def staff_token(test_db: Session):
    """Create medical staff user and generate token"""
    # Create staff user if not exists
    staff_user = test_db.query(User).filter(User.username == "staff_test").first()
    if not staff_user:
        staff_user = User(
            user_id=uuid.uuid4(),
            username="staff_test",
            email="staff@test.com",
            hashed_password="$2b$12$CwIlIVhkwGnH.HL5K9vHieuQB96XKR5L1UT9bZAQB7LAKbC2Kl9Uy",  # hashed "password"
            role="medical_staff",
            is_active=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        test_db.add(staff_user)
        test_db.commit()
        test_db.refresh(staff_user)
    
    # Generate token
    access_token = create_access_token(
        data={"sub": staff_user.username, "user_id": str(staff_user.user_id), "role": staff_user.role}
    )
    return access_token


class TestPatientWorkflow:
    """Test the complete patient workflow from API to database"""
    
    def test_complete_patient_lifecycle(self, client, test_db, staff_token):
        """Test the complete lifecycle of a patient record"""
        # 1. Create a new patient
        patient_data = {
            "first_name": "John",
            "last_name": "Integration",
            "date_of_birth": (datetime.utcnow() - timedelta(days=365*30)).date().isoformat(),
            "gender": "male",
            "phone_number": "555-1234",
            "email": "john.integration@example.com",
            "address": "123 Test St, Test City",
            "emergency_contact": {
                "name": "Jane Integration",
                "relationship": "Spouse",
                "phone_number": "555-5678"
            }
        }
        
        # Create patient through API
        create_response = client.post(
            "/api/v1/patients/",
            json=patient_data,
            headers={"Authorization": f"Bearer {staff_token}"}
        )
        
        # Verify API response
        assert create_response.status_code == 201
        created_patient = create_response.json()["patient"]
        assert created_patient["first_name"] == patient_data["first_name"]
        assert created_patient["last_name"] == patient_data["last_name"]
        
        # Verify database state
        patient_id = created_patient["patient_id"]
        db_patient = test_db.query(Patient).filter(Patient.patient_id == patient_id).first()
        assert db_patient is not None
        assert db_patient.first_name == patient_data["first_name"]
        assert db_patient.last_name == patient_data["last_name"]
        
        # 2. Retrieve the patient by ID
        get_response = client.get(
            f"/api/v1/patients/{patient_id}",
            headers={"Authorization": f"Bearer {staff_token}"}
        )
        
        # Verify retrieval
        assert get_response.status_code == 200
        retrieved_patient = get_response.json()
        assert retrieved_patient["patient_id"] == patient_id
        assert retrieved_patient["first_name"] == patient_data["first_name"]
        
        # 3. Update the patient
        update_data = {
            "first_name": "Johnny",
            "phone_number": "555-9876",
            "emergency_contact": {
                "name": "Jane Integration",
                "relationship": "Spouse",
                "phone_number": "555-8765"
            }
        }
        
        update_response = client.put(
            f"/api/v1/patients/{patient_id}",
            json=update_data,
            headers={"Authorization": f"Bearer {staff_token}"}
        )
        
        # Verify update
        assert update_response.status_code == 200
        updated_patient = update_response.json()
        assert updated_patient["first_name"] == update_data["first_name"]
        assert updated_patient["phone_number"] == update_data["phone_number"]
        
        # Verify database state after update
        test_db.refresh(db_patient)
        assert db_patient.first_name == update_data["first_name"]
        assert db_patient.phone_number == update_data["phone_number"]
        
        # 4. Search for the patient
        search_response = client.get(
            "/api/v1/patients/search",
            params={"last_name": "Integration"},
            headers={"Authorization": f"Bearer {staff_token}"}
        )
        
        # Verify search results
        assert search_response.status_code == 200
        search_results = search_response.json()
        assert search_results["total"] >= 1
        assert any(p["patient_id"] == patient_id for p in search_results["patients"])
        
        # 5. Deactivate (soft delete) the patient
        deactivate_response = client.delete(
            f"/api/v1/patients/{patient_id}",
            headers={"Authorization": f"Bearer {staff_token}"}
        )
        
        # Verify deactivation
        assert deactivate_response.status_code == 200
        assert deactivate_response.json()["success"] is True
        
        # Verify database state after deactivation
        test_db.refresh(db_patient)
        assert db_patient.is_active is False
        
        # 6. Verify the patient doesn't appear in default active patient list
        list_response = client.get(
            "/api/v1/patients/",
            headers={"Authorization": f"Bearer {staff_token}"}
        )
        
        assert list_response.status_code == 200
        list_results = list_response.json()
        assert not any(p["patient_id"] == patient_id for p in list_results["patients"])
    
    def test_error_handling_invalid_input(self, client, staff_token):
        """Test error handling for invalid input"""
        # Invalid patient data (missing required fields)
        invalid_patient = {
            "first_name": "",  # Empty first name
            "gender": "invalid_gender"  # Invalid enum value
        }
        
        # Attempt to create with invalid data
        response = client.post(
            "/api/v1/patients/",
            json=invalid_patient,
            headers={"Authorization": f"Bearer {staff_token}"}
        )
        
        # Verify validation error response
        assert response.status_code == 422
        error_detail = response.json()
        assert "detail" in error_detail
    
    def test_authorization_controls(self, client, test_db):
        """Test authorization controls for patient endpoints"""
        # Attempt to access without token
        response = client.get("/api/v1/patients/")
        assert response.status_code == 401
        
        # Attempt to access with invalid token
        response = client.get(
            "/api/v1/patients/",
            headers={"Authorization": "Bearer invalid_token"}
        )
        assert response.status_code == 401
    
    def test_data_consistency_across_endpoints(self, client, test_db, staff_token):
        """Test data consistency across different endpoints"""
        # Create a test patient
        patient_data = {
            "first_name": "Data",
            "last_name": "Consistency",
            "date_of_birth": "1990-01-01",
            "gender": "female"
        }
        
        # Create through API
        create_response = client.post(
            "/api/v1/patients/",
            json=patient_data,
            headers={"Authorization": f"Bearer {staff_token}"}
        )
        
        patient_id = create_response.json()["patient"]["patient_id"]
        
        # Get from direct endpoint
        direct_response = client.get(
            f"/api/v1/patients/{patient_id}",
            headers={"Authorization": f"Bearer {staff_token}"}
        )
        
        # Get from search endpoint
        search_response = client.get(
            "/api/v1/patients/search",
            params={"last_name": "Consistency"},
            headers={"Authorization": f"Bearer {staff_token}"}
        )
        
        # Get from list endpoint
        list_response = client.get(
            "/api/v1/patients/",
            headers={"Authorization": f"Bearer {staff_token}"}
        )
        
        # Extract patient data from each response
        direct_patient = direct_response.json()
        search_patients = [p for p in search_response.json()["patients"] if p["patient_id"] == patient_id]
        list_patients = [p for p in list_response.json()["patients"] if p["patient_id"] == patient_id]
        
        # Verify data consistency
        assert len(search_patients) == 1
        search_patient = search_patients[0]
        
        # If patient is found in list (might not be due to pagination)
        if list_patients:
            list_patient = list_patients[0]
            assert direct_patient["first_name"] == list_patient["first_name"]
            assert direct_patient["last_name"] == list_patient["last_name"]
        
        # Compare direct and search results
        assert direct_patient["first_name"] == search_patient["first_name"]
        assert direct_patient["last_name"] == search_patient["last_name"]
        assert direct_patient["date_of_birth"] == search_patient["date_of_birth"] 