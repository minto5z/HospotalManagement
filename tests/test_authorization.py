"""
Authorization and role-based access control tests
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.user import User, UserRole
from app.core.authorization import PermissionChecker, check_permission
from app.core.security import create_access_token


@pytest.fixture
def create_test_user(db_session):
    """Create a test user in the database"""
    def _create_user(role=UserRole.STAFF, **kwargs):
        from app.core.security import get_password_hash
        
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
def auth_headers():
    """Create authentication headers for different user roles"""
    def _get_headers(user):
        token = create_access_token(
            data={
                "sub": user.username,
                "user_id": str(user.user_id),
                "role": user.role.value
            }
        )
        return {"Authorization": f"Bearer {token}"}
    
    return _get_headers


class TestPermissionChecker:
    """Test the PermissionChecker class"""
    
    def test_can_create_patient_admin(self, create_test_user):
        """Test admin can create patients"""
        admin = create_test_user(role=UserRole.ADMIN)
        assert PermissionChecker.can_create_patient(admin) is True
    
    def test_can_create_patient_doctor(self, create_test_user):
        """Test doctor can create patients"""
        doctor = create_test_user(role=UserRole.DOCTOR)
        assert PermissionChecker.can_create_patient(doctor) is True
    
    def test_can_create_patient_staff(self, create_test_user):
        """Test staff can create patients"""
        staff = create_test_user(role=UserRole.STAFF)
        assert PermissionChecker.can_create_patient(staff) is True
    
    def test_can_create_patient_patient(self, create_test_user):
        """Test patient cannot create patients"""
        patient = create_test_user(role=UserRole.PATIENT)
        assert PermissionChecker.can_create_patient(patient) is False
    
    def test_can_view_patient_all_roles(self, create_test_user):
        """Test all roles can view patient data"""
        for role in UserRole:
            user = create_test_user(role=role)
            assert PermissionChecker.can_view_patient(user) is True
    
    def test_can_update_patient_medical_staff(self, create_test_user):
        """Test medical staff can update patients"""
        for role in [UserRole.ADMIN, UserRole.DOCTOR, UserRole.STAFF]:
            user = create_test_user(role=role)
            assert PermissionChecker.can_update_patient(user) is True
    
    def test_can_update_patient_patient(self, create_test_user):
        """Test patient cannot update patient data"""
        patient = create_test_user(role=UserRole.PATIENT)
        assert PermissionChecker.can_update_patient(patient) is False
    
    def test_can_delete_patient_admin_staff(self, create_test_user):
        """Test admin and staff can delete patients"""
        for role in [UserRole.ADMIN, UserRole.STAFF]:
            user = create_test_user(role=role)
            assert PermissionChecker.can_delete_patient(user) is True
    
    def test_can_delete_patient_doctor_patient(self, create_test_user):
        """Test doctor and patient cannot delete patients"""
        for role in [UserRole.DOCTOR, UserRole.PATIENT]:
            user = create_test_user(role=role)
            assert PermissionChecker.can_delete_patient(user) is False
    
    def test_can_manage_users_admin_only(self, create_test_user):
        """Test only admin can manage users"""
        admin = create_test_user(role=UserRole.ADMIN)
        assert PermissionChecker.can_manage_users(admin) is True
        
        for role in [UserRole.DOCTOR, UserRole.STAFF, UserRole.PATIENT]:
            user = create_test_user(role=role)
            assert PermissionChecker.can_manage_users(user) is False
    
    def test_can_view_analytics_admin_doctor(self, create_test_user):
        """Test admin and doctor can view analytics"""
        for role in [UserRole.ADMIN, UserRole.DOCTOR]:
            user = create_test_user(role=role)
            assert PermissionChecker.can_view_analytics(user) is True
        
        for role in [UserRole.STAFF, UserRole.PATIENT]:
            user = create_test_user(role=role)
            assert PermissionChecker.can_view_analytics(user) is False
    
    def test_inactive_user_permissions(self, create_test_user):
        """Test inactive user has no permissions"""
        inactive_admin = create_test_user(role=UserRole.ADMIN, is_active=False)
        
        assert PermissionChecker.can_create_patient(inactive_admin) is False
        assert PermissionChecker.can_manage_users(inactive_admin) is False


class TestCheckPermission:
    """Test the check_permission function"""
    
    def test_admin_has_all_permissions(self, create_test_user):
        """Test admin has all permissions"""
        admin = create_test_user(role=UserRole.ADMIN)
        
        # Admin should have access to any role requirement
        for role in UserRole:
            assert check_permission(admin, [role]) is True
    
    def test_role_based_permission(self, create_test_user):
        """Test role-based permission checking"""
        doctor = create_test_user(role=UserRole.DOCTOR)
        
        # Doctor should have doctor permissions
        assert check_permission(doctor, [UserRole.DOCTOR]) is True
        
        # Doctor should not have admin-only permissions
        assert check_permission(doctor, [UserRole.ADMIN]) is False
        
        # Doctor should have permissions for multiple roles including doctor
        assert check_permission(doctor, [UserRole.ADMIN, UserRole.DOCTOR]) is True
    
    def test_inactive_user_no_permission(self, create_test_user):
        """Test inactive user has no permissions"""
        inactive_user = create_test_user(role=UserRole.ADMIN, is_active=False)
        
        assert check_permission(inactive_user, [UserRole.ADMIN]) is False


class TestPatientEndpointAuthorization:
    """Test authorization for patient endpoints"""
    
    def test_create_patient_authorized_roles(self, client, create_test_user, auth_headers, sample_patient_data):
        """Test authorized roles can create patients"""
        for role in [UserRole.ADMIN, UserRole.DOCTOR, UserRole.STAFF]:
            user = create_test_user(role=role)
            headers = auth_headers(user)
            
            response = client.post("/api/v1/patients/", json=sample_patient_data, headers=headers)
            
            assert response.status_code == 201, f"Role {role.value} should be able to create patients"
    
    def test_create_patient_unauthorized_role(self, client, create_test_user, auth_headers, sample_patient_data):
        """Test unauthorized role cannot create patients"""
        patient_user = create_test_user(role=UserRole.PATIENT)
        headers = auth_headers(patient_user)
        
        response = client.post("/api/v1/patients/", json=sample_patient_data, headers=headers)
        
        assert response.status_code == 403
    
    def test_create_patient_no_auth(self, client, sample_patient_data):
        """Test creating patient without authentication"""
        response = client.post("/api/v1/patients/", json=sample_patient_data)
        
        assert response.status_code == 401
    
    def test_view_patient_all_roles(self, client, create_test_user, auth_headers, create_test_patient):
        """Test all authenticated roles can view patients"""
        # Create a test patient first
        patient = create_test_patient()
        
        for role in UserRole:
            user = create_test_user(role=role)
            headers = auth_headers(user)
            
            response = client.get(f"/api/v1/patients/{patient.patient_id}", headers=headers)
            
            assert response.status_code == 200, f"Role {role.value} should be able to view patients"
    
    def test_update_patient_authorized_roles(self, client, create_test_user, auth_headers, create_test_patient):
        """Test authorized roles can update patients"""
        patient = create_test_patient()
        update_data = {"first_name": "Updated"}
        
        for role in [UserRole.ADMIN, UserRole.DOCTOR, UserRole.STAFF]:
            user = create_test_user(role=role)
            headers = auth_headers(user)
            
            response = client.put(f"/api/v1/patients/{patient.patient_id}", json=update_data, headers=headers)
            
            assert response.status_code == 200, f"Role {role.value} should be able to update patients"
    
    def test_update_patient_unauthorized_role(self, client, create_test_user, auth_headers, create_test_patient):
        """Test unauthorized role cannot update patients"""
        patient = create_test_patient()
        patient_user = create_test_user(role=UserRole.PATIENT)
        headers = auth_headers(patient_user)
        update_data = {"first_name": "Updated"}
        
        response = client.put(f"/api/v1/patients/{patient.patient_id}", json=update_data, headers=headers)
        
        assert response.status_code == 403
    
    def test_delete_patient_authorized_roles(self, client, create_test_user, auth_headers, create_test_patient):
        """Test authorized roles can delete patients"""
        for role in [UserRole.ADMIN, UserRole.STAFF]:
            patient = create_test_patient()
            user = create_test_user(role=role)
            headers = auth_headers(user)
            
            response = client.delete(f"/api/v1/patients/{patient.patient_id}", headers=headers)
            
            assert response.status_code == 200, f"Role {role.value} should be able to delete patients"
    
    def test_delete_patient_unauthorized_roles(self, client, create_test_user, auth_headers, create_test_patient):
        """Test unauthorized roles cannot delete patients"""
        for role in [UserRole.DOCTOR, UserRole.PATIENT]:
            patient = create_test_patient()
            user = create_test_user(role=role)
            headers = auth_headers(user)
            
            response = client.delete(f"/api/v1/patients/{patient.patient_id}", headers=headers)
            
            assert response.status_code == 403, f"Role {role.value} should not be able to delete patients"


class TestUserManagementAuthorization:
    """Test authorization for user management endpoints"""
    
    def test_create_user_admin_only(self, client, create_test_user, auth_headers):
        """Test only admin can create users"""
        admin = create_test_user(role=UserRole.ADMIN)
        headers = auth_headers(admin)
        
        user_data = {
            "username": "newuser",
            "email": "new@example.com",
            "password": "Password123",
            "full_name": "New User",
            "role": "staff"
        }
        
        response = client.post("/api/v1/users/", json=user_data, headers=headers)
        
        assert response.status_code == 200
    
    def test_create_user_non_admin_forbidden(self, client, create_test_user, auth_headers):
        """Test non-admin cannot create users"""
        for role in [UserRole.DOCTOR, UserRole.STAFF, UserRole.PATIENT]:
            user = create_test_user(role=role)
            headers = auth_headers(user)
            
            user_data = {
                "username": "newuser",
                "email": "new@example.com",
                "password": "Password123",
                "full_name": "New User",
                "role": "staff"
            }
            
            response = client.post("/api/v1/users/", json=user_data, headers=headers)
            
            assert response.status_code == 403, f"Role {role.value} should not be able to create users"
    
    def test_list_users_admin_only(self, client, create_test_user, auth_headers):
        """Test only admin can list users"""
        admin = create_test_user(role=UserRole.ADMIN)
        headers = auth_headers(admin)
        
        response = client.get("/api/v1/users/", headers=headers)
        
        assert response.status_code == 200
    
    def test_list_users_non_admin_forbidden(self, client, create_test_user, auth_headers):
        """Test non-admin cannot list users"""
        for role in [UserRole.DOCTOR, UserRole.STAFF, UserRole.PATIENT]:
            user = create_test_user(role=role)
            headers = auth_headers(user)
            
            response = client.get("/api/v1/users/", headers=headers)
            
            assert response.status_code == 403, f"Role {role.value} should not be able to list users"


class TestSecurityVulnerabilities:
    """Test for common security vulnerabilities"""
    
    def test_sql_injection_protection(self, client, create_test_user, auth_headers):
        """Test SQL injection protection in search endpoints"""
        user = create_test_user(role=UserRole.STAFF)
        headers = auth_headers(user)
        
        # Try SQL injection in search parameters
        malicious_params = {
            "first_name": "'; DROP TABLE patients; --",
            "last_name": "1' OR '1'='1",
            "email": "test@example.com'; DELETE FROM users; --"
        }
        
        response = client.get("/api/v1/patients/search", params=malicious_params, headers=headers)
        
        # Should not cause server error (500), should handle gracefully
        assert response.status_code in [200, 400, 422]
    
    def test_jwt_token_tampering(self, client, create_test_user):
        """Test JWT token tampering protection"""
        user = create_test_user(role=UserRole.PATIENT)
        
        # Create a valid token
        token = create_access_token(
            data={
                "sub": user.username,
                "user_id": str(user.user_id),
                "role": user.role.value
            }
        )
        
        # Tamper with the token
        tampered_token = token[:-10] + "tampered123"
        headers = {"Authorization": f"Bearer {tampered_token}"}
        
        response = client.get("/api/v1/auth/me", headers=headers)
        
        assert response.status_code == 401
    
    def test_role_escalation_protection(self, client, create_test_user):
        """Test protection against role escalation"""
        patient = create_test_user(role=UserRole.PATIENT)
        
        # Try to create a token with admin role (this would be done by tampering)
        # In a real attack, this would be attempted through token manipulation
        fake_admin_token = create_access_token(
            data={
                "sub": patient.username,  # Same user
                "user_id": str(patient.user_id),
                "role": "admin"  # But with admin role
            }
        )
        
        headers = {"Authorization": f"Bearer {fake_admin_token}"}
        
        # Try to access admin endpoint
        response = client.get("/api/v1/users/", headers=headers)
        
        # Should fail because the user in database is still a patient
        # The dependency should check the actual user role from database
        assert response.status_code == 403
    
    def test_inactive_user_token_rejection(self, client, create_test_user, auth_headers):
        """Test that inactive users' tokens are rejected"""
        user = create_test_user(role=UserRole.STAFF)
        headers = auth_headers(user)
        
        # First request should work
        response = client.get("/api/v1/auth/me", headers=headers)
        assert response.status_code == 200
        
        # Deactivate user
        user.is_active = False
        
        # Second request should fail
        response = client.get("/api/v1/auth/me", headers=headers)
        assert response.status_code == 400  # Inactive user