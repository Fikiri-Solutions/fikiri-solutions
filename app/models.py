"""
Fikiri Solutions - Database Models
SQLAlchemy models for PostgreSQL
"""

from sqlalchemy import Column, String, Integer, Boolean, ForeignKey, JSON, DateTime, func, Text
from sqlalchemy.orm import relationship
from .db import Base

class Organization(Base):
    """Organization model for multi-tenant support"""
    __tablename__ = "organizations"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(120), nullable=False, unique=True)
    domain = Column(String(255), unique=True, nullable=True)
    settings = Column(JSON, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # Relationships
    users = relationship("User", back_populates="org")
    leads = relationship("Lead", back_populates="org")
    automations = relationship("Automation", back_populates="org")

class User(Base):
    """User model with OAuth support"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    org_id = Column(Integer, ForeignKey("organizations.id"), nullable=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    name = Column(String(120), nullable=True)
    is_admin = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    
    # OAuth fields
    provider = Column(String(50), nullable=True)  # google, microsoft, auth0
    sub = Column(String(255), index=True, nullable=True)  # OIDC subject
    provider_id = Column(String(255), nullable=True)  # Provider-specific ID
    
    # Profile data
    avatar_url = Column(String(500), nullable=True)
    phone = Column(String(20), nullable=True)
    timezone = Column(String(50), default="UTC")
    
    # Timestamps
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    last_login = Column(DateTime, nullable=True)
    
    # Relationships
    org = relationship("Organization", back_populates="users")

class Lead(Base):
    """Lead model for CRM functionality"""
    __tablename__ = "leads"
    
    id = Column(Integer, primary_key=True, index=True)
    org_id = Column(Integer, ForeignKey("organizations.id"), nullable=True)
    
    # Contact information
    email = Column(String(255), index=True, nullable=True)
    name = Column(String(120), nullable=True)
    phone = Column(String(20), nullable=True)
    company = Column(String(120), nullable=True)
    
    # Lead data
    source = Column(String(50), nullable=True)  # landing, onboarding, import, api
    status = Column(String(50), default="new")  # new, contacted, qualified, converted, lost
    score = Column(Integer, default=0)  # Lead scoring
    
    # Additional data
    meta = Column(JSON, nullable=True)  # Custom fields, tags, etc.
    notes = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    last_contacted = Column(DateTime, nullable=True)
    
    # Relationships
    org = relationship("Organization", back_populates="leads")

class Automation(Base):
    """Automation model for workflow management"""
    __tablename__ = "automations"
    
    id = Column(Integer, primary_key=True, index=True)
    org_id = Column(Integer, ForeignKey("organizations.id"), nullable=True)
    
    # Automation details
    name = Column(String(120), nullable=False)
    description = Column(Text, nullable=True)
    trigger_type = Column(String(50), nullable=False)  # webhook, schedule, event
    trigger_config = Column(JSON, nullable=True)
    
    # Workflow steps
    steps = Column(JSON, nullable=False)  # Array of workflow steps
    
    # Status
    is_active = Column(Boolean, default=True)
    is_paused = Column(Boolean, default=False)
    
    # Statistics
    runs_count = Column(Integer, default=0)
    success_count = Column(Integer, default=0)
    failure_count = Column(Integer, default=0)
    
    # Timestamps
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    last_run = Column(DateTime, nullable=True)
    
    # Relationships
    org = relationship("Organization", back_populates="automations")

class Job(Base):
    """Background job model for Celery task tracking"""
    __tablename__ = "jobs"
    
    id = Column(Integer, primary_key=True, index=True)
    org_id = Column(Integer, ForeignKey("organizations.id"), nullable=True)
    
    # Job details
    task_name = Column(String(120), nullable=False)
    task_id = Column(String(255), unique=True, index=True)  # Celery task ID
    status = Column(String(50), default="pending")  # pending, running, success, failure, retry
    
    # Job data
    args = Column(JSON, nullable=True)
    kwargs = Column(JSON, nullable=True)
    result = Column(JSON, nullable=True)
    error = Column(Text, nullable=True)
    
    # Progress tracking
    progress = Column(Integer, default=0)  # 0-100
    progress_message = Column(String(255), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, server_default=func.now())
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    
    # Relationships
    org = relationship("Organization")

class Webhook(Base):
    """Webhook model for external integrations"""
    __tablename__ = "webhooks"
    
    id = Column(Integer, primary_key=True, index=True)
    org_id = Column(Integer, ForeignKey("organizations.id"), nullable=True)
    
    # Webhook details
    name = Column(String(120), nullable=False)
    url = Column(String(500), nullable=False)
    secret = Column(String(255), nullable=True)
    
    # Configuration
    events = Column(JSON, nullable=True)  # Array of events to listen for
    is_active = Column(Boolean, default=True)
    
    # Statistics
    calls_count = Column(Integer, default=0)
    success_count = Column(Integer, default=0)
    failure_count = Column(Integer, default=0)
    
    # Timestamps
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    last_called = Column(DateTime, nullable=True)
    
    # Relationships
    org = relationship("Organization")

class AuditLog(Base):
    """Audit log for tracking changes"""
    __tablename__ = "audit_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    org_id = Column(Integer, ForeignKey("organizations.id"), nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    # Action details
    action = Column(String(50), nullable=False)  # create, update, delete, login, etc.
    resource_type = Column(String(50), nullable=False)  # user, lead, automation, etc.
    resource_id = Column(String(50), nullable=True)
    
    # Change data
    old_values = Column(JSON, nullable=True)
    new_values = Column(JSON, nullable=True)
    
    # Request context
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(500), nullable=True)
    
    # Timestamp
    created_at = Column(DateTime, server_default=func.now())
    
    # Relationships
    org = relationship("Organization")
    user = relationship("User")
