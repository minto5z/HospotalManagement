"""
Patient API endpoints
"""
import logging
from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.services.patient import PatientService
from app.schemas.patient import (
    PatientCreate,
    PatientUpdate,
    PatientResponse,
    PatientCreateResponse,
    PatientListResponse,
    PatientSearchCriteria
)
from app.schemas.base import BaseResponse, ErrorResponse
from app.core.security import get_client_ip
from app.core.dependencies import (
    get_current_active_user, 
    require_medical_staff,
    require_admin_or_staff
)
from app.models.user import User

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post(
    "/",
    response_model=PatientCreateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new patient",
    description="""
    Register a new patient in the hospital management system.
    
    This endpoint allows medical staff to register a new patient with their personal and medical information.
    All operations are securely logged with the user ID and IP address for audit purposes.
    
    Authorization:
    - Requires medical staff role
    - All actions are logged for compliance and security
    
    Returns:
    - 201: Patient successfully created
    - 422: Validation error in patient data
    - 401: Unauthorized access
    - 500: Server error
    """
)
async def create_patient(
    patient_data: PatientCreate,
    request: Request,
    current_user: User = Depends(require_medical_staff),
    db: Session = Depends(get_db)
):
    """
    Create a new patient with the provided information.
    
    - **first_name**: Patient's first name (required)
    - **last_name**: Patient's last name (required)
    - **date_of_birth**: Patient's date of birth (required)
    - **gender**: Patient's gender (optional)
    - **phone_number**: Patient's phone number (optional)
    - **email**: Patient's email address (optional)
    - **address**: Patient's address (optional)
    - **emergency_contact**: Emergency contact information (optional)
    """
    try:
        # Get client IP and user info
        client_ip = get_client_ip(request)
        user_id = str(current_user.user_id)
        
        patient = PatientService.create_patient(db, patient_data, user_id, client_ip)
        patient_response = PatientResponse.model_validate(patient)
        
        return PatientCreateResponse(
            message="Patient created successfully",
            patient=patient_response
        )
        
    except ValueError as e:
        logger.warning(f"Patient creation validation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error creating patient: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error occurred while creating patient"
        )


@router.get(
    "/search",
    response_model=PatientListResponse,
    summary="Search patients",
    description="""
    Search for patients based on various criteria with pagination.
    
    This endpoint allows medical staff to search for patients using multiple filter criteria.
    Results are paginated for better performance and usability.
    All search parameters are optional and can be combined for more precise filtering.
    All search operations are validated against SQL injection and properly sanitized.
    
    Security features:
    - Input validation and sanitization
    - SQL injection prevention
    - Access control based on user role
    - Audit logging of all search operations
    
    Returns:
    - 200: List of matching patients with pagination metadata
    - 401: Unauthorized access
    - 422: Invalid search parameters
    - 500: Server error
    """
)
async def search_patients(
    request: Request,
    current_user: User = Depends(require_medical_staff),
    patient_id: UUID = Query(None, description="Patient ID to search for"),
    first_name: str = Query(None, min_length=1, max_length=50, description="First name to search for"),
    last_name: str = Query(None, min_length=1, max_length=50, description="Last name to search for"),
    email: str = Query(None, description="Email to search for"),
    phone_number: str = Query(None, max_length=20, description="Phone number to search for"),
    is_active: bool = Query(True, description="Filter by active status"),
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(10, ge=1, le=100, description="Page size"),
    db: Session = Depends(get_db)
):
    """
    Search for patients based on various criteria.
    
    - **patient_id**: Filter by specific patient ID
    - **first_name**: Filter by first name (partial match)
    - **last_name**: Filter by last name (partial match)
    - **email**: Filter by email (partial match)
    - **phone_number**: Filter by phone number (partial match)
    - **is_active**: Filter by active status (default: true)
    - **page**: Page number for pagination (default: 1)
    - **size**: Number of results per page (default: 10, max: 100)
    """
    try:
        criteria = PatientSearchCriteria(
            patient_id=patient_id,
            first_name=first_name,
            last_name=last_name,
            email=email,
            phone_number=phone_number,
            is_active=is_active,
            page=page,
            size=size
        )
        
        # Get client IP and user info
        client_ip = get_client_ip(request)
        user_id = str(current_user.user_id)
        
        patients, total = PatientService.search_patients(db, criteria, user_id, client_ip)
        
        patient_responses = [PatientResponse.model_validate(patient) for patient in patients]
        pages = (total + size - 1) // size  # Ceiling division
        
        return PatientListResponse(
            message=f"Found {total} patients matching search criteria",
            patients=patient_responses,
            total=total,
            page=page,
            size=size,
            pages=pages
        )
        
    except Exception as e:
        logger.error(f"Error searching patients: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error occurred while searching patients"
        )


@router.get(
    "/{patient_id}",
    response_model=PatientResponse,
    summary="Get patient by ID",
    description="Retrieve a specific patient by their unique ID"
)
async def get_patient(
    patient_id: UUID,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get a patient by their unique ID.
    
    - **patient_id**: The unique identifier of the patient
    """
    try:
        # Get client IP and user info
        client_ip = get_client_ip(request)
        user_id = str(current_user.user_id)
        
        patient = PatientService.get_patient_by_id(db, patient_id, user_id, client_ip)
        
        if not patient:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Patient with ID {patient_id} not found"
            )
        
        return PatientResponse.model_validate(patient)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving patient {patient_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error occurred while retrieving patient"
        )


@router.put(
    "/{patient_id}",
    response_model=PatientResponse,
    summary="Update patient information",
    description="Update an existing patient's information"
)
async def update_patient(
    patient_id: UUID,
    patient_data: PatientUpdate,
    request: Request,
    current_user: User = Depends(require_medical_staff),
    db: Session = Depends(get_db)
):
    """
    Update a patient's information.
    
    - **patient_id**: The unique identifier of the patient
    - **patient_data**: Updated patient information (only provided fields will be updated)
    """
    try:
        # Get client IP and user info
        client_ip = get_client_ip(request)
        user_id = str(current_user.user_id)
        
        patient = PatientService.update_patient(db, patient_id, patient_data, user_id, client_ip)
        
        if not patient:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Patient with ID {patient_id} not found"
            )
        
        return PatientResponse.model_validate(patient)
        
    except ValueError as e:
        logger.warning(f"Patient update validation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e)
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating patient {patient_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error occurred while updating patient"
        )


@router.delete(
    "/{patient_id}",
    response_model=BaseResponse,
    summary="Deactivate patient",
    description="Deactivate a patient (soft delete)"
)
async def deactivate_patient(
    patient_id: UUID,
    request: Request,
    current_user: User = Depends(require_admin_or_staff),
    db: Session = Depends(get_db)
):
    """
    Deactivate a patient (soft delete).
    
    - **patient_id**: The unique identifier of the patient to deactivate
    """
    try:
        # Get client IP and user info
        client_ip = get_client_ip(request)
        user_id = str(current_user.user_id)
        
        patient = PatientService.deactivate_patient(db, patient_id, user_id, client_ip)
        
        if not patient:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Patient with ID {patient_id} not found"
            )
        
        return BaseResponse(
            message=f"Patient {patient_id} deactivated successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deactivating patient {patient_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error occurred while deactivating patient"
        )


@router.get(
    "/",
    response_model=PatientListResponse,
    summary="List all patients",
    description="Get a paginated list of all active patients"
)
async def list_patients(
    request: Request,
    current_user: User = Depends(require_medical_staff),
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(10, ge=1, le=100, description="Page size"),
    db: Session = Depends(get_db)
):
    """
    Get a paginated list of all active patients.
    
    - **page**: Page number for pagination (default: 1)
    - **size**: Number of results per page (default: 10, max: 100)
    """
    try:
        criteria = PatientSearchCriteria(
            is_active=True,
            page=page,
            size=size
        )
        
        # Get client IP and user info
        client_ip = get_client_ip(request)
        user_id = str(current_user.user_id)
        
        patients, total = PatientService.search_patients(db, criteria, user_id, client_ip)
        
        patient_responses = [PatientResponse.model_validate(patient) for patient in patients]
        pages = (total + size - 1) // size  # Ceiling division
        
        return PatientListResponse(
            message=f"Retrieved {len(patient_responses)} patients",
            patients=patient_responses,
            total=total,
            page=page,
            size=size,
            pages=pages
        )
        
    except Exception as e:
        logger.error(f"Error listing patients: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error occurred while listing patients"
        )