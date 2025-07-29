"""
Global exception handlers and custom exceptions for the Hospital Management System
"""
import logging
from datetime import datetime
from typing import Optional, Dict, Any, Union
from uuid import UUID
from enum import Enum

from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from pydantic import ValidationError

from app.schemas.base import ErrorResponse

logger = logging.getLogger(__name__)


class ErrorCode(str, Enum):
    """Standard error codes for the application"""
    # Validation errors
    VALIDATION_ERROR = "VALIDATION_ERROR"
    INVALID_INPUT = "INVALID_INPUT"
    MISSING_FIELD = "MISSING_FIELD"
    
    # Authentication/Authorization errors
    AUTHENTICATION_FAILED = "AUTHENTICATION_FAILED"
    INVALID_TOKEN = "INVALID_TOKEN"
    TOKEN_EXPIRED = "TOKEN_EXPIRED"
    INSUFFICIENT_PERMISSIONS = "INSUFFICIENT_PERMISSIONS"
    
    # Business logic errors
    RESOURCE_NOT_FOUND = "RESOURCE_NOT_FOUND"
    RESOURCE_ALREADY_EXISTS = "RESOURCE_ALREADY_EXISTS"
    BUSINESS_RULE_VIOLATION = "BUSINESS_RULE_VIOLATION"
    APPOINTMENT_CONFLICT = "APPOINTMENT_CONFLICT"
    DOCTOR_NOT_AVAILABLE = "DOCTOR_NOT_AVAILABLE"
    RESOURCE_ALREADY_ASSIGNED = "RESOURCE_ALREADY_ASSIGNED"
    
    # Database errors
    DATABASE_ERROR = "DATABASE_ERROR"
    CONSTRAINT_VIOLATION = "CONSTRAINT_VIOLATION"
    CONNECTION_ERROR = "CONNECTION_ERROR"
    
    # External service errors
    AZURE_SERVICE_ERROR = "AZURE_SERVICE_ERROR"
    ETL_PIPELINE_ERROR = "ETL_PIPELINE_ERROR"
    SYNAPSE_CONNECTION_ERROR = "SYNAPSE_CONNECTION_ERROR"
    
    # System errors
    INTERNAL_SERVER_ERROR = "INTERNAL_SERVER_ERROR"
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"


class HospitalManagementException(Exception):
    """Base exception for hospital management system"""
    
    def __init__(
        self,
        message: str,
        error_code: ErrorCode = ErrorCode.INTERNAL_SERVER_ERROR,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        self.details = details or {}


class ValidationException(HospitalManagementException):
    """Exception for validation errors"""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code=ErrorCode.VALIDATION_ERROR,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            details=details
        )


class AuthenticationException(HospitalManagementException):
    """Exception for authentication errors"""
    
    def __init__(self, message: str = "Authentication failed", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code=ErrorCode.AUTHENTICATION_FAILED,
            status_code=status.HTTP_401_UNAUTHORIZED,
            details=details
        )


class AuthorizationException(HospitalManagementException):
    """Exception for authorization errors"""
    
    def __init__(self, message: str = "Insufficient permissions", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code=ErrorCode.INSUFFICIENT_PERMISSIONS,
            status_code=status.HTTP_403_FORBIDDEN,
            details=details
        )


class ResourceNotFoundException(HospitalManagementException):
    """Exception for resource not found errors"""
    
    def __init__(self, resource_type: str, resource_id: Union[str, UUID], details: Optional[Dict[str, Any]] = None):
        message = f"{resource_type} with ID {resource_id} not found"
        super().__init__(
            message=message,
            error_code=ErrorCode.RESOURCE_NOT_FOUND,
            status_code=status.HTTP_404_NOT_FOUND,
            details=details or {"resource_type": resource_type, "resource_id": str(resource_id)}
        )


class ResourceAlreadyExistsException(HospitalManagementException):
    """Exception for resource already exists errors"""
    
    def __init__(self, resource_type: str, identifier: str, details: Optional[Dict[str, Any]] = None):
        message = f"{resource_type} with identifier {identifier} already exists"
        super().__init__(
            message=message,
            error_code=ErrorCode.RESOURCE_ALREADY_EXISTS,
            status_code=status.HTTP_409_CONFLICT,
            details=details or {"resource_type": resource_type, "identifier": identifier}
        )


class BusinessRuleViolationException(HospitalManagementException):
    """Exception for business rule violations"""
    
    def __init__(self, message: str, rule: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code=ErrorCode.BUSINESS_RULE_VIOLATION,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            details=details or {"violated_rule": rule}
        )


class AppointmentConflictException(HospitalManagementException):
    """Exception for appointment scheduling conflicts"""
    
    def __init__(self, message: str = "Appointment conflict detected", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code=ErrorCode.APPOINTMENT_CONFLICT,
            status_code=status.HTTP_409_CONFLICT,
            details=details
        )


class DatabaseException(HospitalManagementException):
    """Exception for database errors"""
    
    def __init__(self, message: str, original_error: Optional[Exception] = None, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code=ErrorCode.DATABASE_ERROR,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details=details or {"original_error": str(original_error) if original_error else None}
        )


class ExternalServiceException(HospitalManagementException):
    """Exception for external service errors"""
    
    def __init__(
        self, 
        service_name: str, 
        message: str, 
        error_code: ErrorCode = ErrorCode.AZURE_SERVICE_ERROR,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=f"{service_name}: {message}",
            error_code=error_code,
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            details=details or {"service": service_name}
        )


def get_correlation_id(request: Request) -> str:
    """Extract correlation ID from request"""
    return getattr(request.state, 'correlation_id', 'unknown')


def create_error_response(
    error_code: ErrorCode,
    message: str,
    details: Optional[Dict[str, Any]] = None,
    request_id: Optional[str] = None
) -> ErrorResponse:
    """Create standardized error response"""
    return ErrorResponse(
        error_code=error_code.value,
        message=message,
        details=details,
        request_id=request_id,
        timestamp=datetime.utcnow()
    )


async def hospital_management_exception_handler(request: Request, exc: HospitalManagementException) -> JSONResponse:
    """Handler for custom hospital management exceptions"""
    correlation_id = get_correlation_id(request)
    
    # Log the error
    logger.error(
        f"Hospital management error: {exc.message}",
        extra={
            "correlation_id": correlation_id,
            "error_code": exc.error_code.value,
            "status_code": exc.status_code,
            "details": exc.details,
            "path": request.url.path,
            "method": request.method
        }
    )
    
    error_response = create_error_response(
        error_code=exc.error_code,
        message=exc.message,
        details=exc.details,
        request_id=correlation_id
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content=error_response.dict()
    )


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Handler for FastAPI HTTP exceptions"""
    correlation_id = get_correlation_id(request)
    
    # Map HTTP status codes to error codes
    error_code_map = {
        400: ErrorCode.INVALID_INPUT,
        401: ErrorCode.AUTHENTICATION_FAILED,
        403: ErrorCode.INSUFFICIENT_PERMISSIONS,
        404: ErrorCode.RESOURCE_NOT_FOUND,
        409: ErrorCode.RESOURCE_ALREADY_EXISTS,
        422: ErrorCode.VALIDATION_ERROR,
        429: ErrorCode.RATE_LIMIT_EXCEEDED,
        500: ErrorCode.INTERNAL_SERVER_ERROR,
        503: ErrorCode.SERVICE_UNAVAILABLE
    }
    
    error_code = error_code_map.get(exc.status_code, ErrorCode.INTERNAL_SERVER_ERROR)
    
    # Log the error
    logger.warning(
        f"HTTP exception: {exc.detail}",
        extra={
            "correlation_id": correlation_id,
            "status_code": exc.status_code,
            "path": request.url.path,
            "method": request.method
        }
    )
    
    error_response = create_error_response(
        error_code=error_code,
        message=str(exc.detail),
        request_id=correlation_id
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content=error_response.dict()
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Handler for Pydantic validation errors"""
    correlation_id = get_correlation_id(request)
    
    # Format validation errors
    validation_errors = []
    for error in exc.errors():
        validation_errors.append({
            "field": ".".join(str(loc) for loc in error["loc"]),
            "message": error["msg"],
            "type": error["type"]
        })
    
    # Log the error
    logger.warning(
        f"Validation error: {len(validation_errors)} field(s) failed validation",
        extra={
            "correlation_id": correlation_id,
            "validation_errors": validation_errors,
            "path": request.url.path,
            "method": request.method
        }
    )
    
    error_response = create_error_response(
        error_code=ErrorCode.VALIDATION_ERROR,
        message="Input validation failed",
        details={"validation_errors": validation_errors},
        request_id=correlation_id
    )
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=error_response.dict()
    )


async def sqlalchemy_exception_handler(request: Request, exc: SQLAlchemyError) -> JSONResponse:
    """Handler for SQLAlchemy database errors"""
    correlation_id = get_correlation_id(request)
    
    # Determine error type and message
    if isinstance(exc, IntegrityError):
        error_code = ErrorCode.CONSTRAINT_VIOLATION
        message = "Database constraint violation"
        status_code = status.HTTP_409_CONFLICT
    else:
        error_code = ErrorCode.DATABASE_ERROR
        message = "Database operation failed"
        status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    
    # Log the error (don't expose internal database details)
    logger.error(
        f"Database error: {type(exc).__name__}",
        extra={
            "correlation_id": correlation_id,
            "error_type": type(exc).__name__,
            "path": request.url.path,
            "method": request.method,
            "original_error": str(exc)
        }
    )
    
    error_response = create_error_response(
        error_code=error_code,
        message=message,
        request_id=correlation_id
    )
    
    return JSONResponse(
        status_code=status_code,
        content=error_response.dict()
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handler for unhandled exceptions"""
    correlation_id = get_correlation_id(request)
    
    # Log the error with full details
    logger.error(
        f"Unhandled exception: {type(exc).__name__}: {str(exc)}",
        extra={
            "correlation_id": correlation_id,
            "exception_type": type(exc).__name__,
            "path": request.url.path,
            "method": request.method
        },
        exc_info=True
    )
    
    error_response = create_error_response(
        error_code=ErrorCode.INTERNAL_SERVER_ERROR,
        message="An unexpected error occurred",
        request_id=correlation_id
    )
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=error_response.dict()
    )