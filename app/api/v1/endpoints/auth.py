"""
Authentication endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.schemas.auth import UserLogin, Token, UserCreate, UserResponse, PasswordChange
from app.services.auth import AuthService
from app.core.dependencies import get_current_active_user
from app.models.user import User

router = APIRouter()


@router.post("/login", response_model=Token)
def login(
    login_data: UserLogin,
    db: Session = Depends(get_db)
):
    """
    Login endpoint to authenticate users and return JWT token
    
    Args:
        login_data: User login credentials
        db: Database session
        
    Returns:
        Token: JWT token with user information
    """
    auth_service = AuthService(db)
    return auth_service.login(login_data)


@router.post("/register", response_model=UserResponse)
def register(
    user_data: UserCreate,
    db: Session = Depends(get_db)
):
    """
    Register a new user
    
    Args:
        user_data: User registration data
        db: Database session
        
    Returns:
        UserResponse: Created user information
    """
    auth_service = AuthService(db)
    user = auth_service.create_user(user_data)
    return UserResponse.from_orm(user)


@router.get("/me", response_model=UserResponse)
def get_current_user_info(
    current_user: User = Depends(get_current_active_user)
):
    """
    Get current user information
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        UserResponse: Current user information
    """
    return UserResponse.from_orm(current_user)


@router.post("/change-password")
def change_password(
    password_data: PasswordChange,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Change user password
    
    Args:
        password_data: Password change data
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        dict: Success message
    """
    auth_service = AuthService(db)
    auth_service.change_password(
        current_user,
        password_data.current_password,
        password_data.new_password
    )
    return {"message": "Password changed successfully"}


@router.post("/logout")
def logout(current_user: User = Depends(get_current_active_user)):
    """
    Logout endpoint (client-side token invalidation)
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        dict: Success message
    """
    # In a JWT-based system, logout is typically handled client-side
    # by removing the token. For server-side logout, you would need
    # to implement a token blacklist.
    return {"message": "Successfully logged out"}