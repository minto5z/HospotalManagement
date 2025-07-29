"""
Patient service layer for business logic
"""
import logging
from typing import Optional, List, Tuple
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_

from app.models.patient import Patient
from app.schemas.patient import PatientCreate, PatientUpdate, PatientSearchCriteria
from app.core.security import audit_logger, sanitize_input, validate_sql_injection

logger = logging.getLogger(__name__)


class PatientService:
    """Service class for patient-related operations"""

    @staticmethod
    def create_patient(db: Session, patient_data: PatientCreate, user_id: Optional[str] = None, 
                      ip_address: Optional[str] = None) -> Patient:
        """
        Create a new patient
        
        Args:
            db: Database session
            patient_data: Patient creation data
            user_id: ID of user creating the patient
            ip_address: IP address of the request
            
        Returns:
            Patient: Created patient object
            
        Raises:
            ValueError: If patient data is invalid
        """
        try:
            # Sanitize input data
            sanitized_data = patient_data.model_dump()
            for key, value in sanitized_data.items():
                if isinstance(value, str):
                    sanitized_data[key] = sanitize_input(value)
            
            # Validate for SQL injection
            if not validate_sql_injection(sanitized_data):
                raise ValueError("Invalid input data detected")

            # Check if patient with same email already exists (if email provided)
            if sanitized_data.get('email'):
                # For email checking, we need to encrypt the email to compare
                from app.core.security import data_encryption
                encrypted_email = data_encryption.encrypt(sanitized_data['email'])
                existing_patient = db.query(Patient).filter(
                    Patient.email == encrypted_email,
                    Patient.is_active == True
                ).first()
                if existing_patient:
                    raise ValueError(f"Patient with email already exists")

            # Create new patient
            db_patient = Patient(**sanitized_data)
            
            # Encrypt sensitive data before saving
            db_patient.encrypt_sensitive_data()
            
            db.add(db_patient)
            db.commit()
            db.refresh(db_patient)
            
            # Decrypt data for return
            db_patient.decrypt_sensitive_data()
            
            # Log audit event
            audit_logger.log_patient_created(
                patient_id=str(db_patient.patient_id),
                user_id=user_id,
                ip_address=ip_address
            )
            
            logger.info(f"Created patient with ID: {db_patient.patient_id}")
            return db_patient
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error creating patient: {e}")
            raise

    @staticmethod
    def get_patient_by_id(db: Session, patient_id: UUID, user_id: Optional[str] = None,
                         ip_address: Optional[str] = None) -> Optional[Patient]:
        """
        Get patient by ID
        
        Args:
            db: Database session
            patient_id: Patient UUID
            user_id: ID of user accessing the patient
            ip_address: IP address of the request
            
        Returns:
            Patient: Patient object if found, None otherwise
        """
        try:
            patient = db.query(Patient).filter(
                Patient.patient_id == patient_id,
                Patient.is_active == True
            ).first()
            
            if patient:
                # Decrypt sensitive data
                patient.decrypt_sensitive_data()
                
                # Log audit event
                audit_logger.log_patient_accessed(
                    patient_id=str(patient_id),
                    user_id=user_id,
                    ip_address=ip_address
                )
                
                logger.info(f"Retrieved patient with ID: {patient_id}")
            else:
                logger.warning(f"Patient not found with ID: {patient_id}")
                
            return patient
            
        except Exception as e:
            logger.error(f"Error retrieving patient {patient_id}: {e}")
            raise

    @staticmethod
    def update_patient(db: Session, patient_id: UUID, patient_data: PatientUpdate,
                      user_id: Optional[str] = None, ip_address: Optional[str] = None) -> Optional[Patient]:
        """
        Update patient information
        
        Args:
            db: Database session
            patient_id: Patient UUID
            patient_data: Patient update data
            user_id: ID of user updating the patient
            ip_address: IP address of the request
            
        Returns:
            Patient: Updated patient object if found, None otherwise
            
        Raises:
            ValueError: If update data is invalid
        """
        try:
            # Get existing patient
            db_patient = db.query(Patient).filter(
                Patient.patient_id == patient_id,
                Patient.is_active == True
            ).first()
            
            if not db_patient:
                logger.warning(f"Patient not found for update: {patient_id}")
                return None

            # Sanitize input data
            update_data = patient_data.model_dump(exclude_unset=True)
            sanitized_data = {}
            for key, value in update_data.items():
                if isinstance(value, str):
                    sanitized_data[key] = sanitize_input(value)
                else:
                    sanitized_data[key] = value
            
            # Validate for SQL injection
            if not validate_sql_injection(sanitized_data):
                raise ValueError("Invalid input data detected")

            # Check email uniqueness if email is being updated
            if 'email' in sanitized_data and sanitized_data['email']:
                from app.core.security import data_encryption
                encrypted_email = data_encryption.encrypt(sanitized_data['email'])
                existing_patient = db.query(Patient).filter(
                    Patient.email == encrypted_email,
                    Patient.patient_id != patient_id,
                    Patient.is_active == True
                ).first()
                if existing_patient:
                    raise ValueError(f"Patient with email already exists")

            # Store original values for audit
            original_values = {}
            for field in sanitized_data.keys():
                if hasattr(db_patient, field):
                    original_values[field] = getattr(db_patient, field)

            # Update patient fields
            for field, value in sanitized_data.items():
                setattr(db_patient, field, value)

            # Encrypt sensitive data before saving
            db_patient.encrypt_sensitive_data()

            db.commit()
            db.refresh(db_patient)
            
            # Decrypt data for return
            db_patient.decrypt_sensitive_data()
            
            # Log audit event
            audit_logger.log_patient_updated(
                patient_id=str(patient_id),
                changes=sanitized_data,
                user_id=user_id,
                ip_address=ip_address
            )
            
            logger.info(f"Updated patient with ID: {patient_id}")
            return db_patient
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error updating patient {patient_id}: {e}")
            raise

    @staticmethod
    def search_patients(db: Session, criteria: PatientSearchCriteria, 
                       user_id: Optional[str] = None, ip_address: Optional[str] = None) -> Tuple[List[Patient], int]:
        """
        Search patients based on criteria
        
        Args:
            db: Database session
            criteria: Search criteria
            user_id: ID of user performing the search
            ip_address: IP address of the request
            
        Returns:
            Tuple[List[Patient], int]: List of patients and total count
        """
        try:
            # Validate search criteria for SQL injection
            criteria_dict = criteria.model_dump(exclude_unset=True)
            if not validate_sql_injection(criteria_dict):
                raise ValueError("Invalid search criteria detected")

            query = db.query(Patient)
            
            # Build filters
            filters = []
            
            if criteria.patient_id:
                filters.append(Patient.patient_id == criteria.patient_id)
            
            if criteria.first_name:
                sanitized_name = sanitize_input(criteria.first_name)
                filters.append(Patient.first_name.ilike(f"%{sanitized_name}%"))
            
            if criteria.last_name:
                sanitized_name = sanitize_input(criteria.last_name)
                filters.append(Patient.last_name.ilike(f"%{sanitized_name}%"))
            
            # For encrypted fields, we need to handle search differently
            # Note: Searching encrypted data is complex and may require special handling
            # For now, we'll skip encrypted field searches in this implementation
            # In production, consider using searchable encryption or separate search indexes
            
            if criteria.is_active is not None:
                filters.append(Patient.is_active == criteria.is_active)
            
            # Apply filters
            if filters:
                query = query.filter(and_(*filters))
            
            # Get total count
            total = query.count()
            
            # Apply pagination
            offset = (criteria.page - 1) * criteria.size
            patients = query.offset(offset).limit(criteria.size).all()
            
            # Decrypt sensitive data for all patients
            for patient in patients:
                patient.decrypt_sensitive_data()
            
            # Log audit event
            audit_logger.log_patient_search(
                criteria=criteria_dict,
                result_count=total,
                user_id=user_id,
                ip_address=ip_address
            )
            
            logger.info(f"Found {total} patients matching search criteria")
            return patients, total
            
        except Exception as e:
            logger.error(f"Error searching patients: {e}")
            raise

    @staticmethod
    def deactivate_patient(db: Session, patient_id: UUID, user_id: Optional[str] = None,
                          ip_address: Optional[str] = None) -> Optional[Patient]:
        """
        Deactivate a patient (soft delete)
        
        Args:
            db: Database session
            patient_id: Patient UUID
            user_id: ID of user deactivating the patient
            ip_address: IP address of the request
            
        Returns:
            Patient: Deactivated patient object if found, None otherwise
        """
        try:
            db_patient = db.query(Patient).filter(
                Patient.patient_id == patient_id,
                Patient.is_active == True
            ).first()
            
            if not db_patient:
                logger.warning(f"Patient not found for deactivation: {patient_id}")
                return None

            db_patient.is_active = False
            db.commit()
            db.refresh(db_patient)
            
            # Decrypt data for return
            db_patient.decrypt_sensitive_data()
            
            # Log audit event
            audit_logger.log_patient_deactivated(
                patient_id=str(patient_id),
                user_id=user_id,
                ip_address=ip_address
            )
            
            logger.info(f"Deactivated patient with ID: {patient_id}")
            return db_patient
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error deactivating patient {patient_id}: {e}")
            raise

    @staticmethod
    def get_patient_by_email(db: Session, email: str) -> Optional[Patient]:
        """
        Get patient by email address
        
        Args:
            db: Database session
            email: Patient email
            
        Returns:
            Patient: Patient object if found, None otherwise
        """
        try:
            patient = db.query(Patient).filter(
                Patient.email == email,
                Patient.is_active == True
            ).first()
            
            if patient:
                logger.info(f"Retrieved patient by email: {email}")
            else:
                logger.warning(f"Patient not found with email: {email}")
                
            return patient
            
        except Exception as e:
            logger.error(f"Error retrieving patient by email {email}: {e}")
            raise