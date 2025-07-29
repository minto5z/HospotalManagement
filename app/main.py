"""
Hospital Management System - Main FastAPI Application
"""
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import settings
from app.core.logging import setup_logging
from app.core.middleware import CorrelationMiddleware, AuthorizationLoggingMiddleware
from app.core.exceptions import (
    HospitalManagementException,
    hospital_management_exception_handler,
    http_exception_handler,
    validation_exception_handler,
    sqlalchemy_exception_handler,
    generic_exception_handler
)
from app.api.v1.api import api_router
from app.db.database import check_database_connection, create_tables

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager for startup and shutdown events.
    """
    # Startup
    logger.info("Starting Hospital Management System...")
    
    # Check database connection
    if not check_database_connection():
        logger.error("Failed to connect to database")
        raise Exception("Database connection failed")
    
    # Create tables if they don't exist
    try:
        create_tables()
        logger.info("Database initialization completed")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        raise
    
    # Start ETL scheduler
    try:
        from app.core.scheduler import etl_scheduler
        await etl_scheduler.start()
        logger.info("ETL scheduler started successfully")
    except Exception as e:
        logger.warning(f"ETL scheduler startup failed: {e}")
        # Don't fail the entire application if scheduler fails
    
    logger.info("Hospital Management System started successfully")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Hospital Management System...")
    
    # Stop ETL scheduler
    try:
        from app.core.scheduler import etl_scheduler
        await etl_scheduler.stop()
        logger.info("ETL scheduler stopped successfully")
    except Exception as e:
        logger.warning(f"ETL scheduler shutdown failed: {e}")
    
    logger.info("Hospital Management System shutdown completed")

# Create FastAPI app
app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Hospital Management System with Azure Synapse Analytics Integration",
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan
)

# Add custom middleware
app.add_middleware(CorrelationMiddleware)
app.add_middleware(AuthorizationLoggingMiddleware)

# Set up CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_HOSTS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register exception handlers
app.add_exception_handler(HospitalManagementException, hospital_management_exception_handler)
app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(SQLAlchemyError, sqlalchemy_exception_handler)
app.add_exception_handler(Exception, generic_exception_handler)

# Include API router
app.include_router(api_router, prefix=settings.API_V1_STR)

@app.get("/")
async def root():
    return {"message": "Hospital Management System API", "version": settings.VERSION}

@app.get("/health")
async def health_check():
    """
    Health check endpoint that includes database connectivity status.
    """
    db_status = "connected" if check_database_connection() else "disconnected"
    return {
        "status": "healthy" if db_status == "connected" else "unhealthy",
        "service": "hospital-management-api",
        "database": db_status,
        "version": settings.VERSION
    }