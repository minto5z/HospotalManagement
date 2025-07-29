"""
Database utility functions for common operations.
"""
import logging
from typing import Optional, List, Dict, Any
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import text

from app.db.database import get_db

logger = logging.getLogger(__name__)


def execute_raw_sql(query: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """
    Execute raw SQL query and return results.
    
    Args:
        query: SQL query string
        params: Query parameters
        
    Returns:
        List of dictionaries containing query results
        
    Raises:
        SQLAlchemyError: If query execution fails
    """
    db = next(get_db())
    try:
        result = db.execute(text(query), params or {})
        if result.returns_rows:
            columns = result.keys()
            return [dict(zip(columns, row)) for row in result.fetchall()]
        return []
    except SQLAlchemyError as e:
        logger.error(f"Raw SQL execution failed: {e}")
        raise
    finally:
        db.close()


def check_record_exists(session: Session, model_class, **filters) -> bool:
    """
    Check if a record exists in the database.
    
    Args:
        session: Database session
        model_class: SQLAlchemy model class
        **filters: Filter conditions
        
    Returns:
        bool: True if record exists, False otherwise
    """
    try:
        query = session.query(model_class)
        for key, value in filters.items():
            query = query.filter(getattr(model_class, key) == value)
        return query.first() is not None
    except Exception as e:
        logger.error(f"Error checking record existence: {e}")
        return False


def get_record_by_id(session: Session, model_class, record_id: UUID):
    """
    Get a record by its ID.
    
    Args:
        session: Database session
        model_class: SQLAlchemy model class
        record_id: Record ID
        
    Returns:
        Model instance or None if not found
    """
    try:
        return session.query(model_class).filter(
            getattr(model_class, f"{model_class.__tablename__.rstrip('s')}_id") == record_id
        ).first()
    except Exception as e:
        logger.error(f"Error getting record by ID: {e}")
        return None


def soft_delete_record(session: Session, model_instance) -> bool:
    """
    Soft delete a record by setting is_active to False.
    
    Args:
        session: Database session
        model_instance: Model instance to soft delete
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        if hasattr(model_instance, 'is_active'):
            model_instance.is_active = False
            session.commit()
            return True
        else:
            logger.warning(f"Model {type(model_instance)} does not support soft delete")
            return False
    except Exception as e:
        logger.error(f"Error soft deleting record: {e}")
        session.rollback()
        return False


def bulk_insert(session: Session, model_class, records: List[Dict[str, Any]]) -> bool:
    """
    Bulk insert records into the database.
    
    Args:
        session: Database session
        model_class: SQLAlchemy model class
        records: List of dictionaries containing record data
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        session.bulk_insert_mappings(model_class, records)
        session.commit()
        logger.info(f"Successfully inserted {len(records)} records")
        return True
    except Exception as e:
        logger.error(f"Error bulk inserting records: {e}")
        session.rollback()
        return False


def get_table_row_count(session: Session, model_class) -> int:
    """
    Get the total number of rows in a table.
    
    Args:
        session: Database session
        model_class: SQLAlchemy model class
        
    Returns:
        int: Number of rows in the table
    """
    try:
        return session.query(model_class).count()
    except Exception as e:
        logger.error(f"Error getting table row count: {e}")
        return 0


def validate_foreign_key(session: Session, model_class, foreign_key_field: str, foreign_key_value: UUID) -> bool:
    """
    Validate that a foreign key reference exists.
    
    Args:
        session: Database session
        model_class: SQLAlchemy model class for the referenced table
        foreign_key_field: Name of the foreign key field
        foreign_key_value: Value of the foreign key
        
    Returns:
        bool: True if foreign key is valid, False otherwise
    """
    try:
        return session.query(model_class).filter(
            getattr(model_class, foreign_key_field) == foreign_key_value
        ).first() is not None
    except Exception as e:
        logger.error(f"Error validating foreign key: {e}")
        return False


class DatabaseTransaction:
    """
    Context manager for database transactions.
    """
    
    def __init__(self, session: Session):
        self.session = session
        self._transaction = None
    
    def __enter__(self):
        self._transaction = self.session.begin()
        return self.session
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            self._transaction.rollback()
            logger.error(f"Transaction rolled back due to error: {exc_val}")
        else:
            self._transaction.commit()
            logger.debug("Transaction committed successfully")
        return False