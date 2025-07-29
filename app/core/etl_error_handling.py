"""
Error handling and retry logic for ETL processes.
Provides robust error handling, retry mechanisms, and failure recovery for data pipeline operations.
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Callable, List
from functools import wraps
from enum import Enum
import json

logger = logging.getLogger(__name__)


class ETLErrorType(str, Enum):
    """Types of ETL errors."""
    DATABASE_CONNECTION = "database_connection"
    DATA_VALIDATION = "data_validation"
    AZURE_SERVICE = "azure_service"
    PIPELINE_EXECUTION = "pipeline_execution"
    DATA_EXPORT = "data_export"
    NETWORK_TIMEOUT = "network_timeout"
    AUTHENTICATION = "authentication"
    RESOURCE_LIMIT = "resource_limit"
    UNKNOWN = "unknown"


class ETLErrorSeverity(str, Enum):
    """Severity levels for ETL errors."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ETLError(Exception):
    """Custom exception for ETL operations."""
    
    def __init__(
        self, 
        message: str, 
        error_type: ETLErrorType = ETLErrorType.UNKNOWN,
        severity: ETLErrorSeverity = ETLErrorSeverity.MEDIUM,
        details: Optional[Dict[str, Any]] = None,
        retry_after: Optional[int] = None
    ):
        super().__init__(message)
        self.message = message
        self.error_type = error_type
        self.severity = severity
        self.details = details or {}
        self.retry_after = retry_after
        self.timestamp = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary for logging/storage."""
        return {
            "message": self.message,
            "error_type": self.error_type.value,
            "severity": self.severity.value,
            "details": self.details,
            "retry_after": self.retry_after,
            "timestamp": self.timestamp.isoformat()
        }


class RetryConfig:
    """Configuration for retry logic."""
    
    def __init__(
        self,
        max_attempts: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        jitter: bool = True
    ):
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter


class ETLErrorHandler:
    """Handles ETL errors with retry logic and failure recovery."""
    
    def __init__(self):
        self.error_history: List[Dict[str, Any]] = []
        self.max_history_size = 1000
        
        # Default retry configurations for different error types
        self.retry_configs = {
            ETLErrorType.DATABASE_CONNECTION: RetryConfig(max_attempts=5, base_delay=2.0),
            ETLErrorType.AZURE_SERVICE: RetryConfig(max_attempts=4, base_delay=5.0),
            ETLErrorType.NETWORK_TIMEOUT: RetryConfig(max_attempts=3, base_delay=1.0),
            ETLErrorType.PIPELINE_EXECUTION: RetryConfig(max_attempts=2, base_delay=10.0),
            ETLErrorType.DATA_EXPORT: RetryConfig(max_attempts=3, base_delay=3.0),
            ETLErrorType.AUTHENTICATION: RetryConfig(max_attempts=2, base_delay=5.0),
            ETLErrorType.RESOURCE_LIMIT: RetryConfig(max_attempts=1, base_delay=30.0),
            ETLErrorType.DATA_VALIDATION: RetryConfig(max_attempts=1),  # Don't retry validation errors
            ETLErrorType.UNKNOWN: RetryConfig(max_attempts=2, base_delay=5.0)
        }
    
    def classify_error(self, error: Exception) -> ETLErrorType:
        """Classify error type based on exception details."""
        error_message = str(error).lower()
        
        if "connection" in error_message or "database" in error_message:
            return ETLErrorType.DATABASE_CONNECTION
        elif "azure" in error_message or "blob" in error_message or "synapse" in error_message:
            return ETLErrorType.AZURE_SERVICE
        elif "timeout" in error_message or "timed out" in error_message:
            return ETLErrorType.NETWORK_TIMEOUT
        elif "pipeline" in error_message or "data factory" in error_message:
            return ETLErrorType.PIPELINE_EXECUTION
        elif "export" in error_message or "upload" in error_message:
            return ETLErrorType.DATA_EXPORT
        elif "auth" in error_message or "credential" in error_message or "permission" in error_message:
            return ETLErrorType.AUTHENTICATION
        elif "limit" in error_message or "quota" in error_message or "throttle" in error_message:
            return ETLErrorType.RESOURCE_LIMIT
        elif "validation" in error_message or "invalid" in error_message:
            return ETLErrorType.DATA_VALIDATION
        else:
            return ETLErrorType.UNKNOWN
    
    def determine_severity(self, error_type: ETLErrorType, error: Exception) -> ETLErrorSeverity:
        """Determine error severity based on type and context."""
        severity_map = {
            ETLErrorType.DATABASE_CONNECTION: ETLErrorSeverity.HIGH,
            ETLErrorType.AZURE_SERVICE: ETLErrorSeverity.HIGH,
            ETLErrorType.PIPELINE_EXECUTION: ETLErrorSeverity.HIGH,
            ETLErrorType.AUTHENTICATION: ETLErrorSeverity.CRITICAL,
            ETLErrorType.RESOURCE_LIMIT: ETLErrorSeverity.MEDIUM,
            ETLErrorType.NETWORK_TIMEOUT: ETLErrorSeverity.MEDIUM,
            ETLErrorType.DATA_EXPORT: ETLErrorSeverity.MEDIUM,
            ETLErrorType.DATA_VALIDATION: ETLErrorSeverity.LOW,
            ETLErrorType.UNKNOWN: ETLErrorSeverity.MEDIUM
        }
        
        return severity_map.get(error_type, ETLErrorSeverity.MEDIUM)
    
    def calculate_delay(self, attempt: int, config: RetryConfig) -> float:
        """Calculate delay for retry attempt."""
        delay = config.base_delay * (config.exponential_base ** (attempt - 1))
        delay = min(delay, config.max_delay)
        
        if config.jitter:
            import random
            delay *= (0.5 + random.random() * 0.5)  # Add 0-50% jitter
        
        return delay
    
    def should_retry(self, error_type: ETLErrorType, attempt: int) -> bool:
        """Determine if error should be retried."""
        config = self.retry_configs.get(error_type, self.retry_configs[ETLErrorType.UNKNOWN])
        return attempt < config.max_attempts
    
    def log_error(self, error: ETLError, context: Dict[str, Any] = None):
        """Log error with appropriate level based on severity."""
        log_data = {
            **error.to_dict(),
            "context": context or {}
        }
        
        if error.severity == ETLErrorSeverity.CRITICAL:
            logger.critical(f"Critical ETL error: {error.message}", extra=log_data)
        elif error.severity == ETLErrorSeverity.HIGH:
            logger.error(f"High severity ETL error: {error.message}", extra=log_data)
        elif error.severity == ETLErrorSeverity.MEDIUM:
            logger.warning(f"Medium severity ETL error: {error.message}", extra=log_data)
        else:
            logger.info(f"Low severity ETL error: {error.message}", extra=log_data)
        
        # Add to error history
        self.error_history.append({
            **log_data,
            "logged_at": datetime.utcnow().isoformat()
        })
        
        # Maintain history size
        if len(self.error_history) > self.max_history_size:
            self.error_history = self.error_history[-self.max_history_size:]
    
    async def handle_error_with_retry(
        self,
        func: Callable,
        *args,
        context: Dict[str, Any] = None,
        custom_retry_config: Optional[RetryConfig] = None,
        **kwargs
    ) -> Any:
        """Execute function with error handling and retry logic."""
        attempt = 1
        last_error = None
        
        while True:
            try:
                return await func(*args, **kwargs)
            
            except Exception as e:
                # Classify and wrap error
                error_type = self.classify_error(e)
                severity = self.determine_severity(error_type, e)
                
                etl_error = ETLError(
                    message=str(e),
                    error_type=error_type,
                    severity=severity,
                    details={
                        "attempt": attempt,
                        "function": func.__name__ if hasattr(func, '__name__') else str(func),
                        "args": str(args)[:200],  # Truncate for logging
                        "kwargs": str(kwargs)[:200]
                    }
                )
                
                # Log error
                self.log_error(etl_error, context)
                
                # Check if we should retry
                config = custom_retry_config or self.retry_configs.get(
                    error_type, 
                    self.retry_configs[ETLErrorType.UNKNOWN]
                )
                
                if not self.should_retry(error_type, attempt):
                    logger.error(f"Max retry attempts ({config.max_attempts}) exceeded for {func.__name__}")
                    raise etl_error
                
                # Calculate delay and wait
                delay = self.calculate_delay(attempt, config)
                logger.info(f"Retrying {func.__name__} in {delay:.2f} seconds (attempt {attempt + 1}/{config.max_attempts})")
                
                await asyncio.sleep(delay)
                attempt += 1
                last_error = etl_error
    
    def get_error_history(self, 
                         limit: Optional[int] = None,
                         error_type: Optional[ETLErrorType] = None,
                         severity: Optional[ETLErrorSeverity] = None,
                         since: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """Get filtered error history."""
        filtered_errors = self.error_history.copy()
        
        # Apply filters
        if error_type:
            filtered_errors = [e for e in filtered_errors if e.get("error_type") == error_type.value]
        
        if severity:
            filtered_errors = [e for e in filtered_errors if e.get("severity") == severity.value]
        
        if since:
            since_str = since.isoformat()
            filtered_errors = [e for e in filtered_errors if e.get("timestamp", "") >= since_str]
        
        # Apply limit
        if limit:
            filtered_errors = filtered_errors[-limit:]
        
        return filtered_errors
    
    def get_error_statistics(self, since: Optional[datetime] = None) -> Dict[str, Any]:
        """Get error statistics for monitoring."""
        errors = self.get_error_history(since=since)
        
        if not errors:
            return {
                "total_errors": 0,
                "by_type": {},
                "by_severity": {},
                "recent_critical": []
            }
        
        # Count by type
        by_type = {}
        for error in errors:
            error_type = error.get("error_type", "unknown")
            by_type[error_type] = by_type.get(error_type, 0) + 1
        
        # Count by severity
        by_severity = {}
        for error in errors:
            severity = error.get("severity", "unknown")
            by_severity[severity] = by_severity.get(severity, 0) + 1
        
        # Get recent critical errors
        recent_critical = [
            error for error in errors[-10:]  # Last 10 errors
            if error.get("severity") == ETLErrorSeverity.CRITICAL.value
        ]
        
        return {
            "total_errors": len(errors),
            "by_type": by_type,
            "by_severity": by_severity,
            "recent_critical": recent_critical,
            "period_start": since.isoformat() if since else None,
            "period_end": datetime.utcnow().isoformat()
        }


def with_etl_error_handling(
    context: Dict[str, Any] = None,
    retry_config: Optional[RetryConfig] = None
):
    """Decorator for ETL functions to add error handling and retry logic."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            error_handler = ETLErrorHandler()
            return await error_handler.handle_error_with_retry(
                func, *args, 
                context=context,
                custom_retry_config=retry_config,
                **kwargs
            )
        return wrapper
    return decorator


# Global error handler instance
etl_error_handler = ETLErrorHandler()