"""
Database connection and session management.
"""
import logging
from typing import Generator
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import settings

logger = logging.getLogger(__name__)

# Create SQLAlchemy engine with connection pooling
engine = create_engine(
    settings.database_url,
    poolclass=QueuePool,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,  # Verify connections before use
    pool_recycle=3600,   # Recycle connections every hour
    echo=settings.LOG_LEVEL == "DEBUG",  # Log SQL queries in debug mode
)

# Create SessionLocal class
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)


@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    """Set database-specific connection parameters."""
    # This is primarily for SQLite, but can be extended for other databases
    pass


@event.listens_for(engine, "before_cursor_execute")
def receive_before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    """Log SQL queries for debugging."""
    if settings.LOG_LEVEL == "DEBUG":
        logger.debug(f"Executing SQL: {statement}")
        logger.debug(f"Parameters: {parameters}")


def get_db() -> Generator[Session, None, None]:
    """
    Dependency function to get database session.
    
    This function creates a new SQLAlchemy SessionLocal that will be used
    in a single request, and then close it once the request is finished.
    
    Yields:
        Session: SQLAlchemy database session
        
    Raises:
        SQLAlchemyError: If database connection fails
    """
    db = SessionLocal()
    try:
        yield db
    except SQLAlchemyError as e:
        logger.error(f"Database error occurred: {e}")
        db.rollback()
        raise
    except Exception as e:
        logger.error(f"Unexpected error occurred: {e}")
        db.rollback()
        raise
    finally:
        db.close()


def create_tables():
    """
    Create all tables in the database.
    
    This function should be called during application startup
    to ensure all tables exist.
    """
    try:
        from app.models import Base
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Error creating database tables: {e}")
        raise


def check_database_connection() -> bool:
    """
    Check if database connection is working.
    
    Returns:
        bool: True if connection is successful, False otherwise
    """
    try:
        with engine.connect() as connection:
            connection.execute("SELECT 1")
        logger.info("Database connection successful")
        return True
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        return False


class DatabaseManager:
    """
    Database manager class for handling database operations.
    """
    
    def __init__(self):
        self.engine = engine
        self.SessionLocal = SessionLocal
    
    def get_session(self) -> Session:
        """
        Get a new database session.
        
        Returns:
            Session: SQLAlchemy database session
        """
        return self.SessionLocal()
    
    def close_session(self, session: Session):
        """
        Close a database session.
        
        Args:
            session: SQLAlchemy database session to close
        """
        try:
            session.close()
        except Exception as e:
            logger.error(f"Error closing database session: {e}")
    
    def execute_transaction(self, operations: list):
        """
        Execute multiple database operations in a single transaction.
        
        Args:
            operations: List of database operations to execute
            
        Raises:
            SQLAlchemyError: If any operation fails
        """
        session = self.get_session()
        try:
            for operation in operations:
                operation(session)
            session.commit()
            logger.info("Transaction completed successfully")
        except Exception as e:
            session.rollback()
            logger.error(f"Transaction failed: {e}")
            raise
        finally:
            self.close_session(session)


# Global database manager instance
db_manager = DatabaseManager()