#!/usr/bin/env python3
"""
Fikiri Solutions - Minimal CRM Service
Lightweight CRM functionality with production enhancements.
"""

import json
import csv
import io
import os
import threading
import logging
from typing import Dict, Any, List, Optional
from pathlib import Path
from datetime import datetime, timezone
from contextlib import contextmanager

# Optional Redis integration
try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    redis = None

logger = logging.getLogger(__name__)

class MinimalLead:
    """Minimal lead data structure with enhanced features."""
    
    def __init__(self, email: str, name: str = "", source: str = "email"):
        """Initialize a lead."""
        self.id = self._generate_id()
        self.email = email
        self.name = name
        self.source = source
        self.stage = "new"
        self.created_at = datetime.now(timezone.utc).isoformat()
        self.updated_at = datetime.now(timezone.utc).isoformat()
        self.tags = []
        self.notes = []
        self.last_contact = None
        self.contact_count = 0
        self.score = 0  # Lead scoring
        self.company = ""  # Company name
        self.phone = ""  # Phone number
        self.metadata = {}  # Additional metadata
    
    def _generate_id(self) -> str:
        """Generate a simple ID."""
        import uuid
        return str(uuid.uuid4())[:8]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert lead to dictionary."""
        return {
            "id": self.id,
            "email": self.email,
            "name": self.name,
            "source": self.source,
            "stage": self.stage,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "tags": self.tags,
            "notes": self.notes,
            "last_contact": self.last_contact,
            "contact_count": self.contact_count,
            "score": self.score,
            "company": self.company,
            "phone": self.phone,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MinimalLead':
        """Create lead from dictionary."""
        lead = cls(data["email"], data.get("name", ""), data.get("source", "email"))
        lead.id = data["id"]
        lead.stage = data.get("stage", "new")
        lead.created_at = data.get("created_at", datetime.now(timezone.utc).isoformat())
        lead.updated_at = data.get("updated_at", datetime.now(timezone.utc).isoformat())
        lead.tags = data.get("tags", [])
        # Handle case where tags might be a string instead of list
        if isinstance(lead.tags, str):
            lead.tags = [lead.tags] if lead.tags else []
        lead.notes = data.get("notes", [])
        # Handle case where notes might be None or not a list
        if lead.notes is None or not isinstance(lead.notes, list):
            lead.notes = []
        lead.last_contact = data.get("last_contact")
        lead.contact_count = data.get("contact_count", 0)
        lead.score = data.get("score", 0)
        lead.company = data.get("company", "")
        lead.phone = data.get("phone", "")
        lead.metadata = data.get("metadata", {})
        return lead

class MinimalCRMService:
    """Minimal CRM service with production enhancements."""
    
    def __init__(self, data_path: str = "data/leads.json", services: Dict[str, Any] = None):
        """Initialize minimal CRM service with enhanced features."""
        self.data_path = Path(data_path)
        self.leads: List[MinimalLead] = []
        self.services = services or {}
        self.lock = threading.Lock()  # Thread safety
        
        # Redis client for persistence and caching
        self.redis_client = None
        self._initialize_redis()
        
        # Database optimizer for PostgreSQL mirror
        self.db_optimizer = None
        self._initialize_database()
        
        # Load leads
        self.load_leads()
    
    def _initialize_redis(self):
        """Initialize Redis client for persistence and caching."""
        if not REDIS_AVAILABLE:
            logger.info("ℹ️ Redis not available for CRM persistence")
            return
        
        try:
            redis_url = os.getenv('REDIS_URL')
            if redis_url:
                self.redis_client = redis.from_url(redis_url, decode_responses=True)
            else:
                self.redis_client = redis.Redis(
                    host=os.getenv('REDIS_HOST', 'localhost'),
                    port=int(os.getenv('REDIS_PORT', 6379)),
                    password=os.getenv('REDIS_PASSWORD'),
                    db=int(os.getenv('REDIS_DB', 0)),
                    decode_responses=True
                )
            
            self.redis_client.ping()
            logger.info("✅ Redis initialized for CRM persistence")
            
        except Exception as e:
            logger.error(f"❌ Redis initialization failed: {e}")
            self.redis_client = None
    
    def _initialize_database(self):
        """Initialize database for PostgreSQL mirror."""
        try:
            from core.database_optimization import db_optimizer
            self.db_optimizer = db_optimizer
            logger.info("✅ Database initialized for CRM mirror")
        except Exception as e:
            logger.error(f"❌ Database initialization failed: {e}")
    
    @contextmanager
    def _file_lock(self):
        """Context manager for file locking."""
        with self.lock:
            yield
    
    def load_leads(self) -> bool:
        """Load leads from file with thread safety."""
        try:
            with self._file_lock():
                if self.data_path.exists():
                    with open(self.data_path, 'r') as f:
                        data = json.load(f)
                        
                        # Handle different JSON structures
                        if isinstance(data, dict) and 'leads' in data:
                            # Handle wrapped format: {"leads": [...]}
                            leads_data = data['leads']
                        elif isinstance(data, list):
                            # Handle direct array format: [...]
                            leads_data = data
                        else:
                            leads_data = []
                        
                        self.leads = [MinimalLead.from_dict(lead_data) for lead_data in leads_data]
                    logger.info(f"✅ Loaded {len(self.leads)} leads from {self.data_path}")
                    
                    # Mirror to Redis if available
                    self._mirror_to_redis()
                    
                    return True
                else:
                    logger.info(f"📝 No leads file found at {self.data_path}")
                    return True
        except Exception as e:
            logger.error(f"❌ Error loading leads: {e}")
            return False
    
    def save_leads(self) -> bool:
        """Save leads to file with thread safety and persistence."""
        try:
            with self._file_lock():
                # Ensure data directory exists
                self.data_path.parent.mkdir(exist_ok=True)
                
                # Convert leads to dictionaries
                leads_data = [lead.to_dict() for lead in self.leads]
                
                with open(self.data_path, 'w') as f:
                    json.dump(leads_data, f, indent=2)
                
                logger.info(f"✅ Saved {len(self.leads)} leads to {self.data_path}")
                
                # Mirror to Redis and PostgreSQL
                self._mirror_to_redis()
                self._mirror_to_database()
                
                # Invalidate cache
                self._invalidate_cache()
                
                return True
        except Exception as e:
            logger.error(f"❌ Error saving leads: {e}")
            return False
    
    def _mirror_to_redis(self):
        """Mirror leads to Redis for persistence."""
        if not self.redis_client:
            return
        
        try:
            # Store all leads in Redis
            for lead in self.leads:
                lead_dict = lead.to_dict()
                # Convert lists and None values for Redis compatibility
                for key, value in lead_dict.items():
                    if isinstance(value, list):
                        lead_dict[key] = json.dumps(value)
                    elif value is None:
                        lead_dict[key] = ""  # Replace None with empty string
                self.redis_client.hset(f"fikiri:lead:{lead.id}", mapping=lead_dict)
            
            # Store lead IDs for quick access
            lead_ids = [lead.id for lead in self.leads]
            self.redis_client.set("fikiri:lead:ids", json.dumps(lead_ids))
            
            logger.info(f"✅ Mirrored {len(self.leads)} leads to Redis")
        except Exception as e:
            logger.error(f"❌ Redis mirror failed: {e}")
    
    def _mirror_to_database(self):
        """Mirror leads to PostgreSQL database."""
        if not self.db_optimizer:
            return
        
        try:
            # Ensure leads table exists
            self.db_optimizer.execute_query("""
                CREATE TABLE IF NOT EXISTS leads (
                    id TEXT PRIMARY KEY,
                    email TEXT NOT NULL,
                    name TEXT,
                    source TEXT DEFAULT 'email',
                    stage TEXT DEFAULT 'new',
                    created_at TIMESTAMP,
                    updated_at TIMESTAMP,
                    tags TEXT,  -- JSON array
                    notes TEXT,  -- JSON array
                    last_contact TIMESTAMP,
                    contact_count INTEGER DEFAULT 0,
                    score INTEGER DEFAULT 0,
                    company TEXT,
                    phone TEXT,
                    metadata TEXT  -- JSON object
                )
            """, fetch=False)
            
            # Upsert leads
            for lead in self.leads:
                self.db_optimizer.execute_query("""
                    INSERT OR REPLACE INTO leads 
                    (id, email, name, source, stage, created_at, updated_at, 
                     tags, notes, last_contact, contact_count, score, company, phone, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    lead.id, lead.email, lead.name, lead.source, lead.stage,
                    lead.created_at, lead.updated_at,
                    json.dumps(lead.tags), json.dumps(lead.notes),
                    lead.last_contact, lead.contact_count, lead.score,
                    lead.company, lead.phone, json.dumps(lead.metadata)
                ), fetch=False)
            
            logger.info(f"✅ Mirrored {len(self.leads)} leads to database")
        except Exception as e:
            logger.error(f"❌ Database mirror failed: {e}")
    
    def _invalidate_cache(self):
        """Invalidate Redis cache for lead stats."""
        if not self.redis_client:
            return
        
        try:
            self.redis_client.delete("fikiri:crm:stats")
            logger.info("✅ Invalidated CRM stats cache")
        except Exception as e:
            logger.error(f"❌ Cache invalidation failed: {e}")
    
    def add_lead(self, email: str, name: str = "", source: str = "email", 
                 company: str = "", phone: str = "", metadata: Dict[str, Any] = None) -> MinimalLead:
        """Add a new lead with validation and AI integration."""
        # Validate input parameters
        if not email or not isinstance(email, str):
            raise ValueError("Email must be a non-empty string")
        
        if not isinstance(name, str):
            name = str(name) if name is not None else ""
        
        if not isinstance(source, str):
            source = str(source) if source is not None else "email"
        
        # Basic email validation
        import re
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, email):
            raise ValueError(f"Invalid email format: {email}")
        
        # Check if lead already exists
        existing_lead = self.find_lead_by_email(email)
        if existing_lead:
            logger.info(f"⚠️ Lead with email {email} already exists")
            return existing_lead
        
        # Create new lead
        lead = MinimalLead(email.strip().lower(), name.strip(), source.strip())
        lead.company = company.strip() if company else ""
        lead.phone = phone.strip() if phone else ""
        lead.metadata = metadata or {}
        
        # AI-powered lead scoring if available
        if 'ai_assistant' in self.services:
            try:
                lead.score = self._calculate_lead_score(lead)
                logger.info(f"✅ AI-scored lead {email}: {lead.score}")
            except Exception as e:
                logger.warning(f"AI scoring failed: {e}")
        
        self.leads.append(lead)
        
        # Auto-save and mirror
        self.save_leads()
        
        logger.info(f"✅ Added new lead: {email}")
        return lead
    
    def _calculate_lead_score(self, lead: MinimalLead) -> int:
        """Calculate lead score using AI assistant."""
        try:
            # Simple scoring based on available data
            score = 0
            
            # Email domain scoring
            domain = lead.email.split('@')[1].lower()
            if domain in ['gmail.com', 'yahoo.com', 'hotmail.com']:
                score += 10  # Personal email
            else:
                score += 20  # Business email
            
            # Name completeness
            if lead.name and len(lead.name.split()) >= 2:
                score += 15
            
            # Company information
            if lead.company:
                score += 25
            
            # Phone information
            if lead.phone:
                score += 20
            
            # Source scoring
            if lead.source in ['website', 'referral']:
                score += 30
            elif lead.source == 'email':
                score += 20
            
            return min(score, 100)  # Cap at 100
        except Exception as e:
            logger.error(f"Lead scoring failed: {e}")
            return 0
    
    def find_lead_by_email(self, email: str) -> Optional[MinimalLead]:
        """Find lead by email address."""
        for lead in self.leads:
            if lead.email.lower() == email.lower():
                return lead
        return None
    
    def find_lead_by_id(self, lead_id: str) -> Optional[MinimalLead]:
        """Find lead by ID."""
        for lead in self.leads:
            if lead.id == lead_id:
                return lead
        return None
    
    def update_lead_stage(self, lead_id: str, new_stage: str) -> bool:
        """Update lead stage."""
        lead = self.find_lead_by_id(lead_id)
        if not lead:
            logger.error(f"❌ Lead with ID {lead_id} not found")
            return False
        
        old_stage = lead.stage
        lead.stage = new_stage
        lead.updated_at = datetime.now(timezone.utc).isoformat()
        
        # Auto-save
        self.save_leads()
        
        logger.info(f"✅ Updated lead {lead.email} from {old_stage} to {new_stage}")
        return True
    
    def add_note(self, lead_id: str, note: str) -> bool:
        """Add note to lead."""
        lead = self.find_lead_by_id(lead_id)
        if not lead:
            logger.error(f"❌ Lead with ID {lead_id} not found")
            return False
        
        # Ensure notes is a list
        if lead.notes is None:
            lead.notes = []
        
        timestamp = datetime.now(timezone.utc).isoformat()
        lead.notes.append({
            "timestamp": timestamp,
            "note": note
        })
        lead.updated_at = timestamp
        
        # Auto-save
        self.save_leads()
        
        logger.info(f"✅ Added note to lead {lead.email}")
        return True
    
    def add_tag(self, lead_id: str, tag: str) -> bool:
        """Add tag to lead."""
        lead = self.find_lead_by_id(lead_id)
        if not lead:
            logger.error(f"❌ Lead with ID {lead_id} not found")
            return False
        
        # Ensure tags is a list
        if lead.tags is None:
            lead.tags = []
        
        if tag not in lead.tags:
            lead.tags.append(tag)
            lead.updated_at = datetime.now(timezone.utc).isoformat()
            
            # Auto-save
            self.save_leads()
            
            logger.info(f"✅ Added tag '{tag}' to lead {lead.email}")
        else:
            logger.info(f"⚠️ Tag '{tag}' already exists for lead {lead.email}")
        
        return True
    
    def record_contact(self, lead_id: str, contact_type: str = "email") -> bool:
        """Record contact with lead."""
        lead = self.find_lead_by_id(lead_id)
        if not lead:
            logger.error(f"❌ Lead with ID {lead_id} not found")
            return False
        
        lead.contact_count += 1
        lead.last_contact = datetime.now(timezone.utc).isoformat()
        lead.updated_at = lead.last_contact
        
        # Auto-save
        self.save_leads()
        
        logger.info(f"✅ Recorded {contact_type} contact with lead {lead.email}")
        return True
    
    def get_leads_by_stage(self, stage: str) -> List[MinimalLead]:
        """Get leads by stage."""
        return [lead for lead in self.leads if lead.stage == stage]
    
    def get_leads_by_tag(self, tag: str) -> List[MinimalLead]:
        """Get leads by tag."""
        return [lead for lead in self.leads if tag in lead.tags]
    
    def get_all_leads(self) -> List[Dict[str, Any]]:
        """Get all leads as dictionaries."""
        return [lead.to_dict() for lead in self.leads]
    
    def get_lead_stats(self) -> Dict[str, Any]:
        """Get CRM statistics with Redis caching."""
        # Try to get from cache first
        if self.redis_client:
            try:
                cached_stats = self.redis_client.get("fikiri:crm:stats")
                if cached_stats:
                    logger.info("✅ Retrieved CRM stats from cache")
                    return json.loads(cached_stats)
            except Exception as e:
                logger.warning(f"Cache retrieval failed: {e}")
        
        # Calculate stats
        if not self.leads:
            stats = {
                "total_leads": 0,
                "stages": {},
                "sources": {},
                "tags": {},
                "recent_leads": 0,
                "high_score_leads": 0
            }
        else:
            # Count by stage
            stages = {}
            for lead in self.leads:
                stages[lead.stage] = stages.get(lead.stage, 0) + 1
            
            # Count by source
            sources = {}
            for lead in self.leads:
                sources[lead.source] = sources.get(lead.source, 0) + 1
            
            # Count by tag
            tags = {}
            for lead in self.leads:
                for tag in lead.tags:
                    tags[tag] = tags.get(tag, 0) + 1
            
            # Count recent leads (last 7 days)
            recent_count = 0
            week_ago = datetime.now(timezone.utc).timestamp() - (7 * 24 * 60 * 60)
            for lead in self.leads:
                lead_time = datetime.fromisoformat(lead.created_at.replace('Z', '+00:00')).timestamp()
                if lead_time > week_ago:
                    recent_count += 1
            
            # Count high-score leads
            high_score_count = len([lead for lead in self.leads if lead.score >= 70])
            
            stats = {
                "total_leads": len(self.leads),
                "stages": stages,
                "sources": sources,
                "tags": tags,
                "recent_leads": recent_count,
                "high_score_leads": high_score_count
            }
        
        # Cache the results
        if self.redis_client:
            try:
                self.redis_client.setex("fikiri:crm:stats", 300, json.dumps(stats))  # 5 minute cache
                logger.info("✅ Cached CRM stats")
            except Exception as e:
                logger.warning(f"Cache storage failed: {e}")
        
        return stats
    
    def export_leads(self, format: str = "json") -> str:
        """Export leads in specified format with enhanced CSV support."""
        if format == "json":
            leads_data = [lead.to_dict() for lead in self.leads]
            return json.dumps(leads_data, indent=2)
        elif format == "csv":
            # Enhanced CSV export with all fields
            output = io.StringIO()
            fieldnames = [
                'id', 'email', 'name', 'company', 'phone', 'stage', 'source', 
                'score', 'created_at', 'updated_at', 'last_contact', 'contact_count',
                'tags', 'notes'
            ]
            
            writer = csv.DictWriter(output, fieldnames=fieldnames)
            writer.writeheader()
            
            for lead in self.leads:
                row = {
                    'id': lead.id,
                    'email': lead.email,
                    'name': lead.name,
                    'company': lead.company,
                    'phone': lead.phone,
                    'stage': lead.stage,
                    'source': lead.source,
                    'score': lead.score,
                    'created_at': lead.created_at,
                    'updated_at': lead.updated_at,
                    'last_contact': lead.last_contact or '',
                    'contact_count': lead.contact_count,
                    'tags': '; '.join(lead.tags),
                    'notes': '; '.join([note.get('note', '') for note in lead.notes])
                }
                writer.writerow(row)
            
            return output.getvalue()
        else:
            return "Unsupported format"
    
    def process_email_for_lead(self, parsed_email: Dict[str, Any]) -> Optional[MinimalLead]:
        """Process email and create/update lead automatically."""
        try:
            sender_email = parsed_email.get("headers", {}).get("from", "")
            sender_name = parsed_email.get("headers", {}).get("from", "")
            subject = parsed_email.get("headers", {}).get("subject", "")
            
            # Extract email from sender
            if "<" in sender_email and ">" in sender_email:
                email = sender_email.split("<")[1].split(">")[0].strip()
                name = sender_email.split("<")[0].strip()
            else:
                email = sender_email
                name = ""
            
            # Extract company from email domain
            company = ""
            if "@" in email:
                domain = email.split("@")[1]
                if "." in domain:
                    company = domain.split(".")[0].title()
            
            # Create metadata
            metadata = {
                "email_subject": subject,
                "email_snippet": parsed_email.get("snippet", ""),
                "email_date": parsed_email.get("email_date"),
                "auto_created": True
            }
            
            # Check if lead exists
            existing_lead = self.find_lead_by_email(email)
            if existing_lead:
                # Update existing lead
                existing_lead.contact_count += 1
                existing_lead.last_contact = datetime.now(timezone.utc).isoformat()
                existing_lead.updated_at = existing_lead.last_contact
                
                # Add note about this email
                self.add_note(existing_lead.id, f"Email received: {subject}")
                
                logger.info(f"✅ Updated existing lead: {email}")
                return existing_lead
            else:
                # Create new lead
                lead = self.add_lead(
                    email=email,
                    name=name,
                    source="email",
                    company=company,
                    metadata=metadata
                )
                
                # Add note about initial email
                self.add_note(lead.id, f"Initial email: {subject}")
                
                logger.info(f"✅ Created new lead from email: {email}")
                return lead
                
        except Exception as e:
            logger.error(f"❌ Email processing failed: {e}")
            return None

def create_crm_service(data_path: str = "data/leads.json", services: Dict[str, Any] = None) -> MinimalCRMService:
    """Create and return a CRM service instance with services."""
    return MinimalCRMService(data_path, services)

if __name__ == "__main__":
    # Test the CRM service
    logger.info("🧪 Testing Enhanced Minimal CRM Service")
    logger.info("=" * 40)
    
    crm = MinimalCRMService("data/test_leads.json")
    
    # Test adding leads
    logger.info("Testing add lead...")
    lead1 = crm.add_lead("john.doe@example.com", "John Doe", "email", "Example Corp", "+1234567890")
    lead2 = crm.add_lead("jane.smith@example.com", "Jane Smith", "website")
    
    logger.info(f"✅ Added leads: {lead1.email}, {lead2.email}")
    
    # Test updating stage
    logger.info("Testing stage update...")
    crm.update_lead_stage(lead1.id, "qualified")
    crm.update_lead_stage(lead2.id, "contacted")
    
    # Test adding notes and tags
    logger.info("Testing notes and tags...")
    crm.add_note(lead1.id, "Interested in premium package")
    crm.add_tag(lead1.id, "premium")
    crm.add_tag(lead1.id, "hot")
    
    # Test recording contact
    logger.info("Testing contact recording...")
    crm.record_contact(lead1.id, "email")
    crm.record_contact(lead2.id, "phone")
    
    # Test stats
    logger.info("Testing stats...")
    stats = crm.get_lead_stats()
    logger.info(f"✅ Total leads: {stats['total_leads']}")
    logger.info(f"✅ Stages: {stats['stages']}")
    logger.info(f"✅ Sources: {stats['sources']}")
    logger.info(f"✅ Tags: {stats['tags']}")
    
    # Test CSV export
    logger.info("Testing CSV export...")
    csv_data = crm.export_leads("csv")
    logger.info(f"✅ CSV export: {len(csv_data)} characters")
    
    logger.info("🎉 All enhanced CRM service tests completed!")