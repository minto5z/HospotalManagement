#!/usr/bin/env python3
"""
Simple security tests that don't require database connection
"""
import sys
import os

# Add the app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '.'))

from app.core.security import (
    get_password_hash, 
    verify_password, 
    create_access_token, 
    verify_token
)
from app.models.user import UserRole
from app.core.authorization import PermissionChecker, check_permission


class MockUser:
    """Mock user for testing without database"""
    def __init__(self, role, is_active=True):
        self.role = role
        self.is_active = is_active
        self.user_id = "test-user-id"
        self.username = f"test_{role.value}"


def test_password_security():
    """Test password hashing and verification"""
    print("Testing password security...")
    
    password = "TestPassword123"
    hashed = get_password_hash(password)
    
    # Verify correct password
    assert verify_password(password, hashed), "Password verification failed"
    
    # Verify incorrect password
    assert not verify_password("WrongPassword", hashed), "Wrong password should not verify"
    
    print("✓ Password security tests passed")


def test_jwt_tokens():
    """Test JWT token creation and verification"""
    print("Testing JWT tokens...")
    
    data = {
        "sub": "testuser",
        "user_id": "123",
        "role": "admin"
    }
    
    # Create token
    token = create_access_token(data)
    assert token is not None, "Token creation failed"
    
    # Verify token
    payload = verify_token(token)
    assert payload is not None, "Token verification failed"
    assert payload["sub"] == "testuser", "Token payload incorrect"
    assert payload["user_id"] == "123", "Token user_id incorrect"
    assert payload["role"] == "admin", "Token role incorrect"
    
    # Test invalid token
    invalid_payload = verify_token("invalid.token.here")
    assert invalid_payload is None, "Invalid token should return None"
    
    print("✓ JWT token tests passed")


def test_permission_checker():
    """Test the PermissionChecker class"""
    print("Testing permission checker...")
    
    # Test admin permissions
    admin = MockUser(UserRole.ADMIN)
    assert PermissionChecker.can_create_patient(admin), "Admin should create patients"
    assert PermissionChecker.can_manage_users(admin), "Admin should manage users"
    assert PermissionChecker.can_view_analytics(admin), "Admin should view analytics"
    
    # Test doctor permissions
    doctor = MockUser(UserRole.DOCTOR)
    assert PermissionChecker.can_create_patient(doctor), "Doctor should create patients"
    assert not PermissionChecker.can_manage_users(doctor), "Doctor should not manage users"
    assert PermissionChecker.can_view_analytics(doctor), "Doctor should view analytics"
    
    # Test staff permissions
    staff = MockUser(UserRole.STAFF)
    assert PermissionChecker.can_create_patient(staff), "Staff should create patients"
    assert not PermissionChecker.can_manage_users(staff), "Staff should not manage users"
    assert not PermissionChecker.can_view_analytics(staff), "Staff should not view analytics"
    
    # Test patient permissions
    patient = MockUser(UserRole.PATIENT)
    assert not PermissionChecker.can_create_patient(patient), "Patient should not create patients"
    assert not PermissionChecker.can_manage_users(patient), "Patient should not manage users"
    assert not PermissionChecker.can_view_analytics(patient), "Patient should not view analytics"
    
    # Test inactive user
    inactive_admin = MockUser(UserRole.ADMIN, is_active=False)
    assert not PermissionChecker.can_create_patient(inactive_admin), "Inactive user should have no permissions"
    
    print("✓ Permission checker tests passed")


def test_check_permission():
    """Test the check_permission function"""
    print("Testing check_permission function...")
    
    # Test admin has all permissions
    admin = MockUser(UserRole.ADMIN)
    for role in UserRole:
        assert check_permission(admin, [role]), f"Admin should have {role.value} permissions"
    
    # Test role-specific permissions
    doctor = MockUser(UserRole.DOCTOR)
    assert check_permission(doctor, [UserRole.DOCTOR]), "Doctor should have doctor permissions"
    assert not check_permission(doctor, [UserRole.ADMIN]), "Doctor should not have admin permissions"
    assert check_permission(doctor, [UserRole.ADMIN, UserRole.DOCTOR]), "Doctor should have permissions when included in list"
    
    # Test inactive user
    inactive_user = MockUser(UserRole.ADMIN, is_active=False)
    assert not check_permission(inactive_user, [UserRole.ADMIN]), "Inactive user should have no permissions"
    
    print("✓ check_permission tests passed")


def test_role_hierarchy():
    """Test role hierarchy and access levels"""
    print("Testing role hierarchy...")
    
    # Define expected access levels for different operations
    create_patient_roles = [UserRole.ADMIN, UserRole.DOCTOR, UserRole.STAFF]
    manage_users_roles = [UserRole.ADMIN]
    view_analytics_roles = [UserRole.ADMIN, UserRole.DOCTOR]
    
    for role in UserRole:
        user = MockUser(role)
        
        # Test create patient permissions
        expected_create = role in create_patient_roles
        actual_create = PermissionChecker.can_create_patient(user)
        assert actual_create == expected_create, f"Role {role.value} create patient permission mismatch"
        
        # Test manage users permissions
        expected_manage = role in manage_users_roles
        actual_manage = PermissionChecker.can_manage_users(user)
        assert actual_manage == expected_manage, f"Role {role.value} manage users permission mismatch"
        
        # Test view analytics permissions
        expected_analytics = role in view_analytics_roles
        actual_analytics = PermissionChecker.can_view_analytics(user)
        assert actual_analytics == expected_analytics, f"Role {role.value} view analytics permission mismatch"
    
    print("✓ Role hierarchy tests passed")


def main():
    """Run all security tests"""
    print("Running security tests...\n")
    
    try:
        test_password_security()
        test_jwt_tokens()
        test_permission_checker()
        test_check_permission()
        test_role_hierarchy()
        
        print("\n🎉 All security tests passed!")
        return 0
        
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        return 1
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())