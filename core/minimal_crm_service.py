#!/usr/bin/env python3
"""
Fikiri Solutions - Minimal CRM Service
Lightweight CRM functionality without heavy dependencies.
"""

import json
from typing import Dict, Any, List, Optional
from pathlib import Path
from datetime import datetime

class MinimalLead:
    """Minimal lead data structure."""
    
    def __init__(self, email: str, name: str = "", source: str = "email"):
        """Initialize a lead."""
        self.id = self._generate_id()
        self.email = email
        self.name = name
        self.source = source
        self.stage = "new"
        self.created_at = datetime.now().isoformat()
        self.updated_at = datetime.now().isoformat()
        self.tags = []
        self.notes = []
        self.last_contact = None
        self.contact_count = 0
    
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
            "contact_count": self.contact_count
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MinimalLead':
        """Create lead from dictionary."""
        lead = cls(data["email"], data.get("name", ""), data.get("source", "email"))
        lead.id = data["id"]
        lead.stage = data.get("stage", "new")
        lead.created_at = data.get("created_at", datetime.now().isoformat())
        lead.updated_at = data.get("updated_at", datetime.now().isoformat())
        lead.tags = data.get("tags", [])
        lead.notes = data.get("notes", [])
        lead.last_contact = data.get("last_contact")
        lead.contact_count = data.get("contact_count", 0)
        return lead

class MinimalCRMService:
    """Minimal CRM service - lightweight version."""
    
    def __init__(self, data_path: str = "data/leads.json"):
        """Initialize minimal CRM service."""
        self.data_path = Path(data_path)
        self.leads: List[MinimalLead] = []
        self.load_leads()
    
    def load_leads(self) -> bool:
        """Load leads from file."""
        try:
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
                print(f"✅ Loaded {len(self.leads)} leads from {self.data_path}")
                return True
            else:
                print(f"📝 No leads file found at {self.data_path}")
                return True
        except Exception as e:
            print(f"❌ Error loading leads: {e}")
            return False
    
    def save_leads(self) -> bool:
        """Save leads to file."""
        try:
            # Ensure data directory exists
            self.data_path.parent.mkdir(exist_ok=True)
            
            # Convert leads to dictionaries
            leads_data = [lead.to_dict() for lead in self.leads]
            
            with open(self.data_path, 'w') as f:
                json.dump(leads_data, f, indent=2)
            
            print(f"✅ Saved {len(self.leads)} leads to {self.data_path}")
            return True
        except Exception as e:
            print(f"❌ Error saving leads: {e}")
            return False
    
    def add_lead(self, email: str, name: str = "", source: str = "email") -> MinimalLead:
        """Add a new lead."""
        # Check if lead already exists
        existing_lead = self.find_lead_by_email(email)
        if existing_lead:
            print(f"⚠️  Lead with email {email} already exists")
            return existing_lead
        
        # Create new lead
        lead = MinimalLead(email, name, source)
        self.leads.append(lead)
        
        print(f"✅ Added new lead: {email}")
        return lead
    
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
            print(f"❌ Lead with ID {lead_id} not found")
            return False
        
        old_stage = lead.stage
        lead.stage = new_stage
        lead.updated_at = datetime.now().isoformat()
        
        print(f"✅ Updated lead {lead.email} from {old_stage} to {new_stage}")
        return True
    
    def add_note(self, lead_id: str, note: str) -> bool:
        """Add note to lead."""
        lead = self.find_lead_by_id(lead_id)
        if not lead:
            print(f"❌ Lead with ID {lead_id} not found")
            return False
        
        timestamp = datetime.now().isoformat()
        lead.notes.append({
            "timestamp": timestamp,
            "note": note
        })
        lead.updated_at = timestamp
        
        print(f"✅ Added note to lead {lead.email}")
        return True
    
    def add_tag(self, lead_id: str, tag: str) -> bool:
        """Add tag to lead."""
        lead = self.find_lead_by_id(lead_id)
        if not lead:
            print(f"❌ Lead with ID {lead_id} not found")
            return False
        
        if tag not in lead.tags:
            lead.tags.append(tag)
            lead.updated_at = datetime.now().isoformat()
            print(f"✅ Added tag '{tag}' to lead {lead.email}")
        else:
            print(f"⚠️  Tag '{tag}' already exists for lead {lead.email}")
        
        return True
    
    def record_contact(self, lead_id: str, contact_type: str = "email") -> bool:
        """Record contact with lead."""
        lead = self.find_lead_by_id(lead_id)
        if not lead:
            print(f"❌ Lead with ID {lead_id} not found")
            return False
        
        lead.contact_count += 1
        lead.last_contact = datetime.now().isoformat()
        lead.updated_at = lead.last_contact
        
        print(f"✅ Recorded {contact_type} contact with lead {lead.email}")
        return True
    
    def get_leads_by_stage(self, stage: str) -> List[MinimalLead]:
        """Get leads by stage."""
        return [lead for lead in self.leads if lead.stage == stage]
    
    def get_leads_by_tag(self, tag: str) -> List[MinimalLead]:
        """Get leads by tag."""
        return [lead for lead in self.leads if tag in lead.tags]
    
    def get_all_leads(self) -> List[MinimalLead]:
        """Get all leads."""
        return self.leads.copy()
    
    def get_lead_stats(self) -> Dict[str, Any]:
        """Get CRM statistics."""
        if not self.leads:
            return {
                "total_leads": 0,
                "stages": {},
                "sources": {},
                "tags": {},
                "recent_leads": 0
            }
        
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
        week_ago = datetime.now().timestamp() - (7 * 24 * 60 * 60)
        for lead in self.leads:
            lead_time = datetime.fromisoformat(lead.created_at).timestamp()
            if lead_time > week_ago:
                recent_count += 1
        
        return {
            "total_leads": len(self.leads),
            "stages": stages,
            "sources": sources,
            "tags": tags,
            "recent_leads": recent_count
        }
    
    def export_leads(self, format: str = "json") -> str:
        """Export leads in specified format."""
        if format == "json":
            leads_data = [lead.to_dict() for lead in self.leads]
            return json.dumps(leads_data, indent=2)
        elif format == "csv":
            # Simple CSV export
            csv_lines = ["id,email,name,stage,source,created_at,contact_count"]
            for lead in self.leads:
                csv_lines.append(f"{lead.id},{lead.email},{lead.name},{lead.stage},{lead.source},{lead.created_at},{lead.contact_count}")
            return "\n".join(csv_lines)
        else:
            return "Unsupported format"

def create_crm_service(data_path: str = "data/leads.json") -> MinimalCRMService:
    """Create and return a CRM service instance."""
    return MinimalCRMService(data_path)

if __name__ == "__main__":
    # Test the CRM service
    print("🧪 Testing Minimal CRM Service")
    print("=" * 40)
    
    crm = MinimalCRMService("data/test_leads.json")
    
    # Test adding leads
    print("Testing add lead...")
    lead1 = crm.add_lead("john.doe@example.com", "John Doe", "email")
    lead2 = crm.add_lead("jane.smith@example.com", "Jane Smith", "website")
    
    print(f"✅ Added leads: {lead1.email}, {lead2.email}")
    
    # Test updating stage
    print("\nTesting stage update...")
    crm.update_lead_stage(lead1.id, "qualified")
    crm.update_lead_stage(lead2.id, "contacted")
    
    # Test adding notes and tags
    print("\nTesting notes and tags...")
    crm.add_note(lead1.id, "Interested in premium package")
    crm.add_tag(lead1.id, "premium")
    crm.add_tag(lead1.id, "hot")
    
    # Test recording contact
    print("\nTesting contact recording...")
    crm.record_contact(lead1.id, "email")
    crm.record_contact(lead2.id, "phone")
    
    # Test stats
    print("\nTesting stats...")
    stats = crm.get_lead_stats()
    print(f"✅ Total leads: {stats['total_leads']}")
    print(f"✅ Stages: {stats['stages']}")
    print(f"✅ Sources: {stats['sources']}")
    print(f"✅ Tags: {stats['tags']}")
    
    # Test saving
    print("\nTesting save...")
    crm.save_leads()
    
    print("\n🎉 All CRM service tests completed!")

