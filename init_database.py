#!/usr/bin/env python3
"""
Fikiri Solutions - Database Initialization Script
Simple script to initialize the database with new models
"""

import os
import sys
import logging

# Add the current directory to Python path
sys.path.append(os.path.dirname(__file__))

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    """Initialize the database with new models"""
    try:
        # Import database components
        from app.db import init_database, test_database_connection
        
        logger.info("🚀 Initializing Fikiri Solutions database...")
        
        # Test database connection
        if not test_database_connection():
            logger.error("❌ Database connection failed")
            return False
        
        # Initialize database
        init_database()
        
        logger.info("✅ Database initialization completed successfully!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
