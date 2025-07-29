#!/usr/bin/env python3
"""
Database initialization script for Hospital Management System.

This script can be run independently to initialize the database,
create tables, and optionally seed with sample data.
"""
import sys
import os
import logging
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.core.config import settings
from app.core.logging import setup_logging
from app.db.database import engine, check_database_connection, create_tables
from app.models import Base

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)


def init_database():
    """
    Initialize the database by creating all tables.
    """
    logger.info("Initializing Hospital Management System database...")
    
    # Check database connection
    if not check_database_connection():
        logger.error("Failed to connect to database. Please check your configuration.")
        return False
    
    try:
        # Create all tables
        logger.info("Creating database tables...")
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully")
        
        # Verify tables were created
        inspector = engine.inspect(engine)
        tables = inspector.get_table_names()
        expected_tables = ['patients', 'doctors', 'appointments', 'hospital_resources', 'doctor_schedules']
        
        missing_tables = [table for table in expected_tables if table not in tables]
        if missing_tables:
            logger.warning(f"Some tables were not created: {missing_tables}")
        else:
            logger.info("All expected tables created successfully")
        
        return True
        
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        return False


def drop_all_tables():
    """
    Drop all tables from the database.
    WARNING: This will delete all data!
    """
    logger.warning("Dropping all database tables...")
    
    try:
        Base.metadata.drop_all(bind=engine)
        logger.info("All tables dropped successfully")
        return True
    except Exception as e:
        logger.error(f"Failed to drop tables: {e}")
        return False


def reset_database():
    """
    Reset the database by dropping and recreating all tables.
    WARNING: This will delete all data!
    """
    logger.warning("Resetting database...")
    
    if drop_all_tables() and init_database():
        logger.info("Database reset completed successfully")
        return True
    else:
        logger.error("Database reset failed")
        return False


def main():
    """
    Main function to handle command line arguments.
    """
    import argparse
    
    parser = argparse.ArgumentParser(description="Hospital Management System Database Initialization")
    parser.add_argument(
        "--action",
        choices=["init", "drop", "reset"],
        default="init",
        help="Action to perform: init (create tables), drop (drop all tables), reset (drop and recreate)"
    )
    parser.add_argument(
        "--confirm",
        action="store_true",
        help="Confirm destructive operations (required for drop and reset)"
    )
    
    args = parser.parse_args()
    
    if args.action == "init":
        success = init_database()
    elif args.action == "drop":
        if not args.confirm:
            logger.error("Drop operation requires --confirm flag")
            return 1
        success = drop_all_tables()
    elif args.action == "reset":
        if not args.confirm:
            logger.error("Reset operation requires --confirm flag")
            return 1
        success = reset_database()
    
    return 0 if success else 1


if __name__ == "__main__":
    exit(main())