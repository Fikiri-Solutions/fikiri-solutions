#!/usr/bin/env python3
"""
Tenant Management System
Multi-tenant architecture with tenant isolation and company management
"""

import os
import json
import time
import secrets
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

from core.database_optimization import db_optimizer

logger = logging.getLogger(__name__)

@dataclass
class Company:
    """Company/tenant data structure"""
    id: int
    name: str
    domain: Optional[str]
    industry: Optional[str]
    team_size: Optional[str]
    tenant_id: str
    created_at: datetime
    is_active: bool
    metadata: Dict[str, Any]

@dataclass
class User:
    """User data structure with tenant association"""
    id: int
    email: str
    name: str
    role: str
    company_id: int
    tenant_id: str
    is_active: bool
    created_at: datetime
    metadata: Dict[str, Any]

class TenantManager:
    """Multi-tenant management system with isolation"""
    
    def __init__(self):
        self._initialize_tables()
    
    def _initialize_tables(self):
        """Initialize database tables for tenant management"""
        try:
            # Create companies table
            db_optimizer.execute_query("""
                CREATE TABLE IF NOT EXISTS companies (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    domain TEXT,
                    industry TEXT,
                    team_size TEXT,
                    tenant_id TEXT NOT NULL UNIQUE,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    is_active BOOLEAN DEFAULT TRUE,
                    metadata TEXT DEFAULT '{}',
                    settings TEXT DEFAULT '{}'
                )
            """, fetch=False)
            
            # Create tenant isolation index
            db_optimizer.execute_query("""
                CREATE INDEX IF NOT EXISTS idx_companies_tenant_id 
                ON companies (tenant_id)
            """, fetch=False)
            
            # Update users table to include tenant_id and company_id
            try:
                db_optimizer.execute_query("""
                    ALTER TABLE users ADD COLUMN tenant_id TEXT
                """, fetch=False)
            except:
                pass  # Column might already exist
            
            try:
                db_optimizer.execute_query("""
                    ALTER TABLE users ADD COLUMN company_id INTEGER
                """, fetch=False)
            except:
                pass  # Column might already exist
            
            # Create tenant isolation index for users
            db_optimizer.execute_query("""
                CREATE INDEX IF NOT EXISTS idx_users_tenant_id 
                ON users (tenant_id)
            """, fetch=False)
            
            # Create tenant isolation index for users by company
            db_optimizer.execute_query("""
                CREATE INDEX IF NOT EXISTS idx_users_company_id 
                ON users (company_id)
            """, fetch=False)
            
            logger.info("✅ Tenant management tables initialized")
            
        except Exception as e:
            logger.error(f"❌ Tenant table initialization failed: {e}")
    
    def create_company(self, name: str, domain: str = None, industry: str = None, 
                      team_size: str = None, settings: Dict[str, Any] = None) -> Dict[str, Any]:
        """Create a new company/tenant"""
        try:
            # Generate unique tenant ID
            tenant_id = self._generate_tenant_id()
            
            # Create company record
            company_id = db_optimizer.execute_query("""
                INSERT INTO companies 
                (name, domain, industry, team_size, tenant_id, settings)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                name,
                domain,
                industry,
                team_size,
                tenant_id,
                json.dumps(settings or {})
            ), fetch=False)
            
            # Get the created company
            company_data = db_optimizer.execute_query("""
                SELECT * FROM companies WHERE id = ?
            """, (company_id,))
            
            if company_data:
                company = company_data[0]
                logger.info(f"✅ Created company: {name} (tenant: {tenant_id})")
                
                return {
                    'success': True,
                    'company': {
                        'id': company['id'],
                        'name': company['name'],
                        'domain': company['domain'],
                        'industry': company['industry'],
                        'team_size': company['team_size'],
                        'tenant_id': company['tenant_id'],
                        'created_at': company['created_at'],
                        'is_active': company['is_active'],
                        'settings': json.loads(company.get('settings', '{}'))
                    }
                }
            
            return {
                'success': False,
                'error': 'Failed to create company',
                'error_code': 'COMPANY_CREATION_FAILED'
            }
            
        except Exception as e:
            logger.error(f"❌ Company creation failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'error_code': 'COMPANY_CREATION_ERROR'
            }
    
    def create_user_with_tenant(self, email: str, name: str, password_hash: str, 
                               company_id: int, role: str = 'user', 
                               metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """Create a user associated with a company/tenant"""
        try:
            # Get company tenant_id
            company_data = db_optimizer.execute_query("""
                SELECT tenant_id FROM companies WHERE id = ? AND is_active = TRUE
            """, (company_id,))
            
            if not company_data:
                return {
                    'success': False,
                    'error': 'Company not found',
                    'error_code': 'COMPANY_NOT_FOUND'
                }
            
            tenant_id = company_data[0]['tenant_id']
            
            # Create user with tenant association
            user_id = db_optimizer.execute_query("""
                INSERT INTO users 
                (email, name, password_hash, company_id, tenant_id, role, metadata, is_active)
                VALUES (?, ?, ?, ?, ?, ?, ?, TRUE)
            """, (
                email,
                name,
                password_hash,
                company_id,
                tenant_id,
                role,
                json.dumps(metadata or {})
            ), fetch=False)
            
            # Get the created user
            user_data = db_optimizer.execute_query("""
                SELECT * FROM users WHERE id = ?
            """, (user_id,))
            
            if user_data:
                user = user_data[0]
                logger.info(f"✅ Created user: {email} (tenant: {tenant_id})")
                
                return {
                    'success': True,
                    'user': {
                        'id': user['id'],
                        'email': user['email'],
                        'name': user['name'],
                        'role': user['role'],
                        'company_id': user['company_id'],
                        'tenant_id': user['tenant_id'],
                        'is_active': user['is_active'],
                        'created_at': user['created_at'],
                        'metadata': json.loads(user.get('metadata', '{}'))
                    }
                }
            
            return {
                'success': False,
                'error': 'Failed to create user',
                'error_code': 'USER_CREATION_FAILED'
            }
            
        except Exception as e:
            logger.error(f"❌ User creation with tenant failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'error_code': 'USER_CREATION_ERROR'
            }
    
    def get_company_by_tenant_id(self, tenant_id: str) -> Optional[Dict[str, Any]]:
        """Get company by tenant ID"""
        try:
            company_data = db_optimizer.execute_query("""
                SELECT * FROM companies WHERE tenant_id = ? AND is_active = TRUE
            """, (tenant_id,))
            
            if company_data:
                company = company_data[0]
                return {
                    'id': company['id'],
                    'name': company['name'],
                    'domain': company['domain'],
                    'industry': company['industry'],
                    'team_size': company['team_size'],
                    'tenant_id': company['tenant_id'],
                    'created_at': company['created_at'],
                    'is_active': company['is_active'],
                    'settings': json.loads(company.get('settings', '{}'))
                }
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Company retrieval failed: {e}")
            return None
    
    def get_users_by_tenant(self, tenant_id: str) -> List[Dict[str, Any]]:
        """Get all users for a tenant"""
        try:
            users_data = db_optimizer.execute_query("""
                SELECT * FROM users WHERE tenant_id = ? AND is_active = TRUE
            """, (tenant_id,))
            
            users = []
            for user in users_data:
                users.append({
                    'id': user['id'],
                    'email': user['email'],
                    'name': user['name'],
                    'role': user['role'],
                    'company_id': user['company_id'],
                    'tenant_id': user['tenant_id'],
                    'is_active': user['is_active'],
                    'created_at': user['created_at'],
                    'metadata': json.loads(user.get('metadata', '{}'))
                })
            
            return users
            
        except Exception as e:
            logger.error(f"❌ Users retrieval failed: {e}")
            return []
    
    def get_user_tenant(self, user_id: int) -> Optional[str]:
        """Get tenant ID for a user"""
        try:
            user_data = db_optimizer.execute_query("""
                SELECT tenant_id FROM users WHERE id = ? AND is_active = TRUE
            """, (user_id,))
            
            if user_data:
                return user_data[0]['tenant_id']
            
            return None
            
        except Exception as e:
            logger.error(f"❌ User tenant retrieval failed: {e}")
            return None
    
    def update_company(self, company_id: int, updates: Dict[str, Any]) -> bool:
        """Update company information"""
        try:
            # Build update query dynamically
            update_fields = []
            update_values = []
            
            for field, value in updates.items():
                if field in ['name', 'domain', 'industry', 'team_size']:
                    update_fields.append(f"{field} = ?")
                    update_values.append(value)
                elif field == 'settings':
                    update_fields.append(f"{field} = ?")
                    update_values.append(json.dumps(value))
            
            if not update_fields:
                return False
            
            update_values.append(company_id)
            
            query = f"""
                UPDATE companies 
                SET {', '.join(update_fields)}
                WHERE id = ?
            """
            
            db_optimizer.execute_query(query, tuple(update_values), fetch=False)
            
            logger.info(f"✅ Updated company {company_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Company update failed: {e}")
            return False
    
    def deactivate_company(self, company_id: int) -> bool:
        """Deactivate a company and all its users"""
        try:
            # Get tenant_id
            company_data = db_optimizer.execute_query("""
                SELECT tenant_id FROM companies WHERE id = ?
            """, (company_id,))
            
            if not company_data:
                return False
            
            tenant_id = company_data[0]['tenant_id']
            
            # Deactivate company
            db_optimizer.execute_query("""
                UPDATE companies SET is_active = FALSE WHERE id = ?
            """, (company_id,), fetch=False)
            
            # Deactivate all users in the tenant
            db_optimizer.execute_query("""
                UPDATE users SET is_active = FALSE WHERE tenant_id = ?
            """, (tenant_id,), fetch=False)
            
            logger.info(f"✅ Deactivated company {company_id} and all users")
            return True
            
        except Exception as e:
            logger.error(f"❌ Company deactivation failed: {e}")
            return False
    
    def get_tenant_stats(self, tenant_id: str) -> Dict[str, Any]:
        """Get statistics for a tenant"""
        try:
            # Get company info
            company = self.get_company_by_tenant_id(tenant_id)
            if not company:
                return {}
            
            # Get user count
            user_count = db_optimizer.execute_query("""
                SELECT COUNT(*) as count FROM users 
                WHERE tenant_id = ? AND is_active = TRUE
            """, (tenant_id,))
            
            # Get active sessions count (if using session management)
            # This would need to be implemented based on your session system
            
            return {
                'company': company,
                'user_count': user_count[0]['count'] if user_count else 0,
                'tenant_id': tenant_id
            }
            
        except Exception as e:
            logger.error(f"❌ Tenant stats failed: {e}")
            return {}
    
    def _generate_tenant_id(self) -> str:
        """Generate a unique tenant ID"""
        while True:
            # Generate a short, unique tenant ID
            tenant_id = secrets.token_urlsafe(8).lower()
            
            # Check if it already exists
            existing = db_optimizer.execute_query("""
                SELECT id FROM companies WHERE tenant_id = ?
            """, (tenant_id,))
            
            if not existing:
                return tenant_id
    
    def validate_tenant_access(self, user_id: int, resource_tenant_id: str) -> bool:
        """Validate that a user can access a resource from their tenant"""
        try:
            user_tenant_id = self.get_user_tenant(user_id)
            return user_tenant_id == resource_tenant_id
            
        except Exception as e:
            logger.error(f"❌ Tenant access validation failed: {e}")
            return False
    
    def get_tenant_scope_query(self, user_id: int, table_name: str, 
                              tenant_field: str = 'tenant_id') -> str:
        """Get a SQL query with tenant isolation"""
        try:
            user_tenant_id = self.get_user_tenant(user_id)
            if not user_tenant_id:
                return f"SELECT * FROM {table_name} WHERE 1=0"  # Return no results
            
            return f"SELECT * FROM {table_name} WHERE {tenant_field} = '{user_tenant_id}'"
            
        except Exception as e:
            logger.error(f"❌ Tenant scope query failed: {e}")
            return f"SELECT * FROM {table_name} WHERE 1=0"

# Global tenant manager
tenant_manager = TenantManager()
