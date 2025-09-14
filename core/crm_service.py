#!/usr/bin/env python3
"""
Fikiri Solutions - CRM Service
Lead management and CRM functionality.
"""

import json
import csv
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict
from datetime import datetime
import uuid

@dataclass
class Lead:
    """Lead data structure."""
    id: str
    name: str
    email: str
    phone: Optional[str] = None
    company: Optional[str] = None
    stage: str = "new"
    score: float = 0.0
    source: str = "unknown"
    created_at: str = ""
    updated_at: str = ""
    notes: str = ""
    
    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
        if not self.updated_at:
            self.updated_at = datetime.now().isoformat()

class CRMService:
    """CRM service for lead management."""
    
    def __init__(self, data_file: str = "data/leads.json"):
        """Initialize CRM service."""
        self.data_file = Path(data_file)
        self.leads: Dict[str, Lead] = {}
        self.logger = logging.getLogger(__name__)
        self._load_leads()
    
    def _load_leads(self) -> None:
        """Load leads from data file."""
        try:
            if self.data_file.exists():
                with open(self.data_file, 'r') as f:
                    data = json.load(f)
                    for lead_data in data:
                        if isinstance(lead_data, dict):
                            lead = Lead(**lead_data)
                            self.leads[lead.id] = lead
                        else:
                            self.logger.warning(f"⚠️ Skipping invalid lead data: {lead_data}")
                self.logger.info(f"📁 Loaded {len(self.leads)} leads from {self.data_file}")
            else:
                self.logger.info("📁 No existing leads file found, starting fresh")
        except Exception as e:
            self.logger.error(f"❌ Failed to load leads: {e}")
    
    def _save_leads(self) -> bool:
        """Save leads to data file."""
        try:
            self.data_file.parent.mkdir(parents=True, exist_ok=True)
            data = [asdict(lead) for lead in self.leads.values()]
            with open(self.data_file, 'w') as f:
                json.dump(data, f, indent=2)
            return True
        except Exception as e:
            self.logger.error(f"❌ Failed to save leads: {e}")
            return False
    
    def add_lead(self, lead_data: Dict[str, Any]) -> Optional[Lead]:
        """Add a new lead."""
        try:
            # Generate unique ID
            lead_id = str(uuid.uuid4())
            
            # Create lead object
            lead = Lead(
                id=lead_id,
                name=lead_data.get('name', ''),
                email=lead_data.get('email', ''),
                phone=lead_data.get('phone'),
                company=lead_data.get('company'),
                stage=lead_data.get('stage', 'new'),
                score=self._calculate_score(lead_data),
                source=lead_data.get('source', 'unknown'),
                notes=lead_data.get('notes', '')
            )
            
            # Check for duplicates by email
            existing_lead = self._find_by_email(lead.email)
            if existing_lead:
                self.logger.warning(f"⚠️ Lead with email {lead.email} already exists")
                return existing_lead
            
            # Add to leads
            self.leads[lead.id] = lead
            
            # Save to file
            if self._save_leads():
                self.logger.info(f"✅ Added lead: {lead.name} ({lead.email})")
                return lead
            else:
                # Remove from memory if save failed
                del self.leads[lead.id]
                return None
                
        except Exception as e:
            self.logger.error(f"❌ Failed to add lead: {e}")
            return None
    
    def ingest(self, leads_data: List[Dict[str, Any]]) -> List[Lead]:
        """Ingest multiple leads."""
        added_leads = []
        
        for lead_data in leads_data:
            lead = self.add_lead(lead_data)
            if lead:
                added_leads.append(lead)
        
        self.logger.info(f"📊 Ingested {len(added_leads)}/{len(leads_data)} leads")
        return added_leads
    
    def list(self, stage_filter: Optional[str] = None) -> List[Lead]:
        """List all leads, optionally filtered by stage."""
        leads = list(self.leads.values())
        
        if stage_filter:
            leads = [lead for lead in leads if lead.stage == stage_filter]
        
        # Sort by created date (newest first)
        leads.sort(key=lambda x: x.created_at, reverse=True)
        return leads
    
    def get_lead(self, lead_id: str) -> Optional[Lead]:
        """Get a specific lead by ID."""
        return self.leads.get(lead_id)
    
    def update_lead(self, lead_id: str, updates: Dict[str, Any]) -> Optional[Lead]:
        """Update a lead."""
        lead = self.leads.get(lead_id)
        if not lead:
            return None
        
        try:
            # Update fields
            for key, value in updates.items():
                if hasattr(lead, key):
                    setattr(lead, key, value)
            
            # Update timestamp
            lead.updated_at = datetime.now().isoformat()
            
            # Recalculate score if relevant fields changed
            if any(key in updates for key in ['name', 'email', 'company', 'notes']):
                lead.score = self._calculate_score(asdict(lead))
            
            # Save to file
            if self._save_leads():
                self.logger.info(f"✅ Updated lead: {lead.name}")
                return lead
            else:
                return None
                
        except Exception as e:
            self.logger.error(f"❌ Failed to update lead: {e}")
            return None
    
    def set_stage(self, lead_id: str, stage: str) -> Optional[Lead]:
        """Update lead stage."""
        return self.update_lead(lead_id, {'stage': stage})
    
    def delete_lead(self, lead_id: str) -> bool:
        """Delete a lead."""
        if lead_id not in self.leads:
            return False
        
        try:
            lead_name = self.leads[lead_id].name
            del self.leads[lead_id]
            
            if self._save_leads():
                self.logger.info(f"🗑️ Deleted lead: {lead_name}")
                return True
            else:
                # Restore if save failed
                self.leads[lead_id] = Lead(id=lead_id, name=lead_name, email="")
                return False
                
        except Exception as e:
            self.logger.error(f"❌ Failed to delete lead: {e}")
            return False
    
    def _find_by_email(self, email: str) -> Optional[Lead]:
        """Find lead by email address."""
        for lead in self.leads.values():
            if lead.email.lower() == email.lower():
                return lead
        return None
    
    def _calculate_score(self, lead_data: Dict[str, Any]) -> float:
        """Calculate lead score based on available data."""
        score = 0.0
        
        # Basic scoring criteria
        if lead_data.get('name'):
            score += 1.0
        if lead_data.get('email'):
            score += 2.0
        if lead_data.get('phone'):
            score += 1.5
        if lead_data.get('company'):
            score += 1.0
        
        # Keyword-based scoring
        text_fields = [
            lead_data.get('name', ''),
            lead_data.get('company', ''),
            lead_data.get('notes', '')
        ]
        
        text = ' '.join(text_fields).lower()
        
        # High-value keywords
        high_value_keywords = ['urgent', 'immediately', 'asap', 'budget', 'decision', 'ceo', 'manager']
        for keyword in high_value_keywords:
            if keyword in text:
                score += 2.0
        
        # Business keywords
        business_keywords = ['business', 'company', 'enterprise', 'corporate', 'professional']
        for keyword in business_keywords:
            if keyword in text:
                score += 1.0
        
        # Cap at 10.0
        return min(score, 10.0)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get CRM statistics."""
        total_leads = len(self.leads)
        
        stage_counts = {}
        for lead in self.leads.values():
            stage_counts[lead.stage] = stage_counts.get(lead.stage, 0) + 1
        
        avg_score = sum(lead.score for lead in self.leads.values()) / total_leads if total_leads > 0 else 0
        
        return {
            'total_leads': total_leads,
            'stage_counts': stage_counts,
            'average_score': round(avg_score, 2),
            'high_value_leads': len([lead for lead in self.leads.values() if lead.score >= 7.0])
        }
    
    def export_csv(self, output_file: str) -> bool:
        """Export leads to CSV file."""
        try:
            with open(output_file, 'w', newline='') as f:
                if not self.leads:
                    return True
                
                writer = csv.DictWriter(f, fieldnames=asdict(list(self.leads.values())[0]).keys())
                writer.writeheader()
                
                for lead in self.leads.values():
                    writer.writerow(asdict(lead))
            
            self.logger.info(f"📊 Exported {len(self.leads)} leads to {output_file}")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Failed to export CSV: {e}")
            return False
