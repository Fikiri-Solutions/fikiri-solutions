"""
Google Sheets Connector for Fikiri Solutions
Handles Google Sheets integration for lead logging and CRM data sync
"""

import json
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from datetime import datetime
import requests
from core.minimal_config import get_config

logger = logging.getLogger(__name__)

@dataclass
class SheetsConfig:
    """Google Sheets configuration"""
    spreadsheet_id: str
    worksheet_name: str
    credentials_path: str
    token_path: str

class GoogleSheetsConnector:
    """Google Sheets integration for CRM data sync"""
    
    def __init__(self, config: SheetsConfig):
        self.config = config
        self.service = None
        self.authenticated = False
        self._authenticate()
    
    def _authenticate(self) -> bool:
        """Authenticate with Google Sheets API"""
        try:
            from google.auth.transport.requests import Request
            from google.oauth2.credentials import Credentials
            from google_auth_oauthlib.flow import InstalledAppFlow
            from googleapiclient.discovery import build
            
            SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
            
            creds = None
            
            # Load existing token
            if os.path.exists(self.config.token_path):
                with open(self.config.token_path, 'rb') as token:
                    creds = pickle.load(token)
            
            # If no valid credentials, authenticate
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                else:
                    flow = InstalledAppFlow.from_client_secrets_file(
                        self.config.credentials_path, SCOPES
                    )
                    creds = flow.run_local_server(port=0)
                
                # Save credentials
                with open(self.config.token_path, 'wb') as token:
                    pickle.pickle(creds, token)
            
            # Build service
            self.service = build('sheets', 'v4', credentials=creds)
            self.authenticated = True
            logger.info("✅ Google Sheets service authenticated")
            return True
            
        except Exception as e:
            logger.error(f"❌ Google Sheets authentication failed: {e}")
            return False
    
    def create_lead_sheet(self, sheet_name: str = "Leads") -> Dict[str, Any]:
        """Create a new worksheet for leads if it doesn't exist"""
        try:
            if not self.authenticated:
                return {"success": False, "error": "Not authenticated"}
            
            # Check if sheet exists
            spreadsheet = self.service.spreadsheets().get(
                spreadsheetId=self.config.spreadsheet_id
            ).execute()
            
            sheet_exists = any(
                sheet['properties']['title'] == sheet_name 
                for sheet in spreadsheet['sheets']
            )
            
            if not sheet_exists:
                # Create new sheet
                request_body = {
                    'requests': [{
                        'addSheet': {
                            'properties': {
                                'title': sheet_name
                            }
                        }
                    }]
                }
                
                self.service.spreadsheets().batchUpdate(
                    spreadsheetId=self.config.spreadsheet_id,
                    body=request_body
                ).execute()
                
                # Add headers
                headers = [
                    'ID', 'Name', 'Email', 'Phone', 'Company', 'Source', 
                    'Status', 'Score', 'Created At', 'Last Contact', 'Notes', 'Tags'
                ]
                
                self.service.spreadsheets().values().update(
                    spreadsheetId=self.config.spreadsheet_id,
                    range=f"{sheet_name}!A1:L1",
                    valueInputOption='RAW',
                    body={'values': [headers]}
                ).execute()
                
                logger.info(f"✅ Created new sheet: {sheet_name}")
            
            return {"success": True, "sheet_name": sheet_name}
            
        except Exception as e:
            logger.error(f"❌ Failed to create lead sheet: {e}")
            return {"success": False, "error": str(e)}
    
    def add_lead(self, lead_data: Dict[str, Any]) -> Dict[str, Any]:
        """Add a new lead to the Google Sheet"""
        try:
            if not self.authenticated:
                return {"success": False, "error": "Not authenticated"}
            
            # Prepare lead data for sheet
            row_data = [
                lead_data.get('id', ''),
                lead_data.get('name', ''),
                lead_data.get('email', ''),
                lead_data.get('phone', ''),
                lead_data.get('company', ''),
                lead_data.get('source', ''),
                lead_data.get('status', 'new'),
                lead_data.get('score', 0),
                lead_data.get('created_at', datetime.now().isoformat()),
                lead_data.get('last_contact', ''),
                lead_data.get('notes', ''),
                ', '.join(lead_data.get('tags', []))
            ]
            
            # Append to sheet
            self.service.spreadsheets().values().append(
                spreadsheetId=self.config.spreadsheet_id,
                range=f"{self.config.worksheet_name}!A:L",
                valueInputOption='RAW',
                insertDataOption='INSERT_ROWS',
                body={'values': [row_data]}
            ).execute()
            
            logger.info(f"✅ Added lead to Google Sheets: {lead_data.get('email')}")
            return {"success": True, "lead_id": lead_data.get('id')}
            
        except Exception as e:
            logger.error(f"❌ Failed to add lead to Google Sheets: {e}")
            return {"success": False, "error": str(e)}
    
    def update_lead(self, lead_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Update an existing lead in the Google Sheet"""
        try:
            if not self.authenticated:
                return {"success": False, "error": "Not authenticated"}
            
            # Find the row with the lead ID
            result = self.service.spreadsheets().values().get(
                spreadsheetId=self.config.spreadsheet_id,
                range=f"{self.config.worksheet_name}!A:L"
            ).execute()
            
            values = result.get('values', [])
            if not values:
                return {"success": False, "error": "No data found"}
            
            # Find the row with matching ID
            row_index = None
            for i, row in enumerate(values[1:], start=2):  # Skip header row
                if row and row[0] == lead_id:
                    row_index = i
                    break
            
            if not row_index:
                return {"success": False, "error": "Lead not found"}
            
            # Update specific cells based on updates
            update_requests = []
            headers = values[0] if values else []
            
            for field, value in updates.items():
                if field in headers:
                    col_index = headers.index(field)
                    col_letter = chr(ord('A') + col_index)
                    
                    update_requests.append({
                        'range': f"{self.config.worksheet_name}!{col_letter}{row_index}",
                        'values': [[str(value)]]
                    })
            
            if update_requests:
                self.service.spreadsheets().values().batchUpdate(
                    spreadsheetId=self.config.spreadsheet_id,
                    body={'valueInputOption': 'RAW', 'data': update_requests}
                ).execute()
            
            logger.info(f"✅ Updated lead in Google Sheets: {lead_id}")
            return {"success": True, "lead_id": lead_id}
            
        except Exception as e:
            logger.error(f"❌ Failed to update lead in Google Sheets: {e}")
            return {"success": False, "error": str(e)}
    
    def get_leads(self) -> Dict[str, Any]:
        """Get all leads from the Google Sheet"""
        try:
            if not self.authenticated:
                return {"success": False, "error": "Not authenticated"}
            
            result = self.service.spreadsheets().values().get(
                spreadsheetId=self.config.spreadsheet_id,
                range=f"{self.config.worksheet_name}!A:L"
            ).execute()
            
            values = result.get('values', [])
            if not values:
                return {"success": True, "leads": []}
            
            headers = values[0]
            leads = []
            
            for row in values[1:]:  # Skip header row
                if len(row) >= len(headers):
                    lead = {}
                    for i, header in enumerate(headers):
                        lead[header.lower().replace(' ', '_')] = row[i] if i < len(row) else ''
                    leads.append(lead)
            
            return {"success": True, "leads": leads}
            
        except Exception as e:
            logger.error(f"❌ Failed to get leads from Google Sheets: {e}")
            return {"success": False, "error": str(e)}

# Global instance
sheets_connector = None

def get_sheets_connector() -> Optional[GoogleSheetsConnector]:
    """Get the global Google Sheets connector instance"""
    global sheets_connector
    
    if sheets_connector is None:
        config = get_config()
        sheets_config = SheetsConfig(
            spreadsheet_id=getattr(config, 'google_sheets_id', ''),
            worksheet_name=getattr(config, 'google_sheets_worksheet', 'Leads'),
            credentials_path=getattr(config, 'google_credentials_path', 'auth/credentials.json'),
            token_path=getattr(config, 'google_token_path', 'auth/sheets_token.pkl')
        )
        
        if sheets_config.spreadsheet_id:
            sheets_connector = GoogleSheetsConnector(sheets_config)
        else:
            logger.warning("⚠️ Google Sheets not configured - skipping integration")
    
    return sheets_connector
