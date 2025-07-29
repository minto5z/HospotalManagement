"""
Security utilities for data encryption, audit logging, and JWT authentication
"""
import logging
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Union
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64
import os

from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import HTTPException, status

from app.core.config import settings

logger = logging.getLogger(__name__)


class DataEncryption:
    """Handle encryption and decryption of sensitive data"""
    
    def __init__(self):
        self._key = self._get_or_create_key()
        self._cipher = Fernet(self._key)
    
    def _get_or_create_key(self) -> bytes:
        """Get or create encryption key from environment or generate new one"""
        # In production, this should be stored securely (Azure Key Vault, etc.)
        key_string = os.getenv("ENCRYPTION_KEY")
        
        if key_string:
            try:
                return base64.urlsafe_b64decode(key_string.encode())
            except Exception as e:
                logger.warning(f"Invalid encryption key in environment: {e}")
        
        # Generate key from secret key for consistency
        password = settings.SECRET_KEY.encode()
        salt = b'hospital_management_salt'  # In production, use random salt per installation
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password))
        return key
    
    def encrypt(self, data: str) -> str:
        """
        Encrypt sensitive data
        
        Args:
            data: Plain text data to encrypt
            
        Returns:
            str: Encrypted data as base64 string
        """
        if not data:
            return data
        
        try:
            encrypted_data = self._cipher.encrypt(data.encode())
            return base64.urlsafe_b64encode(encrypted_data).decode()
        except Exception as e:
            logger.error(f"Error encrypting data: {e}")
            raise
    
    def decrypt(self, encrypted_data: str) -> str:
        """
        Decrypt sensitive data
        
        Args:
            encrypted_data: Encrypted data as base64 string
            
        Returns:
            str: Decrypted plain text data
        """
        if not encrypted_data:
            return encrypted_data
        
        try:
            encrypted_bytes = base64.urlsafe_b64decode(encrypted_data.encode())
            decrypted_data = self._cipher.decrypt(encrypted_bytes)
            return decrypted_data.decode()
        except Exception as e:
            logger.error(f"Error decrypting data: {e}")
            raise
    
    def hash_data(self, data: str) -> str:
        """
        Create a hash of data for comparison purposes
        
        Args:
            data: Data to hash
            
        Returns:
            str: SHA256 hash of the data
        """
        if not data:
            return data
        
        return hashlib.sha256(data.encode()).hexdigest()


class AuditLogger:
    """Handle audit logging for data changes"""
    
    def __init__(self):
        self.logger = logging.getLogger("audit")
        # Configure audit logger to write to separate file
        if not self.logger.handlers:
            handler = logging.FileHandler("audit.log")
            formatter = logging.Formatter(
                '%(asctime)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)
    
    def log_patient_created(self, patient_id: str, user_id: Optional[str] = None, 
                           ip_address: Optional[str] = None):
        """Log patient creation event"""
        self._log_event(
            action="PATIENT_CREATED",
            resource_type="Patient",
            resource_id=patient_id,
            user_id=user_id,
            ip_address=ip_address
        )
    
    def log_patient_updated(self, patient_id: str, changes: Dict[str, Any], 
                           user_id: Optional[str] = None, ip_address: Optional[str] = None):
        """Log patient update event"""
        # Don't log sensitive data values, just field names
        changed_fields = list(changes.keys())
        self._log_event(
            action="PATIENT_UPDATED",
            resource_type="Patient",
            resource_id=patient_id,
            details={"changed_fields": changed_fields},
            user_id=user_id,
            ip_address=ip_address
        )
    
    def log_patient_accessed(self, patient_id: str, user_id: Optional[str] = None,
                            ip_address: Optional[str] = None):
        """Log patient access event"""
        self._log_event(
            action="PATIENT_ACCESSED",
            resource_type="Patient",
            resource_id=patient_id,
            user_id=user_id,
            ip_address=ip_address
        )
    
    def log_patient_search(self, criteria: Dict[str, Any], result_count: int,
                          user_id: Optional[str] = None, ip_address: Optional[str] = None):
        """Log patient search event"""
        # Remove sensitive search criteria
        safe_criteria = {k: v for k, v in criteria.items() 
                        if k not in ['email', 'phone_number']}
        self._log_event(
            action="PATIENT_SEARCH",
            resource_type="Patient",
            details={"criteria": safe_criteria, "result_count": result_count},
            user_id=user_id,
            ip_address=ip_address
        )
    
    def log_patient_deactivated(self, patient_id: str, user_id: Optional[str] = None,
                               ip_address: Optional[str] = None):
        """Log patient deactivation event"""
        self._log_event(
            action="PATIENT_DEACTIVATED",
            resource_type="Patient",
            resource_id=patient_id,
            user_id=user_id,
            ip_address=ip_address
        )
    
    def _log_event(self, action: str, resource_type: str, resource_id: Optional[str] = None,
                   details: Optional[Dict[str, Any]] = None, user_id: Optional[str] = None,
                   ip_address: Optional[str] = None):
        """Log an audit event"""
        event = {
            "timestamp": datetime.utcnow().isoformat(),
            "action": action,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "user_id": user_id or "system",
            "ip_address": ip_address or "unknown",
            "details": details or {}
        }
        
        self.logger.info(f"AUDIT: {event}")


# JWT and Password handling
ALGORITHM = "HS256"
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password"""
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a JWT access token
    
    Args:
        data: Data to encode in the token
        expires_delta: Token expiration time
        
    Returns:
        str: JWT token
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Verify and decode a JWT token
    
    Args:
        token: JWT token to verify
        
    Returns:
        dict: Decoded token payload or None if invalid
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None


# Global instances
data_encryption = DataEncryption()
audit_logger = AuditLogger()


def get_client_ip(request) -> str:
    """Extract client IP address from request"""
    # Check for forwarded IP first (in case of proxy/load balancer)
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    
    # Check for real IP header
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip
    
    # Fall back to direct client IP
    return getattr(request.client, "host", "unknown")


def sanitize_input(data: str) -> str:
    """
    Sanitize user input to prevent injection attacks
    
    Args:
        data: Input string to sanitize
        
    Returns:
        str: Sanitized string
    """
    if not data:
        return data
    
    # Remove potentially dangerous characters
    dangerous_chars = ['<', '>', '"', "'", '&', ';', '(', ')', '|', '`']
    sanitized = data
    
    for char in dangerous_chars:
        sanitized = sanitized.replace(char, '')
    
    # Limit length to prevent buffer overflow attacks
    return sanitized[:1000]  # Reasonable limit for most fields


def validate_sql_injection(query_params: Dict[str, Any]) -> bool:
    """
    Check for potential SQL injection patterns in query parameters
    
    Args:
        query_params: Dictionary of query parameters
        
    Returns:
        bool: True if safe, False if potential injection detected
    """
    sql_injection_patterns = [
        'union', 'select', 'insert', 'update', 'delete', 'drop', 'create',
        'alter', 'exec', 'execute', '--', '/*', '*/', 'xp_', 'sp_'
    ]
    
    for key, value in query_params.items():
        if isinstance(value, str):
            value_lower = value.lower()
            for pattern in sql_injection_patterns:
                if pattern in value_lower:
                    logger.warning(f"Potential SQL injection detected in {key}: {value}")
                    return False
    
    return True


