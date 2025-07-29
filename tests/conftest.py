"""
Test configuration and fixtures
"""
import pytest
from datetime import date
from uuid import uuid4
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from app.models.base import Base
from app.models.patient import Patient
from app.models.user import User, UserRole
from app.main import app
from app.db.database import get_db
from app.core.security import get_password_hash


# Create in-memory SQLite database for testing
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, 
    connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db_session():
    """Create a fresh database session for each test"""
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db_session):
    """Create a test client with database dependency override"""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def sample_patient_data():
    """Sample patient data for testing"""
    return {
        "first_name": "John",
        "last_name": "Doe",
        "date_of_birth": "1990-01-01",
        "gender": "Male",
        "phone_number": "+1234567890",
        "email": "john.doe@example.com",
        "address": "123 Main St, City, State 12345",
        "emergency_contact": "Jane Doe - +1234567891"
    }


@pytest.fixture
def sample_patient_update_data():
    """Sample patient update data for testing"""
    return {
        "first_name": "Jane",
        "phone_number": "+1987654321",
        "email": "jane.doe@example.com"
    }


@pytest.fixture
def create_test_patient(db_session):
    """Create a test patient in the database"""
    def _create_patient(**kwargs):
        default_data = {
            "first_name": "Test",
            "last_name": "Patient",
            "date_of_birth": date(1985, 5, 15),
            "gender": "Female",
            "phone_number": "+1555123456",
            "email": "test.patient@example.com",
            "address": "456 Test Ave, Test City, TC 54321",
            "emergency_contact": "Emergency Contact - +1555654321"
        }
        default_data.update(kwargs)
        
        patient = Patient(**default_data)
        # Don't encrypt for testing to make assertions easier
        db_session.add(patient)
        db_session.commit()
        db_session.refresh(patient)
        return patient
    
    return _create_patient


@pytest.fixture
def invalid_patient_data():
    """Invalid patient data for testing validation"""
    return [
        # Missing required fields
        {
            "last_name": "Doe",
            "date_of_birth": "1990-01-01"
        },
        # Invalid email
        {
            "first_name": "John",
            "last_name": "Doe", 
            "date_of_birth": "1990-01-01",
            "email": "invalid-email"
        },
        # Future date of birth
        {
            "first_name": "John",
            "last_name": "Doe",
            "date_of_birth": "2030-01-01"
        },
        # Invalid gender
        {
            "first_name": "John",
            "last_name": "Doe",
            "date_of_birth": "1990-01-01",
            "gender": "Invalid"
        }
    ]


@pytest.fixture
def create_test_user(db_session):
    """Create a test user in the database"""
    def _create_user(role=UserRole.STAFF, **kwargs):
        default_data = {
            "username": f"testuser_{role.value}_{uuid4().hex[:8]}",
            "email": f"test_{role.value}_{uuid4().hex[:8]}@example.com",
            "hashed_password": get_password_hash("TestPassword123"),
            "full_name": f"Test {role.value.title()}",
            "role": role,
            "is_active": True
        }
        default_data.update(kwargs)
        
        user = User(**default_data)
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        return user
    
    return _create_user