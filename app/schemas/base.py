"""
Base response schemas for the Hospital Management System
"""
from datetime import datetime
from typing import Optional, Any, Dict
from pydantic import BaseModel, Field
from uuid import UUID


class BaseResponse(BaseModel):
    """Base response model with common fields"""
    success: bool = True
    message: str = "Operation completed successfully"
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ErrorResponse(BaseModel):
    """Standard error response model"""
    success: bool = False
    error_code: str
    message: str
    details: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    request_id: Optional[str] = None
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class PaginatedResponse(BaseModel):
    """Paginated response wrapper"""
    items: list
    total: int
    page: int = 1
    size: int = 10
    pages: int
    
    @classmethod
    def create(cls, items: list, total: int, page: int = 1, size: int = 10):
        pages = (total + size - 1) // size  # Ceiling division
        return cls(
            items=items,
            total=total,
            page=page,
            size=size,
            pages=pages
        )


class IDResponse(BaseResponse):
    """Response containing an ID"""
    id: UUID