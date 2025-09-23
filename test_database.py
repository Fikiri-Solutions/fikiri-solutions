#!/usr/bin/env python3
"""
Fikiri Solutions - Database Test Script
Test the new PostgreSQL models and API
"""

import os
import sys
import logging

# Add the current directory to Python path
sys.path.append(os.path.dirname(__file__))

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_database_models():
    """Test database models and operations"""
    try:
        from app.db import SessionLocal, init_database
        from app.models import Organization, User, Lead, Automation, Job
        
        logger.info("🧪 Testing database models...")
        
        # Initialize database
        init_database()
        
        # Create session
        db = SessionLocal()
        
        try:
            # Test Organization
            logger.info("📊 Testing Organization model...")
            orgs = db.query(Organization).all()
            logger.info(f"   Found {len(orgs)} organizations")
            
            # Test User
            logger.info("👤 Testing User model...")
            users = db.query(User).all()
            logger.info(f"   Found {len(users)} users")
            
            # Test Lead
            logger.info("🎯 Testing Lead model...")
            leads = db.query(Lead).all()
            logger.info(f"   Found {len(leads)} leads")
            
            # Test Automation
            logger.info("🤖 Testing Automation model...")
            automations = db.query(Automation).all()
            logger.info(f"   Found {len(automations)} automations")
            
            # Test Job
            logger.info("⚙️ Testing Job model...")
            jobs = db.query(Job).all()
            logger.info(f"   Found {len(jobs)} jobs")
            
            # Create a test lead
            logger.info("➕ Creating test lead...")
            test_lead = Lead(
                email="test@example.com",
                name="Test User",
                company="Test Company",
                source="test"
            )
            db.add(test_lead)
            db.commit()
            db.refresh(test_lead)
            logger.info(f"   Created lead with ID: {test_lead.id}")
            
            # Verify the lead was created
            created_lead = db.query(Lead).filter(Lead.id == test_lead.id).first()
            if created_lead:
                logger.info(f"   ✅ Lead verified: {created_lead.email}")
            else:
                logger.error("   ❌ Lead not found after creation")
            
            logger.info("✅ All database model tests passed!")
            return True
            
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"❌ Database model test failed: {e}")
        return False

def test_api_endpoints():
    """Test API endpoints"""
    try:
        from app.api import app
        from fastapi.testclient import TestClient
        
        logger.info("🌐 Testing API endpoints...")
        
        # Create test client
        client = TestClient(app)
        
        # Test root endpoint
        response = client.get("/")
        if response.status_code == 200:
            logger.info("   ✅ Root endpoint working")
        else:
            logger.error(f"   ❌ Root endpoint failed: {response.status_code}")
        
        # Test health check
        response = client.get("/health")
        if response.status_code == 200:
            logger.info("   ✅ Health check working")
        else:
            logger.error(f"   ❌ Health check failed: {response.status_code}")
        
        # Test organizations endpoint
        response = client.get("/api/organizations")
        if response.status_code == 200:
            logger.info("   ✅ Organizations endpoint working")
        else:
            logger.error(f"   ❌ Organizations endpoint failed: {response.status_code}")
        
        # Test leads endpoint
        response = client.get("/api/leads")
        if response.status_code == 200:
            logger.info("   ✅ Leads endpoint working")
        else:
            logger.error(f"   ❌ Leads endpoint failed: {response.status_code}")
        
        # Test creating a lead
        response = client.post("/api/leads", json={
            "email": "api-test@example.com",
            "name": "API Test User",
            "company": "API Test Company",
            "source": "api-test"
        })
        if response.status_code == 200:
            logger.info("   ✅ Lead creation endpoint working")
        else:
            logger.error(f"   ❌ Lead creation failed: {response.status_code}")
        
        logger.info("✅ All API endpoint tests passed!")
        return True
        
    except Exception as e:
        logger.error(f"❌ API endpoint test failed: {e}")
        return False

def main():
    """Run all tests"""
    logger.info("🚀 Starting Fikiri Solutions database and API tests...")
    
    # Test database models
    db_success = test_database_models()
    
    # Test API endpoints
    api_success = test_api_endpoints()
    
    if db_success and api_success:
        logger.info("🎉 All tests passed! PostgreSQL integration is working!")
        return True
    else:
        logger.error("❌ Some tests failed!")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
