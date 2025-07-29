"""
Custom middleware for the Hospital Management System
"""
import uuid
import time
import logging
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.security import verify_token

logger = logging.getLogger(__name__)


class CorrelationMiddleware(BaseHTTPMiddleware):
    """Add correlation ID to requests for tracing"""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Generate or extract correlation ID
        correlation_id = request.headers.get("X-Correlation-ID", str(uuid.uuid4()))
        
        # Add to request state
        request.state.correlation_id = correlation_id
        
        # Process request
        start_time = time.time()
        response = await call_next(request)
        process_time = time.time() - start_time
        
        # Add correlation ID to response headers
        response.headers["X-Correlation-ID"] = correlation_id
        response.headers["X-Process-Time"] = str(process_time)
        
        # Log request
        logger.info(
            f"Request processed",
            extra={
                "correlation_id": correlation_id,
                "method": request.method,
                "url": str(request.url),
                "status_code": response.status_code,
                "process_time": process_time
            }
        )
        
        return response


class AuthorizationLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware to log authorization events"""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Extract user info from JWT token if present
        user_info = None
        auth_header = request.headers.get("Authorization")
        
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
            payload = verify_token(token)
            if payload:
                user_info = {
                    "user_id": payload.get("user_id"),
                    "username": payload.get("sub"),
                    "role": payload.get("role")
                }
        
        # Store user info in request state for logging
        request.state.user_info = user_info
        
        # Process request
        response = await call_next(request)
        
        # Log authorization events for protected endpoints
        if user_info and request.url.path.startswith("/api/"):
            from app.core.security import audit_logger
            audit_logger._log_event(
                action="API_ACCESS",
                resource_type="Endpoint",
                resource_id=f"{request.method} {request.url.path}",
                user_id=user_info["user_id"],
                details={
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code,
                    "user_role": user_info["role"]
                }
            )
        
        return response