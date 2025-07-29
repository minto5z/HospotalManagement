"""
Pydantic schemas for the hospital management system.
"""
from .base import BaseResponse, ErrorResponse
from .patient import PatientCreate, PatientUpdate, PatientResponse, PatientSearch
from .auth import (
    UserCreate, UserUpdate, UserResponse, UserLogin, 
    Token, TokenData, PasswordChange
)

__all__ = [
    "BaseResponse",
    "ErrorResponse",
    "PatientCreate",
    "PatientUpdate", 
    "PatientResponse",
    "PatientSearch",
    "UserCreate",
    "UserUpdate",
    "UserResponse",
    "UserLogin",
    "Token",
    "TokenData",
    "PasswordChange",
]