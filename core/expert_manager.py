#!/usr/bin/env python3
"""
Expert Manager
Manages expert teams, members, and expert-related operations
"""

import json
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

from core.database_optimization import db_optimizer
from core.trace_context import get_trace_id

logger = logging.getLogger(__name__)

class ExpertManager:
    """Manages expert teams and members"""
    
    def __init__(self):
        logger.info("👥 Expert manager initialized")
    
    def create_expert_team(
        self,
        tenant_id: str,
        name: str,
        description: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a new expert team
        
        Args:
            tenant_id: Tenant ID
            name: Team name
            description: Optional team description
        
        Returns:
            Dict with team details
        """
        try:
            team_id = db_optimizer.execute_query(
                """INSERT INTO expert_teams (tenant_id, name, description)
                   VALUES (?, ?, ?)""",
                (tenant_id, name, description),
                fetch=False
            )
            
            logger.info(f"✅ Created expert team {team_id} for tenant {tenant_id}")
            
            return {
                'success': True,
                'team_id': team_id,
                'name': name,
                'description': description
            }
        except Exception as e:
            logger.error(f"❌ Failed to create expert team: {e}")
            return {
                'success': False,
                'error': str(e),
                'error_code': 'TEAM_CREATE_FAILED'
            }
    
    def add_team_member(
        self,
        team_id: int,
        user_id: int,
        role: str = 'expert'
    ) -> Dict[str, Any]:
        """
        Add member to expert team
        
        Args:
            team_id: Team ID
            user_id: User ID to add
            role: Member role ('expert' or 'admin')
        
        Returns:
            Dict with result
        """
        try:
            db_optimizer.execute_query(
                """INSERT OR IGNORE INTO expert_team_members (team_id, user_id, role)
                   VALUES (?, ?, ?)""",
                (team_id, user_id, role),
                fetch=False
            )
            
            logger.info(f"✅ Added user {user_id} to team {team_id}")
            
            return {
                'success': True,
                'team_id': team_id,
                'user_id': user_id,
                'role': role
            }
        except Exception as e:
            logger.error(f"❌ Failed to add team member: {e}")
            return {
                'success': False,
                'error': str(e),
                'error_code': 'MEMBER_ADD_FAILED'
            }
    
    def get_team_members(self, team_id: int) -> List[Dict[str, Any]]:
        """Get all members of a team"""
        try:
            members = db_optimizer.execute_query(
                """SELECT etm.id, etm.user_id, etm.role, etm.is_active, u.name, u.email
                   FROM expert_team_members etm
                   JOIN users u ON etm.user_id = u.id
                   WHERE etm.team_id = ?""",
                (team_id,)
            )
            
            return [
                {
                    'id': m['id'],
                    'user_id': m['user_id'],
                    'name': m['name'],
                    'email': m['email'],
                    'role': m['role'],
                    'is_active': bool(m['is_active'])
                }
                for m in members
            ]
        except Exception as e:
            logger.error(f"Failed to get team members: {e}")
            return []
    
    def get_expert_teams(self, tenant_id: str) -> List[Dict[str, Any]]:
        """Get all expert teams for a tenant"""
        try:
            teams = db_optimizer.execute_query(
                """SELECT id, name, description, created_at 
                   FROM expert_teams WHERE tenant_id = ?""",
                (tenant_id,)
            )
            
            return [
                {
                    'id': t['id'],
                    'name': t['name'],
                    'description': t['description'],
                    'created_at': t['created_at']
                }
                for t in teams
            ]
        except Exception as e:
            logger.error(f"Failed to get expert teams: {e}")
            return []
    
    def get_expert_stats(self, expert_user_id: int) -> Dict[str, Any]:
        """Get statistics for an expert"""
        try:
            # Total assigned questions
            total_assigned = db_optimizer.execute_query(
                """SELECT COUNT(*) as count FROM escalated_questions 
                   WHERE assigned_to = ?""",
                (expert_user_id,)
            )
            total = total_assigned[0]['count'] if total_assigned else 0
            
            # Resolved questions
            resolved = db_optimizer.execute_query(
                """SELECT COUNT(*) as count FROM escalated_questions 
                   WHERE assigned_to = ? AND status = 'resolved'""",
                (expert_user_id,)
            )
            resolved_count = resolved[0]['count'] if resolved else 0
            
            # Pending questions
            pending = db_optimizer.execute_query(
                """SELECT COUNT(*) as count FROM escalated_questions 
                   WHERE assigned_to = ? AND status IN ('pending', 'assigned', 'in_progress')""",
                (expert_user_id,)
            )
            pending_count = pending[0]['count'] if pending else 0
            
            return {
                'total_assigned': total,
                'resolved': resolved_count,
                'pending': pending_count,
                'resolution_rate': (resolved_count / total * 100) if total > 0 else 0
            }
        except Exception as e:
            logger.error(f"Failed to get expert stats: {e}")
            return {
                'total_assigned': 0,
                'resolved': 0,
                'pending': 0,
                'resolution_rate': 0
            }

# Global expert manager instance
_expert_manager = None

def get_expert_manager() -> ExpertManager:
    """Get global expert manager instance"""
    global _expert_manager
    if _expert_manager is None:
        _expert_manager = ExpertManager()
    return _expert_manager
