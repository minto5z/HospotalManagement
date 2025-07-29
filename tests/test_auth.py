"""
Authentication and authorization tests
"""
import pytest
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.user import User, UserRole
from app.core.security import get_password_hash, create_access_token, verify_token
from app.services.auth import AuthService


@pytest.fixture
def auth_service(db_session):
    """Create an AuthService instance for testing"""
    return AuthService(db_session)


@pytest.fixture
def sample_user_data():
    """Sample user data for testing"""
    return {
        "username": "testuser",
        "email": "test@example.com",
        "password": "TestPassword123",
        "full_name": "Test User",
        "role": UserRole.STAFF
    }


@pytest.fixture
def create_test_user(db_session):
    """Create a test user in the database"""
    def _create_user(role=UserRole.STAFF, **kwargs):
        default_data = {
            "username": f"testuser_{role.value}",
            "email": f"test_{role.value}@example.com",
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


@pytest.fixture
def auth_headers(create_test_user):
    """Create authentication headers for different user roles"""
    def _get_headers(role=UserRole.STAFF):
        user = create_test_user(role=role)
        token = create_access_token(
            data={
                "sub": user.username,
                "user_id": str(user.user_id),
                "role": user.role.value
            }
        )
        return {"Authorization": f"Bearer {token}"}, user
    
    return _get_headers


class TestAuthentication:
    """Test authentication functionality"""
    
    def test_create_user(self, auth_service, sample_user_data):
        """Test user creation"""
        from app.schemas.auth import UserCreate
        
        user_data = UserCreate(**sample_user_data)
        user = auth_service.create_user(user_data)
        
        assert user.username == sample_user_data["username"]
        assert user.email == sample_user_data["email"]
        assert user.full_name == sample_user_data["full_name"]
        assert user.role == sample_user_data["role"]
        assert user.is_active is True
        assert user.hashed_password != sample_user_data["password"]  # Should be hashed
    
    def test_create_duplicate_user(self, auth_service, sample_user_data):
        """Test creating user with duplicate username/email"""
        from app.schemas.auth import UserCreate
        from fastapi import HTTPException
        
        user_data = UserCreate(**sample_user_data)
        auth_service.create_user(user_data)
        
        # Try to create another user with same username
        with pytest.raises(HTTPException) as exc_info:
            auth_service.create_user(user_data)
        
        assert exc_info.value.status_code == 400
        assert "already registered" in str(exc_info.value.detail)
    
    def test_authenticate_user_success(self, auth_service, create_test_user):
        """Test successful user authentication"""
        user = create_test_user()
        
        authenticated_user = auth_service.authenticate_user(user.username, "TestPassword123")
        
        assert authenticated_user is not None
        assert authenticated_user.user_id == user.user_id
        assert authenticated_user.last_login is not None
    
    def test_authenticate_user_wrong_password(self, auth_service, create_test_user):
        """Test authentication with wrong password"""
        user = create_test_user()
        
        authenticated_user = auth_service.authenticate_user(user.username, "WrongPassword")
        
        assert authenticated_user is None
    
    def test_authenticate_user_nonexistent(self, auth_service):
        """Test authentication with nonexistent user"""
        authenticated_user = auth_service.authenticate_user("nonexistent", "password")
        
        assert authenticated_user is None
    
    def test_authenticate_inactive_user(self, auth_service, create_test_user):
        """Test authentication with inactive user"""
        user = create_test_user(is_active=False)
        
        authenticated_user = auth_service.authenticate_user(user.username, "TestPassword123")
        
        assert authenticated_user is None
    
    def test_login_success(self, auth_service, create_test_user):
        """Test successful login"""
        from app.schemas.auth import UserLogin
        
        user = create_test_user()
        login_data = UserLogin(username=user.username, password="TestPassword123")
        
        token = auth_service.login(login_data)
        
        assert token.access_token is not None
        assert token.token_type == "bearer"
        assert token.expires_in > 0
        assert token.user.username == user.username
    
    def test_login_failure(self, auth_service, create_test_user):
        """Test failed login"""
        from app.schemas.auth import UserLogin
        from fastapi import HTTPException
        
        user = create_test_user()
        login_data = UserLogin(username=user.username, password="WrongPassword")
        
        with pytest.raises(HTTPException) as exc_info:
            auth_service.login(login_data)
        
        assert exc_info.value.status_code == 401
    
    def test_change_password_success(self, auth_service, create_test_user):
        """Test successful password change"""
        user = create_test_user()
        old_password_hash = user.hashed_password
        
        success = auth_service.change_password(user, "TestPassword123", "NewPassword123")
        
        assert success is True
        assert user.hashed_password != old_password_hash
    
    def test_change_password_wrong_current(self, auth_service, create_test_user):
        """Test password change with wrong current password"""
        from fastapi import HTTPException
        
        user = create_test_user()
        
        with pytest.raises(HTTPException) as exc_info:
            auth_service.change_password(user, "WrongPassword", "NewPassword123")
        
        assert exc_info.value.status_code == 400


class TestJWTTokens:
    """Test JWT token functionality"""
    
    def test_create_access_token(self):
        """Test JWT token creation"""
        data = {"sub": "testuser", "user_id": "123", "role": "staff"}
        token = create_access_token(data)
        
        assert token is not None
        assert isinstance(token, str)
    
    def test_verify_token_valid(self):
        """Test JWT token verification with valid token"""
        data = {"sub": "testuser", "user_id": "123", "role": "staff"}
        token = create_access_token(data)
        
        payload = verify_token(token)
        
        assert payload is not None
        assert payload["sub"] == "testuser"
        assert payload["user_id"] == "123"
        assert payload["role"] == "staff"
    
    def test_verify_token_invalid(self):
        """Test JWT token verification with invalid token"""
        payload = verify_token("invalid.token.here")
        
        assert payload is None
    
    def test_verify_token_expired(self):
        """Test JWT token verification with expired token"""
        data = {"sub": "testuser", "user_id": "123", "role": "staff"}
        # Create token that expires immediately
        token = create_access_token(data, expires_delta=timedelta(seconds=-1))
        
        payload = verify_token(token)
        
        assert payload is None


class TestAuthenticationEndpoints:
    """Test authentication API endpoints"""
    
    def test_register_endpoint(self, client, sample_user_data):
        """Test user registration endpoint"""
        response = client.post("/api/v1/auth/register", json=sample_user_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["username"] == sample_user_data["username"]
        assert data["email"] == sample_user_data["email"]
        assert "user_id" in data
    
    def test_register_invalid_data(self, client):
        """Test registration with invalid data"""
        invalid_data = {
            "username": "test",
            "email": "invalid-email",
            "password": "weak",  # Too weak
            "full_name": "Test User"
        }
        
        response = client.post("/api/v1/auth/register", json=invalid_data)
        
        assert response.status_code == 422  # Validation error
    
    def test_login_endpoint(self, client, create_test_user):
        """Test login endpoint"""
        user = create_test_user()
        login_data = {
            "username": user.username,
            "password": "TestPassword123"
        }
        
        response = client.post("/api/v1/auth/login", json=login_data)
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert "user" in data
    
    def test_login_invalid_credentials(self, client, create_test_user):
        """Test login with invalid credentials"""
        user = create_test_user()
        login_data = {
            "username": user.username,
            "password": "WrongPassword"
        }
        
        response = client.post("/api/v1/auth/login", json=login_data)
        
        assert response.status_code == 401
    
    def test_get_current_user_endpoint(self, client, auth_headers):
        """Test get current user endpoint"""
        headers, user = auth_headers()
        
        response = client.get("/api/v1/auth/me", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["username"] == user.username
        assert data["email"] == user.email
    
    def test_get_current_user_no_token(self, client):
        """Test get current user without token"""
        response = client.get("/api/v1/auth/me")
        
        assert response.status_code == 401
    
    def test_get_current_user_invalid_token(self, client):
        """Test get current user with invalid token"""
        headers = {"Authorization": "Bearer invalid.token.here"}
        
        response = client.get("/api/v1/auth/me", headers=headers)
        
        assert response.status_code == 401
    
    def test_change_password_endpoint(self, client, auth_headers):
        """Test change password endpoint"""
        headers, user = auth_headers()
        password_data = {
            "current_password": "TestPassword123",
            "new_password": "NewPassword123"
        }
        
        response = client.post("/api/v1/auth/change-password", json=password_data, headers=headers)
        
        assert response.status_code == 200
        assert response.json()["message"] == "Password changed successfully"
    
    def test_logout_endpoint(self, client, auth_headers):
        """Test logout endpoint"""
        headers, user = auth_headers()
        
        response = client.post("/api/v1/auth/logout", headers=headers)
        
        assert response.status_code == 200
        assert "logged out" in response.json()["message"]