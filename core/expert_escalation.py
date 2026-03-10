#!/usr/bin/env python3
"""
Expert Escalation Engine
Handles escalation of low-confidence chatbot answers to human experts
"""

import json
import logging
import os
import uuid
from typing import Dict, Any, Optional, List
from datetime import datetime
from dataclasses import dataclass
from enum import Enum

from core.database_optimization import db_optimizer
from core.trace_context import get_trace_id

logger = logging.getLogger(__name__)

class EscalationStatus(Enum):
    """Escalation status types"""
    PENDING = "pending"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    CLOSED = "closed"

@dataclass
class EscalatedQuestion:
    """Escalated question data structure"""
    id: int
    conversation_id: str
    tenant_id: str
    user_id: Optional[str]
    question: str
    original_answer: Optional[str]
    confidence: float
    assigned_to: Optional[int]
    team_id: Optional[int]
    status: EscalationStatus
    resolution: Optional[str]
    created_at: datetime
    assigned_at: Optional[datetime]
    resolved_at: Optional[datetime]

class ExpertEscalationEngine:
    """Engine for escalating low-confidence answers to experts"""
    
    def __init__(self, confidence_threshold: float = 0.7):
        """
        Initialize escalation engine
        
        Args:
            confidence_threshold: Minimum confidence score to avoid escalation (default 0.7)
        """
        self.confidence_threshold = confidence_threshold
        logger.info(f"🔧 Expert escalation engine initialized (threshold: {confidence_threshold})")
    
    def should_escalate(self, confidence: float, fallback_used: bool = False) -> bool:
        """
        Determine if a question should be escalated to experts
        
        Args:
            confidence: Confidence score from chatbot (0-1)
            fallback_used: Whether fallback response was used
        
        Returns:
            True if should escalate, False otherwise
        """
        if fallback_used:
            return True
        return confidence < self.confidence_threshold
    
    def escalate_question(
        self,
        conversation_id: str,
        tenant_id: str,
        question: str,
        original_answer: Optional[str] = None,
        confidence: float = 0.0,
        user_id: Optional[str] = None,
        team_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Escalate a question to expert team
        
        Args:
            conversation_id: Conversation ID
            tenant_id: Tenant ID for multi-tenant isolation
            question: User's question
            original_answer: Bot's original answer (if any)
            confidence: Confidence score
            user_id: End user ID who asked
            team_id: Optional team ID to assign to (otherwise auto-assigns)
        
        Returns:
            Dict with escalation details
        """
        try:
            # Auto-assign to team if not specified
            if not team_id:
                team_id = self._get_default_team_for_tenant(tenant_id)
            
            # Create escalated question record
            escalated_id = db_optimizer.execute_query(
                """INSERT INTO escalated_questions 
                   (conversation_id, tenant_id, user_id, question, original_answer, confidence, team_id, status)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    conversation_id,
                    tenant_id,
                    user_id,
                    question,
                    original_answer,
                    confidence,
                    team_id,
                    EscalationStatus.PENDING.value
                ),
                fetch=False
            )
            
            # Auto-assign to available expert if team specified
            assigned_to = None
            if team_id:
                assigned_to = self._assign_to_expert(team_id, escalated_id)
            
            logger.info(
                f"📤 Escalated question {escalated_id} (conversation: {conversation_id}, confidence: {confidence:.2f})",
                extra={
                    'event': 'question_escalated',
                    'service': 'expert_escalation',
                    'severity': 'INFO',
                    'escalated_question_id': escalated_id,
                    'conversation_id': conversation_id,
                    'tenant_id': tenant_id,
                    'confidence': confidence,
                    'team_id': team_id,
                    'assigned_to': assigned_to
                }
            )
            
            return {
                'success': True,
                'escalated_question_id': escalated_id,
                'conversation_id': conversation_id,
                'status': EscalationStatus.PENDING.value,
                'assigned_to': assigned_to,
                'team_id': team_id,
                'message': 'Question escalated to expert team'
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to escalate question: {e}", exc_info=True)
            return {
                'success': False,
                'error': str(e),
                'error_code': 'ESCALATION_FAILED'
            }
    
    def _get_default_team_for_tenant(self, tenant_id: str) -> Optional[int]:
        """Get default expert team for tenant"""
        try:
            teams = db_optimizer.execute_query(
                "SELECT id FROM expert_teams WHERE tenant_id = ? ORDER BY created_at ASC LIMIT 1",
                (tenant_id,)
            )
            if teams:
                return teams[0]['id']
        except Exception as e:
            logger.warning(f"Failed to get default team for tenant {tenant_id}: {e}")
        return None
    
    def _assign_to_expert(self, team_id: int, escalated_question_id: int) -> Optional[int]:
        """
        Assign escalated question to available expert (round-robin)
        
        Args:
            team_id: Expert team ID
            escalated_question_id: Escalated question ID
        
        Returns:
            Assigned expert user_id or None
        """
        try:
            # Get active experts in team
            experts = db_optimizer.execute_query(
                """SELECT user_id FROM expert_team_members 
                   WHERE team_id = ? AND is_active = 1 
                   ORDER BY user_id ASC""",
                (team_id,)
            )
            
            if not experts:
                logger.warning(f"No active experts in team {team_id}")
                return None
            
            # Get current assignments per expert
            assignments = {}
            for expert in experts:
                expert_id = expert['user_id']
                count = db_optimizer.execute_query(
                    """SELECT COUNT(*) as count FROM escalated_questions 
                       WHERE assigned_to = ? AND status IN ('pending', 'assigned', 'in_progress')""",
                    (expert_id,)
                )
                assignments[expert_id] = count[0]['count'] if count else 0
            
            # Assign to expert with least assignments (round-robin)
            assigned_expert = min(assignments.items(), key=lambda x: x[1])[0]
            
            # Update escalated question
            db_optimizer.execute_query(
                """UPDATE escalated_questions 
                   SET assigned_to = ?, status = ?, assigned_at = CURRENT_TIMESTAMP 
                   WHERE id = ?""",
                (assigned_expert, EscalationStatus.ASSIGNED.value, escalated_question_id),
                fetch=False
            )
            
            logger.info(f"✅ Assigned question {escalated_question_id} to expert {assigned_expert}")
            return assigned_expert
            
        except Exception as e:
            logger.error(f"Failed to assign expert: {e}")
            return None
    
    def get_escalated_question(self, escalated_question_id: int) -> Optional[EscalatedQuestion]:
        """Get escalated question by ID"""
        try:
            result = db_optimizer.execute_query(
                """SELECT id, conversation_id, tenant_id, user_id, question, original_answer, 
                   confidence, assigned_to, team_id, status, resolution, created_at, assigned_at, resolved_at
                   FROM escalated_questions WHERE id = ?""",
                (escalated_question_id,)
            )
            
            if not result:
                return None
            
            row = result[0]
            return EscalatedQuestion(
                id=row['id'],
                conversation_id=row['conversation_id'],
                tenant_id=row['tenant_id'],
                user_id=row['user_id'],
                question=row['question'],
                original_answer=row['original_answer'],
                confidence=row['confidence'],
                assigned_to=row['assigned_to'],
                team_id=row['team_id'],
                status=EscalationStatus(row['status']),
                resolution=row['resolution'],
                created_at=datetime.fromisoformat(row['created_at']) if isinstance(row['created_at'], str) else row['created_at'],
                assigned_at=datetime.fromisoformat(row['assigned_at']) if row['assigned_at'] and isinstance(row['assigned_at'], str) else row['assigned_at'],
                resolved_at=datetime.fromisoformat(row['resolved_at']) if row['resolved_at'] and isinstance(row['resolved_at'], str) else row['resolved_at']
            )
        except Exception as e:
            logger.error(f"Failed to get escalated question: {e}")
            return None
    
    def update_status(
        self,
        escalated_question_id: int,
        status: EscalationStatus,
        resolution: Optional[str] = None
    ) -> bool:
        """Update escalation status"""
        try:
            updates = ["status = ?"]
            params = [status.value, escalated_question_id]
            
            if status == EscalationStatus.RESOLVED:
                updates.append("resolved_at = CURRENT_TIMESTAMP")
            if resolution:
                updates.append("resolution = ?")
                params.insert(-1, resolution)
            
            query = f"UPDATE escalated_questions SET {', '.join(updates)} WHERE id = ?"
            db_optimizer.execute_query(query, tuple(params), fetch=False)
            
            return True
        except Exception as e:
            logger.error(f"Failed to update escalation status: {e}")
            return False

# Global escalation engine instance
_escalation_engine = None

def get_escalation_engine(confidence_threshold: float = 0.7) -> ExpertEscalationEngine:
    """Get global escalation engine instance (threshold can be overridden via env)."""
    global _escalation_engine
    if _escalation_engine is None:
        try:
            env_threshold = os.getenv("ESCALATION_CONFIDENCE_THRESHOLD")
            if env_threshold is not None:
                confidence_threshold = float(env_threshold)
        except Exception:
            pass
        _escalation_engine = ExpertEscalationEngine(confidence_threshold=confidence_threshold)
    return _escalation_engine
