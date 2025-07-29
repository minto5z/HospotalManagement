"""
Authentication service
"""
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models.user import User, UserRole
from app.schemas.auth import UserCreate, UserLogin, Token, UserResponse
from app.core.security import (
    verify_password, 
    get_password_hash, 
    create_access_token,
    audit_logger
)
from app.core.config import settings


class AuthService:
    """Service for handling authentication operations"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def authenticate_user(self, username: str, password: str) -> Optional[User]:
        """
        Authenticate a user with username and password
        
        Args:
            username: Username or email
            password: Plain text password
            
        Returns:
            User: Authenticated user or None if authentication fails
        """
        # Try to find user by username or email
        user = self.db.query(User).filter(
            (User.username == username) | (User.email == username)
        ).first()
        
        if not user:
            return None
        
        if not user.is_active:
            return None
        
        if not verify_password(password, user.hashed_password):
            return None
        
        # Update last login time
        user.last_login = datetime.utcnow()
        self.db.commit()
        
        # Log successful authentication
        audit_logger._log_event(
            action="USER_LOGIN",
            resource_type="User",
            resource_id=str(user.user_id),
            user_id=str(user.user_id)
        )
        
        return user
    
    def create_user(self, user_data: UserCreate) -> User:
        """
        Create a new user
        
        Args:
            user_data: User creation data
            
        Returns:
            User: Created user
        """
        # Check if username already exists
        existing_user = self.db.query(User).filter(
            (User.username == user_data.username) | (User.email == user_data.email)
        ).first()
        
        if existing_user:
            if existing_user.username == user_data.username:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Username already registered"
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Email already registered"
                )
        
        # Create new user
        hashed_password = get_password_hash(user_data.password)
        db_user = User(
            username=user_data.username,
            email=user_data.email,
            hashed_password=hashed_password,
            full_name=user_data.full_name,
            role=user_data.role
        )
        
        self.db.add(db_user)
        self.db.commit()
        self.db.refresh(db_user)
        
        # Log user creation
        audit_logger._log_event(
            action="USER_CREATED",
            resource_type="User",
            resource_id=str(db_user.user_id),
            details={"username": db_user.username, "role": db_user.role.value}
        )
        
        return db_user
    
    def login(self, login_data: UserLogin) -> Token:
        """
        Login user and return JWT token
        
        Args:
            login_data: Login credentials
            
        Returns:
            Token: JWT token with user information
        """
        user = self.authenticate_user(login_data.username, login_data.password)
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Create access token
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={
                "sub": user.username,
                "user_id": str(user.user_id),
                "role": user.role.value
            },
            expires_delta=access_token_expires
        )
        
        return Token(
            access_token=access_token,
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,  # Convert to seconds
            user=UserResponse.from_orm(user)
        )
    
    def get_user_by_username(self, username: str) -> Optional[User]:
        """
        Get user by username
        
        Args:
            username: Username to search for
            
        Returns:
            User: User object or None if not found
        """
        return self.db.query(User).filter(User.username == username).first()
    
    def get_user_by_id(self, user_id: str) -> Optional[User]:
        """
        Get user by ID
        
        Args:
            user_id: User ID to search for
            
        Returns:
            User: User object or None if not found
        """
        return self.db.query(User).filter(User.user_id == user_id).first()
    
    def change_password(self, user: User, current_password: str, new_password: str) -> bool:
        """
        Change user password
        
        Args:
            user: User object
            current_password: Current password
            new_password: New password
            
        Returns:
            bool: True if password changed successfully
        """
        if not verify_password(current_password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current password is incorrect"
            )
        
        user.hashed_password = get_password_hash(new_password)
        user.updated_at = datetime.utcnow()
        self.db.commit()
        
        # Log password change
        audit_logger._log_event(
            action="PASSWORD_CHANGED",
            resource_type="User",
            resource_id=str(user.user_id),
            user_id=str(user.user_id)
        )
        
        return True