"""
Fikiri Solutions - API Endpoints
FastAPI endpoints for the new database models
"""

from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
import logging

from .db import get_db, init_database
from .models import Organization, User, Lead, Automation, Job, Webhook, AuditLog

logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Fikiri Solutions API",
    description="API for Fikiri Solutions with PostgreSQL support",
    version="1.0.0"
)

@app.on_event("startup")
async def startup_event():
    """Initialize database on startup"""
    try:
        init_database()
        logger.info("✅ Database initialized on startup")
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}")

@app.get("/")
async def root():
    """Root endpoint"""
    return {"message": "Fikiri Solutions API", "version": "1.0.0"}

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "database": "connected"}

# Organization endpoints
@app.get("/api/organizations", response_model=List[dict])
async def get_organizations(db: Session = Depends(get_db)):
    """Get all organizations"""
    try:
        organizations = db.query(Organization).all()
        return [
            {
                "id": org.id,
                "name": org.name,
                "domain": org.domain,
                "created_at": org.created_at.isoformat() if org.created_at else None
            }
            for org in organizations
        ]
    except Exception as e:
        logger.error(f"Error fetching organizations: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.post("/api/organizations", response_model=dict)
async def create_organization(
    name: str,
    domain: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Create a new organization"""
    try:
        # Check if organization already exists
        existing_org = db.query(Organization).filter(Organization.name == name).first()
        if existing_org:
            raise HTTPException(status_code=400, detail="Organization already exists")
        
        # Create new organization
        org = Organization(name=name, domain=domain)
        db.add(org)
        db.commit()
        db.refresh(org)
        
        return {
            "id": org.id,
            "name": org.name,
            "domain": org.domain,
            "created_at": org.created_at.isoformat() if org.created_at else None
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating organization: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Internal server error")

# User endpoints
@app.get("/api/users", response_model=List[dict])
async def get_users(db: Session = Depends(get_db)):
    """Get all users"""
    try:
        users = db.query(User).all()
        return [
            {
                "id": user.id,
                "email": user.email,
                "name": user.name,
                "is_admin": user.is_admin,
                "provider": user.provider,
                "created_at": user.created_at.isoformat() if user.created_at else None
            }
            for user in users
        ]
    except Exception as e:
        logger.error(f"Error fetching users: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.post("/api/users", response_model=dict)
async def create_user(
    email: str,
    name: Optional[str] = None,
    org_id: Optional[int] = None,
    provider: Optional[str] = None,
    sub: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Create a new user"""
    try:
        # Check if user already exists
        existing_user = db.query(User).filter(User.email == email).first()
        if existing_user:
            raise HTTPException(status_code=400, detail="User already exists")
        
        # Create new user
        user = User(
            email=email,
            name=name,
            org_id=org_id,
            provider=provider,
            sub=sub
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        
        return {
            "id": user.id,
            "email": user.email,
            "name": user.name,
            "is_admin": user.is_admin,
            "provider": user.provider,
            "created_at": user.created_at.isoformat() if user.created_at else None
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating user: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Internal server error")

# Lead endpoints
@app.get("/api/leads", response_model=List[dict])
async def get_leads(
    offset: int = 0,
    limit: int = 100,
    q: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Get leads with pagination and search"""
    try:
        query = db.query(Lead)
        
        # Apply search filter if provided
        if q:
            query = query.filter(
                (Lead.name.contains(q)) | 
                (Lead.email.contains(q)) | 
                (Lead.company.contains(q))
            )
        
        # Apply pagination
        leads = query.offset(offset).limit(limit).all()
        
        return [
            {
                "id": lead.id,
                "email": lead.email,
                "name": lead.name,
                "company": lead.company,
                "source": lead.source,
                "status": lead.status,
                "score": lead.score,
                "created_at": lead.created_at.isoformat() if lead.created_at else None
            }
            for lead in leads
        ]
    except Exception as e:
        logger.error(f"Error fetching leads: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.post("/api/leads", response_model=dict)
async def create_lead(
    email: Optional[str] = None,
    name: Optional[str] = None,
    company: Optional[str] = None,
    source: Optional[str] = None,
    org_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """Create a new lead"""
    try:
        # Create new lead
        lead = Lead(
            email=email,
            name=name,
            company=company,
            source=source or "api",
            org_id=org_id
        )
        db.add(lead)
        db.commit()
        db.refresh(lead)
        
        return {
            "id": lead.id,
            "email": lead.email,
            "name": lead.name,
            "company": lead.company,
            "source": lead.source,
            "status": lead.status,
            "score": lead.score,
            "created_at": lead.created_at.isoformat() if lead.created_at else None
        }
    except Exception as e:
        logger.error(f"Error creating lead: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Internal server error")

# Automation endpoints
@app.get("/api/automations", response_model=List[dict])
async def get_automations(db: Session = Depends(get_db)):
    """Get all automations"""
    try:
        automations = db.query(Automation).all()
        return [
            {
                "id": automation.id,
                "name": automation.name,
                "description": automation.description,
                "trigger_type": automation.trigger_type,
                "is_active": automation.is_active,
                "runs_count": automation.runs_count,
                "success_count": automation.success_count,
                "failure_count": automation.failure_count,
                "created_at": automation.created_at.isoformat() if automation.created_at else None
            }
            for automation in automations
        ]
    except Exception as e:
        logger.error(f"Error fetching automations: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

# Job endpoints
@app.get("/api/jobs", response_model=List[dict])
async def get_jobs(
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Get background jobs"""
    try:
        query = db.query(Job)
        
        # Apply status filter if provided
        if status:
            query = query.filter(Job.status == status)
        
        jobs = query.all()
        
        return [
            {
                "id": job.id,
                "task_name": job.task_name,
                "task_id": job.task_id,
                "status": job.status,
                "progress": job.progress,
                "progress_message": job.progress_message,
                "created_at": job.created_at.isoformat() if job.created_at else None,
                "started_at": job.started_at.isoformat() if job.started_at else None,
                "completed_at": job.completed_at.isoformat() if job.completed_at else None
            }
            for job in jobs
        ]
    except Exception as e:
        logger.error(f"Error fetching jobs: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
