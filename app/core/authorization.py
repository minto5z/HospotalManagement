"""
Authorization decorators and utilities for role-based access control
"""
from functools import wraps
from typing import List, Callable, Any
from fastapi import HTTPException, status

from app.models.user import User, UserRole


def check_permission(user: User, required_roles: List[UserRole], resource_id: str = None) -> bool:
    """
    Check if user has permission to access a resource
    
    Args:
        user: Current user
        required_roles: List of roles that can access the resource
        resource_id: Optional resource ID for resource-specific permissions
        
    Returns:
        bool: True if user has permission
    """
    if not user.is_active:
        return False
    
    # Admin can access everything
    if user.role == UserRole.ADMIN:
        return True
    
    # Check if user role is in required roles
    if user.role in required_roles:
        return True
    
    # Special case: Patients can only access their own data
    if user.role == UserRole.PATIENT and resource_id:
        # This would need to be implemented based on how patient data is linked to users
        # For now, we'll allow patients to access any resource if they have the patient role
        # In a real system, you'd check if the resource belongs to the patient
        return UserRole.PATIENT in required_roles
    
    return False


def require_permissions(required_roles: List[UserRole]):
    """
    Decorator to require specific roles for endpoint access
    
    Args:
        required_roles: List of roles that can access the endpoint
        
    Returns:
        Decorator function
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract current_user from kwargs
            current_user = kwargs.get('current_user')
            if not current_user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required"
                )
            
            if not check_permission(current_user, required_roles):
                roles_str = ", ".join([role.value for role in required_roles])
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Access denied. Required roles: {roles_str}"
                )
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator


def require_resource_access(required_roles: List[UserRole], resource_param: str = "resource_id"):
    """
    Decorator to require specific roles for resource access with resource-specific checks
    
    Args:
        required_roles: List of roles that can access the resource
        resource_param: Name of the parameter containing the resource ID
        
    Returns:
        Decorator function
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract current_user and resource_id from kwargs
            current_user = kwargs.get('current_user')
            resource_id = kwargs.get(resource_param)
            
            if not current_user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required"
                )
            
            if not check_permission(current_user, required_roles, str(resource_id) if resource_id else None):
                roles_str = ", ".join([role.value for role in required_roles])
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Access denied. Required roles: {roles_str}"
                )
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator


class PermissionChecker:
    """
    Class-based permission checker for more complex authorization logic
    """
    
    @staticmethod
    def can_create_patient(user: User) -> bool:
        """Check if user can create patients"""
        if not user.is_active:
            return False
        return user.role in [UserRole.ADMIN, UserRole.DOCTOR, UserRole.STAFF]
    
    @staticmethod
    def can_view_patient(user: User, patient_id: str = None) -> bool:
        """Check if user can view patient data"""
        if not user.is_active:
            return False
            
        if user.role in [UserRole.ADMIN, UserRole.DOCTOR, UserRole.STAFF]:
            return True
        
        # Patients can view their own data (would need proper implementation)
        if user.role == UserRole.PATIENT:
            # In a real system, you'd check if the patient_id belongs to the user
            return True
        
        return False
    
    @staticmethod
    def can_update_patient(user: User, patient_id: str = None) -> bool:
        """Check if user can update patient data"""
        if not user.is_active:
            return False
        return user.role in [UserRole.ADMIN, UserRole.DOCTOR, UserRole.STAFF]
    
    @staticmethod
    def can_delete_patient(user: User) -> bool:
        """Check if user can delete/deactivate patients"""
        if not user.is_active:
            return False
        return user.role in [UserRole.ADMIN, UserRole.STAFF]
    
    @staticmethod
    def can_manage_users(user: User) -> bool:
        """Check if user can manage other users"""
        if not user.is_active:
            return False
        return user.role == UserRole.ADMIN
    
    @staticmethod
    def can_view_analytics(user: User) -> bool:
        """Check if user can view analytics and reports"""
        if not user.is_active:
            return False
        return user.role in [UserRole.ADMIN, UserRole.DOCTOR]
    
    @staticmethod
    def can_manage_appointments(user: User) -> bool:
        """Check if user can manage appointments"""
        if not user.is_active:
            return False
        return user.role in [UserRole.ADMIN, UserRole.DOCTOR, UserRole.STAFF]
    
    @staticmethod
    def can_manage_resources(user: User) -> bool:
        """Check if user can manage hospital resources"""
        if not user.is_active:
            return False
        return user.role in [UserRole.ADMIN, UserRole.STAFF]


# Audit logging for authorization events
def log_authorization_event(user: User, action: str, resource: str, granted: bool):
    """
    Log authorization events for audit purposes
    
    Args:
        user: User attempting the action
        action: Action being attempted
        resource: Resource being accessed
        granted: Whether access was granted
    """
    from app.core.security import audit_logger
    
    audit_logger._log_event(
        action=f"AUTHORIZATION_{action.upper()}",
        resource_type=resource,
        user_id=str(user.user_id),
        details={
            "granted": granted,
            "user_role": user.role.value,
            "action": action
        }
    )