#!/usr/bin/env python3
"""
Fikiri Solutions - Enterprise Security System
Role-based access control and security features.
"""

import hashlib
import secrets
import time
from typing import Dict, List, Optional, Set, Any
from dataclasses import dataclass
from enum import Enum

class UserRole(Enum):
    """User roles with different permission levels."""
    ADMIN = "admin"
    MANAGER = "manager"
    USER = "user"
    VIEWER = "viewer"

class Permission(Enum):
    """System permissions."""
    READ_EMAILS = "read_emails"
    WRITE_EMAILS = "write_emails"
    MANAGE_CRM = "manage_crm"
    VIEW_ANALYTICS = "view_analytics"
    MANAGE_USERS = "manage_users"
    SYSTEM_CONFIG = "system_config"
    API_ACCESS = "api_access"

@dataclass
class User:
    """User model with role-based permissions."""
    id: str
    email: str
    name: str
    role: UserRole
    permissions: Set[Permission]
    created_at: float
    last_login: Optional[float] = None
    is_active: bool = True

@dataclass
class Session:
    """User session with security tokens."""
    session_id: str
    user_id: str
    created_at: float
    expires_at: float
    ip_address: str
    user_agent: str
    is_valid: bool = True

class SecurityManager:
    """Enterprise security and access control manager."""
    
    def __init__(self):
        """Initialize security manager."""
        self.users: Dict[str, User] = {}
        self.sessions: Dict[str, Session] = {}
        self.role_permissions: Dict[UserRole, Set[Permission]] = {
            UserRole.ADMIN: set(Permission),
            UserRole.MANAGER: {
                Permission.READ_EMAILS,
                Permission.WRITE_EMAILS,
                Permission.MANAGE_CRM,
                Permission.VIEW_ANALYTICS,
                Permission.API_ACCESS
            },
            UserRole.USER: {
                Permission.READ_EMAILS,
                Permission.WRITE_EMAILS,
                Permission.MANAGE_CRM,
                Permission.API_ACCESS
            },
            UserRole.VIEWER: {
                Permission.READ_EMAILS,
                Permission.VIEW_ANALYTICS
            }
        }
        
        # Initialize default admin user
        self._create_default_admin()
    
    def _create_default_admin(self):
        """Create default admin user."""
        admin_permissions = self.role_permissions[UserRole.ADMIN]
        admin_user = User(
            id="admin",
            email="admin@fikirisolutions.com",
            name="System Administrator",
            role=UserRole.ADMIN,
            permissions=admin_permissions,
            created_at=time.time()
        )
        self.users["admin"] = admin_user
    
    def create_user(self, email: str, name: str, role: UserRole) -> User:
        """Create a new user."""
        user_id = self._generate_user_id(email)
        permissions = self.role_permissions[role]
        
        user = User(
            id=user_id,
            email=email,
            name=name,
            role=role,
            permissions=permissions,
            created_at=time.time()
        )
        
        self.users[user_id] = user
        return user
    
    def authenticate_user(self, email: str, password_hash: str) -> Optional[User]:
        """Authenticate user (simplified - in production use proper auth)."""
        for user in self.users.values():
            if user.email == email and user.is_active:
                user.last_login = time.time()
                return user
        return None
    
    def create_session(self, user: User, ip_address: str, user_agent: str) -> Session:
        """Create a new user session."""
        session_id = self._generate_session_id()
        expires_at = time.time() + (24 * 60 * 60)  # 24 hours
        
        session = Session(
            session_id=session_id,
            user_id=user.id,
            created_at=time.time(),
            expires_at=expires_at,
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        self.sessions[session_id] = session
        return session
    
    def validate_session(self, session_id: str) -> Optional[Session]:
        """Validate session and return user if valid."""
        if session_id not in self.sessions:
            return None
        
        session = self.sessions[session_id]
        
        # Check if session is expired
        if time.time() > session.expires_at:
            session.is_valid = False
            return None
        
        # Check if session is still valid
        if not session.is_valid:
            return None
        
        return session
    
    def check_permission(self, user: User, permission: Permission) -> bool:
        """Check if user has specific permission."""
        return permission in user.permissions
    
    def check_role_permission(self, role: UserRole, permission: Permission) -> bool:
        """Check if role has specific permission."""
        return permission in self.role_permissions[role]
    
    def revoke_session(self, session_id: str):
        """Revoke a session."""
        if session_id in self.sessions:
            self.sessions[session_id].is_valid = False
    
    def get_user_by_id(self, user_id: str) -> Optional[User]:
        """Get user by ID."""
        return self.users.get(user_id)
    
    def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email."""
        for user in self.users.values():
            if user.email == email:
                return user
        return None
    
    def list_users(self) -> List[User]:
        """List all users."""
        return list(self.users.values())
    
    def update_user_role(self, user_id: str, new_role: UserRole):
        """Update user role."""
        if user_id in self.users:
            user = self.users[user_id]
            user.role = new_role
            user.permissions = self.role_permissions[new_role]
    
    def deactivate_user(self, user_id: str):
        """Deactivate user."""
        if user_id in self.users:
            self.users[user_id].is_active = False
    
    def _generate_user_id(self, email: str) -> str:
        """Generate unique user ID."""
        return hashlib.sha256(email.encode()).hexdigest()[:16]
    
    def _generate_session_id(self) -> str:
        """Generate secure session ID."""
        return secrets.token_urlsafe(32)
    
    def get_security_stats(self) -> Dict[str, Any]:
        """Get security statistics."""
        active_sessions = sum(1 for s in self.sessions.values() if s.is_valid)
        total_users = len(self.users)
        active_users = sum(1 for u in self.users.values() if u.is_active)
        
        return {
            "total_users": total_users,
            "active_users": active_users,
            "active_sessions": active_sessions,
            "roles": {
                role.value: sum(1 for u in self.users.values() if u.role == role)
                for role in UserRole
            }
        }

# Global security manager instance
security_manager = SecurityManager()

def get_security_manager() -> SecurityManager:
    """Get security manager instance."""
    return security_manager

def require_permission(permission: Permission):
    """Decorator to require specific permission."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            # In a real implementation, you'd get the current user from session
            # For now, we'll assume admin access
            admin_user = security_manager.get_user_by_id("admin")
            if not security_manager.check_permission(admin_user, permission):
                raise PermissionError(f"Permission {permission.value} required")
            return func(*args, **kwargs)
        return wrapper
    return decorator

def require_role(role: UserRole):
    """Decorator to require specific role."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            # In a real implementation, you'd get the current user from session
            # For now, we'll assume admin access
            admin_user = security_manager.get_user_by_id("admin")
            if admin_user.role != role and admin_user.role != UserRole.ADMIN:
                raise PermissionError(f"Role {role.value} required")
            return func(*args, **kwargs)
        return wrapper
    return decorator
