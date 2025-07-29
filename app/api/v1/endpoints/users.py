"""
User management endpoints (Admin only)
"""
from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.schemas.auth import UserCreate, UserUpdate, UserResponse
from app.services.auth import AuthService
from app.core.dependencies import require_admin
from app.models.user import User, UserRole

router = APIRouter()


@router.post("/", response_model=UserResponse)
def create_user(
    user_data: UserCreate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Create a new user (Admin only)
    
    Args:
        user_data: User creation data
        current_user: Current authenticated admin user
        db: Database session
        
    Returns:
        UserResponse: Created user information
    """
    auth_service = AuthService(db)
    user = auth_service.create_user(user_data)
    return UserResponse.from_orm(user)


@router.get("/", response_model=List[UserResponse])
def list_users(
    current_user: User = Depends(require_admin),
    role: UserRole = Query(None, description="Filter by user role"),
    is_active: bool = Query(None, description="Filter by active status"),
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(10, ge=1, le=100, description="Page size"),
    db: Session = Depends(get_db)
):
    """
    List all users with optional filtering (Admin only)
    
    Args:
        current_user: Current authenticated admin user
        role: Optional role filter
        is_active: Optional active status filter
        page: Page number for pagination
        size: Page size for pagination
        db: Database session
        
    Returns:
        List[UserResponse]: List of users
    """
    query = db.query(User)
    
    if role:
        query = query.filter(User.role == role)
    
    if is_active is not None:
        query = query.filter(User.is_active == is_active)
    
    # Apply pagination
    offset = (page - 1) * size
    users = query.offset(offset).limit(size).all()
    
    return [UserResponse.from_orm(user) for user in users]


@router.get("/{user_id}", response_model=UserResponse)
def get_user(
    user_id: UUID,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Get a specific user by ID (Admin only)
    
    Args:
        user_id: User ID to retrieve
        current_user: Current authenticated admin user
        db: Database session
        
    Returns:
        UserResponse: User information
    """
    auth_service = AuthService(db)
    user = auth_service.get_user_by_id(str(user_id))
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID {user_id} not found"
        )
    
    return UserResponse.from_orm(user)


@router.put("/{user_id}", response_model=UserResponse)
def update_user(
    user_id: UUID,
    user_data: UserUpdate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Update a user's information (Admin only)
    
    Args:
        user_id: User ID to update
        user_data: Updated user information
        current_user: Current authenticated admin user
        db: Database session
        
    Returns:
        UserResponse: Updated user information
    """
    user = db.query(User).filter(User.user_id == user_id).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID {user_id} not found"
        )
    
    # Update user fields
    update_data = user_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(user, field, value)
    
    db.commit()
    db.refresh(user)
    
    return UserResponse.from_orm(user)


@router.delete("/{user_id}")
def deactivate_user(
    user_id: UUID,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Deactivate a user (Admin only)
    
    Args:
        user_id: User ID to deactivate
        current_user: Current authenticated admin user
        db: Database session
        
    Returns:
        dict: Success message
    """
    if str(user_id) == str(current_user.user_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot deactivate your own account"
        )
    
    user = db.query(User).filter(User.user_id == user_id).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID {user_id} not found"
        )
    
    user.is_active = False
    db.commit()
    
    return {"message": f"User {user_id} deactivated successfully"}


@router.post("/{user_id}/activate")
def activate_user(
    user_id: UUID,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Activate a user (Admin only)
    
    Args:
        user_id: User ID to activate
        current_user: Current authenticated admin user
        db: Database session
        
    Returns:
        dict: Success message
    """
    user = db.query(User).filter(User.user_id == user_id).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID {user_id} not found"
        )
    
    user.is_active = True
    db.commit()
    
    return {"message": f"User {user_id} activated successfully"}