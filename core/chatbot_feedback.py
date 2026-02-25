#!/usr/bin/env python3
"""
Chatbot Feedback System
Collects and processes user feedback on chatbot answers
"""

import json
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

from core.database_optimization import db_optimizer
from core.trace_context import get_trace_id

logger = logging.getLogger(__name__)

class ChatbotFeedbackSystem:
    """System for collecting and processing chatbot feedback"""
    
    def __init__(self):
        logger.info("💬 Chatbot feedback system initialized")
    
    def record_feedback(
        self,
        conversation_id: str,
        helpful: bool,
        feedback_text: Optional[str] = None,
        message_id: Optional[str] = None,
        user_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Record user feedback on a chatbot answer.

        metadata may include confidence_score, retrieval_confidence, llm_confidence
        for evaluation (stored in conversation_feedback.metadata when column exists).
        """
        try:
            meta_json = json.dumps(metadata)[:10000] if metadata else None
            params = (conversation_id, message_id, helpful, feedback_text, user_id)
            try:
                feedback_id = db_optimizer.execute_query(
                    """INSERT INTO conversation_feedback 
                       (conversation_id, message_id, helpful, feedback_text, user_id, metadata)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    params + (meta_json,),
                    fetch=False
                )
            except Exception:
                feedback_id = db_optimizer.execute_query(
                    """INSERT INTO conversation_feedback 
                       (conversation_id, message_id, helpful, feedback_text, user_id)
                       VALUES (?, ?, ?, ?, ?)""",
                    params,
                    fetch=False
                )
            
            logger.info(
                f"📝 Recorded feedback {feedback_id} (conversation: {conversation_id}, helpful: {helpful})",
                extra={
                    'event': 'feedback_recorded',
                    'service': 'chatbot_feedback',
                    'severity': 'INFO',
                    'feedback_id': feedback_id,
                    'conversation_id': conversation_id,
                    'helpful': helpful
                }
            )
            
            return {
                'success': True,
                'feedback_id': feedback_id,
                'message': 'Feedback recorded successfully'
            }
        except Exception as e:
            logger.error(f"❌ Failed to record feedback: {e}")
            return {
                'success': False,
                'error': str(e),
                'error_code': 'FEEDBACK_RECORD_FAILED'
            }
    
    def get_conversation_feedback(self, conversation_id: str) -> List[Dict[str, Any]]:
        """Get all feedback for a conversation"""
        try:
            feedbacks = db_optimizer.execute_query(
                """SELECT id, message_id, helpful, feedback_text, user_id, created_at
                   FROM conversation_feedback 
                   WHERE conversation_id = ?
                   ORDER BY created_at DESC""",
                (conversation_id,)
            )
            
            return [
                {
                    'id': f['id'],
                    'message_id': f['message_id'],
                    'helpful': bool(f['helpful']),
                    'feedback_text': f['feedback_text'],
                    'user_id': f['user_id'],
                    'created_at': f['created_at']
                }
                for f in feedbacks
            ]
        except Exception as e:
            logger.error(f"Failed to get conversation feedback: {e}")
            return []
    
    def get_feedback_stats(self, conversation_id: Optional[str] = None) -> Dict[str, Any]:
        """Get feedback statistics"""
        try:
            if conversation_id:
                helpful = db_optimizer.execute_query(
                    """SELECT COUNT(*) as count FROM conversation_feedback 
                       WHERE conversation_id = ? AND helpful = 1""",
                    (conversation_id,)
                )
                not_helpful = db_optimizer.execute_query(
                    """SELECT COUNT(*) as count FROM conversation_feedback 
                       WHERE conversation_id = ? AND helpful = 0""",
                    (conversation_id,)
                )
            else:
                helpful = db_optimizer.execute_query(
                    "SELECT COUNT(*) as count FROM conversation_feedback WHERE helpful = 1"
                )
                not_helpful = db_optimizer.execute_query(
                    "SELECT COUNT(*) as count FROM conversation_feedback WHERE helpful = 0"
                )
            
            helpful_count = helpful[0]['count'] if helpful else 0
            not_helpful_count = not_helpful[0]['count'] if not_helpful else 0
            total = helpful_count + not_helpful_count
            
            return {
                'total_feedback': total,
                'helpful': helpful_count,
                'not_helpful': not_helpful_count,
                'helpfulness_rate': (helpful_count / total * 100) if total > 0 else 0
            }
        except Exception as e:
            logger.error(f"Failed to get feedback stats: {e}")
            return {
                'total_feedback': 0,
                'helpful': 0,
                'not_helpful': 0,
                'helpfulness_rate': 0
            }

    def get_evaluation_stats(
        self,
        tenant_id: Optional[str] = None,
        since: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Aggregate stats by joining chatbot_query_log with conversation_feedback
        for evaluation (confidence vs helpfulness, fallback rate, etc.).
        """
        try:
            if not db_optimizer.table_exists("chatbot_query_log"):
                return {
                    "total_queries": 0,
                    "total_with_feedback": 0,
                    "helpfulness_rate": 0.0,
                    "avg_confidence_when_helpful": 0.0,
                    "avg_confidence_when_not_helpful": 0.0,
                    "fallback_rate": 0.0,
                }
            params = []
            tenant_clause = ""
            if tenant_id is not None:
                tenant_clause = " AND q.tenant_id = ?"
                params.append(tenant_id)
            since_clause = ""
            if since is not None:
                since_clause = " AND q.created_at >= ?"
                params.append(since.isoformat() if hasattr(since, "isoformat") else since)

            # Total queries (from log)
            total_q = db_optimizer.execute_query(
                "SELECT COUNT(*) as c FROM chatbot_query_log q WHERE 1=1" + tenant_clause + since_clause,
                tuple(params)
            )
            total_queries = total_q[0]["c"] if total_q else 0

            # Fallback rate
            fallback_q = db_optimizer.execute_query(
                "SELECT COUNT(*) as c FROM chatbot_query_log q WHERE q.fallback_used = 1" + tenant_clause + since_clause,
                tuple(params)
            )
            fallback_count = fallback_q[0]["c"] if fallback_q else 0
            fallback_rate = (fallback_count / total_queries * 100) if total_queries else 0.0

            # Join with feedback (same conversation_id + message_id)
            join_sql = """
                SELECT q.confidence, f.helpful
                FROM chatbot_query_log q
                INNER JOIN conversation_feedback f
                  ON q.conversation_id = f.conversation_id AND q.message_id = f.message_id
                WHERE 1=1
            """ + tenant_clause + since_clause
            rows = db_optimizer.execute_query(join_sql, tuple(params))
            if not rows:
                return {
                    "total_queries": total_queries,
                    "total_with_feedback": 0,
                    "helpfulness_rate": 0.0,
                    "avg_confidence_when_helpful": 0.0,
                    "avg_confidence_when_not_helpful": 0.0,
                    "fallback_rate": fallback_rate,
                }
            helpful_list = [r["confidence"] for r in rows if r.get("helpful")]
            not_helpful_list = [r["confidence"] for r in rows if not r.get("helpful")]
            total_with_feedback = len(rows)
            helpful_count = len(helpful_list)
            not_helpful_count = len(not_helpful_list)
            helpfulness_rate = (helpful_count / total_with_feedback * 100) if total_with_feedback else 0.0
            avg_conf_helpful = sum(helpful_list) / len(helpful_list) if helpful_list else 0.0
            avg_conf_not = sum(not_helpful_list) / len(not_helpful_list) if not_helpful_list else 0.0

            return {
                "total_queries": total_queries,
                "total_with_feedback": total_with_feedback,
                "helpfulness_rate": round(helpfulness_rate, 2),
                "avg_confidence_when_helpful": round(avg_conf_helpful, 4),
                "avg_confidence_when_not_helpful": round(avg_conf_not, 4),
                "fallback_rate": round(fallback_rate, 2),
            }
        except Exception as e:
            logger.error("Failed to get evaluation stats: %s", e)
            return {
                "total_queries": 0,
                "total_with_feedback": 0,
                "helpfulness_rate": 0.0,
                "avg_confidence_when_helpful": 0.0,
                "avg_confidence_when_not_helpful": 0.0,
                "fallback_rate": 0.0,
            }

# Global feedback system instance
_feedback_system = None

def get_feedback_system() -> ChatbotFeedbackSystem:
    """Get global feedback system instance"""
    global _feedback_system
    if _feedback_system is None:
        _feedback_system = ChatbotFeedbackSystem()
    return _feedback_system
