"""
Notion Connector for Fikiri Solutions
Handles Notion integration for customer profiles and CRM data sync
"""

import json
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from datetime import datetime

# Optional dependencies
try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    requests = None

try:
    from core.minimal_config import get_config
    CONFIG_AVAILABLE = True
except ImportError:
    CONFIG_AVAILABLE = False
    get_config = None

logger = logging.getLogger(__name__)

@dataclass
class NotionConfig:
    """Notion configuration"""
    api_key: str
    database_id: str
    page_id: Optional[str] = None

class NotionConnector:
    """Notion integration for CRM data sync"""
    
    def __init__(self, config: NotionConfig):
        self.config = config
        self.base_url = "https://api.notion.com/v1"
        self.headers = {
            "Authorization": f"Bearer {config.api_key}",
            "Content-Type": "application/json",
            "Notion-Version": "2022-06-28"
        }
        self.authenticated = False
        self._authenticate()
    
    def _authenticate(self) -> bool:
        """Test Notion API authentication"""
        try:
            response = requests.get(
                f"{self.base_url}/users/me",
                headers=self.headers
            )
            
            if response.status_code == 200:
                self.authenticated = True
                logger.info("✅ Notion API authenticated successfully")
                return True
            else:
                logger.error(f"❌ Notion authentication failed: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Notion authentication error: {e}")
            return False
    
    def create_customer_profile(self, lead_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new customer profile page in Notion"""
        try:
            if not self.authenticated:
                return {"success": False, "error": "Not authenticated"}
            
            # Prepare page properties for Notion
            properties = {
                "Name": {
                    "title": [
                        {
                            "text": {
                                "content": lead_data.get('name', 'Unknown')
                            }
                        }
                    ]
                },
                "Email": {
                    "email": lead_data.get('email', '')
                },
                "Phone": {
                    "phone_number": lead_data.get('phone', '')
                },
                "Company": {
                    "rich_text": [
                        {
                            "text": {
                                "content": lead_data.get('company', '')
                            }
                        }
                    ]
                },
                "Source": {
                    "select": {
                        "name": lead_data.get('source', 'web')
                    }
                },
                "Status": {
                    "select": {
                        "name": lead_data.get('status', 'new')
                    }
                },
                "Score": {
                    "number": lead_data.get('score', 0)
                },
                "Created": {
                    "date": {
                        "start": lead_data.get('created_at', datetime.now().isoformat())
                    }
                }
            }
            
            # Add notes if available
            if lead_data.get('notes'):
                properties["Notes"] = {
                    "rich_text": [
                        {
                            "text": {
                                "content": lead_data.get('notes', '')
                            }
                        }
                    ]
                }
            
            # Add tags if available
            if lead_data.get('tags'):
                properties["Tags"] = {
                    "multi_select": [
                        {"name": tag} for tag in lead_data.get('tags', [])
                    ]
                }
            
            # Create the page
            page_data = {
                "parent": {
                    "database_id": self.config.database_id
                },
                "properties": properties
            }
            
            response = requests.post(
                f"{self.base_url}/pages",
                headers=self.headers,
                json=page_data
            )
            
            if response.status_code == 200:
                page_info = response.json()
                logger.info(f"✅ Created Notion customer profile: {lead_data.get('email')}")
                return {
                    "success": True, 
                    "page_id": page_info.get('id'),
                    "url": page_info.get('url')
                }
            else:
                logger.error(f"❌ Failed to create Notion page: {response.status_code}")
                return {"success": False, "error": f"HTTP {response.status_code}"}
                
        except Exception as e:
            logger.error(f"❌ Failed to create Notion customer profile: {e}")
            return {"success": False, "error": str(e)}
    
    def update_customer_profile(self, page_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Update an existing customer profile in Notion"""
        try:
            if not self.authenticated:
                return {"success": False, "error": "Not authenticated"}
            
            # Prepare update properties
            properties = {}
            
            for field, value in updates.items():
                if field == 'name':
                    properties["Name"] = {
                        "title": [{"text": {"content": str(value)}}]
                    }
                elif field == 'email':
                    properties["Email"] = {"email": str(value)}
                elif field == 'phone':
                    properties["Phone"] = {"phone_number": str(value)}
                elif field == 'company':
                    properties["Company"] = {
                        "rich_text": [{"text": {"content": str(value)}}]
                    }
                elif field == 'source':
                    properties["Source"] = {"select": {"name": str(value)}}
                elif field == 'status':
                    properties["Status"] = {"select": {"name": str(value)}}
                elif field == 'score':
                    properties["Score"] = {"number": int(value)}
                elif field == 'notes':
                    properties["Notes"] = {
                        "rich_text": [{"text": {"content": str(value)}}]
                    }
                elif field == 'tags':
                    properties["Tags"] = {
                        "multi_select": [{"name": tag} for tag in value]
                    }
            
            if not properties:
                return {"success": False, "error": "No valid properties to update"}
            
            # Update the page
            update_data = {"properties": properties}
            
            response = requests.patch(
                f"{self.base_url}/pages/{page_id}",
                headers=self.headers,
                json=update_data
            )
            
            if response.status_code == 200:
                logger.info(f"✅ Updated Notion customer profile: {page_id}")
                return {"success": True, "page_id": page_id}
            else:
                logger.error(f"❌ Failed to update Notion page: {response.status_code}")
                return {"success": False, "error": f"HTTP {response.status_code}"}
                
        except Exception as e:
            logger.error(f"❌ Failed to update Notion customer profile: {e}")
            return {"success": False, "error": str(e)}
    
    def get_customer_profiles(self) -> Dict[str, Any]:
        """Get all customer profiles from Notion database"""
        try:
            if not self.authenticated:
                return {"success": False, "error": "Not authenticated"}
            
            # Query the database
            query_data = {
                "page_size": 100
            }
            
            response = requests.post(
                f"{self.base_url}/databases/{self.config.database_id}/query",
                headers=self.headers,
                json=query_data
            )
            
            if response.status_code == 200:
                data = response.json()
                profiles = []
                
                for page in data.get('results', []):
                    properties = page.get('properties', {})
                    
                    profile = {
                        'id': page.get('id'),
                        'url': page.get('url'),
                        'name': self._extract_title(properties.get('Name', {})),
                        'email': self._extract_email(properties.get('Email', {})),
                        'phone': self._extract_phone(properties.get('Phone', {})),
                        'company': self._extract_rich_text(properties.get('Company', {})),
                        'source': self._extract_select(properties.get('Source', {})),
                        'status': self._extract_select(properties.get('Status', {})),
                        'score': self._extract_number(properties.get('Score', {})),
                        'notes': self._extract_rich_text(properties.get('Notes', {})),
                        'tags': self._extract_multi_select(properties.get('Tags', {}))
                    }
                    profiles.append(profile)
                
                logger.info(f"✅ Retrieved {len(profiles)} customer profiles from Notion")
                return {"success": True, "profiles": profiles}
            else:
                logger.error(f"❌ Failed to query Notion database: {response.status_code}")
                return {"success": False, "error": f"HTTP {response.status_code}"}
                
        except Exception as e:
            logger.error(f"❌ Failed to get customer profiles from Notion: {e}")
            return {"success": False, "error": str(e)}
    
    def _extract_title(self, prop: Dict[str, Any]) -> str:
        """Extract title from Notion property"""
        if 'title' in prop and prop['title']:
            return prop['title'][0].get('text', {}).get('content', '')
        return ''
    
    def _extract_email(self, prop: Dict[str, Any]) -> str:
        """Extract email from Notion property"""
        return prop.get('email', '')
    
    def _extract_phone(self, prop: Dict[str, Any]) -> str:
        """Extract phone from Notion property"""
        return prop.get('phone_number', '')
    
    def _extract_rich_text(self, prop: Dict[str, Any]) -> str:
        """Extract rich text from Notion property"""
        if 'rich_text' in prop and prop['rich_text']:
            return prop['rich_text'][0].get('text', {}).get('content', '')
        return ''
    
    def _extract_select(self, prop: Dict[str, Any]) -> str:
        """Extract select value from Notion property"""
        if 'select' in prop and prop['select']:
            return prop['select'].get('name', '')
        return ''
    
    def _extract_number(self, prop: Dict[str, Any]) -> int:
        """Extract number from Notion property"""
        return prop.get('number', 0)
    
    def _extract_multi_select(self, prop: Dict[str, Any]) -> List[str]:
        """Extract multi-select values from Notion property"""
        if 'multi_select' in prop and prop['multi_select']:
            return [item.get('name', '') for item in prop['multi_select']]
        return []

# Global instance
notion_connector = None

def get_notion_connector() -> Optional[NotionConnector]:
    """Get the global Notion connector instance"""
    global notion_connector
    
    if notion_connector is None:
        config = get_config()
        notion_config = NotionConfig(
            api_key=getattr(config, 'notion_api_key', ''),
            database_id=getattr(config, 'notion_database_id', ''),
            page_id=getattr(config, 'notion_page_id', None)
        )
        
        if notion_config.api_key and notion_config.database_id:
            notion_connector = NotionConnector(notion_config)
        else:
            logger.warning("⚠️ Notion not configured - skipping integration")
    
    return notion_connector
