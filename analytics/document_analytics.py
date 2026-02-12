"""
Document Analytics System for Fikiri Solutions
Tracks document processing metrics, usage analytics, and insights
"""

import json
import logging
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from enum import Enum
import uuid
from collections import defaultdict, Counter

from core.minimal_config import get_config

logger = logging.getLogger(__name__)

class AnalyticsEventType(Enum):
    """Analytics event types"""
    DOCUMENT_PROCESSED = "document_processed"
    FORM_SUBMITTED = "form_submitted"
    TEMPLATE_USED = "template_used"
    DOCUMENT_GENERATED = "document_generated"
    OCR_PERFORMED = "ocr_performed"
    VALIDATION_FAILED = "validation_failed"
    CONVERSION_COMPLETED = "conversion_completed"

@dataclass
class AnalyticsEvent:
    """Analytics event data structure"""
    id: str
    event_type: AnalyticsEventType
    user_id: int
    timestamp: datetime
    metadata: Dict[str, Any]
    session_id: Optional[str] = None

@dataclass
class ProcessingMetrics:
    """Document processing metrics"""
    total_documents: int
    successful_processes: int
    failed_processes: int
    avg_processing_time: float
    total_processing_time: float
    success_rate: float
    most_common_format: str
    formats_processed: Dict[str, int]

@dataclass
class FormMetrics:
    """Form metrics"""
    total_submissions: int
    successful_submissions: int
    validation_failures: int
    avg_completion_time: float
    completion_rate: float
    most_popular_form: str
    submissions_by_form: Dict[str, int]

@dataclass
class TemplateMetrics:
    """Template usage metrics"""
    total_generations: int
    most_used_template: str
    templates_by_usage: Dict[str, int]
    documents_by_type: Dict[str, int]
    avg_generation_time: float

@dataclass
class UserEngagementMetrics:
    """User engagement metrics"""
    active_users: int
    total_sessions: int
    avg_session_duration: float
    documents_per_user: float
    most_active_user: int

class DocumentAnalyticsSystem:
    """Document processing and form analytics system"""
    
    def __init__(self):
        self.config = get_config()
        self.events = {}  # In-memory storage for demo
        self.sessions = {}  # Track user sessions
        
        logger.info("📊 Document analytics system initialized")
    
    def track_event(self, event_type: AnalyticsEventType, user_id: int, 
                   metadata: Dict[str, Any], session_id: Optional[str] = None) -> str:
        """Track an analytics event"""
        try:
            event_id = str(uuid.uuid4())
            event = AnalyticsEvent(
                id=event_id,
                event_type=event_type,
                user_id=user_id,
                timestamp=datetime.now(),
                metadata=metadata,
                session_id=session_id
            )
            
            self.events[event_id] = event
            
            # Update session tracking
            if session_id:
                if session_id not in self.sessions:
                    self.sessions[session_id] = {
                        'user_id': user_id,
                        'start_time': datetime.now(),
                        'last_activity': datetime.now(),
                        'events': []
                    }
                self.sessions[session_id]['last_activity'] = datetime.now()
                self.sessions[session_id]['events'].append(event_id)
            
            logger.debug(f"📊 Tracked event: {event_type.value} for user {user_id}")
            return event_id
            
        except Exception as e:
            logger.error(f"❌ Failed to track analytics event: {e}")
            return ""
    
    def track_document_processing(self, user_id: int, file_type: str, 
                                processing_time: float, success: bool, 
                                error: Optional[str] = None, session_id: Optional[str] = None) -> str:
        """Track document processing event"""
        metadata = {
            "file_type": file_type,
            "processing_time": processing_time,
            "success": success,
            "error": error,
            "timestamp": datetime.now().isoformat()
        }
        
        return self.track_event(
            AnalyticsEventType.DOCUMENT_PROCESSED,
            user_id,
            metadata,
            session_id
        )
    
    def track_form_submission(self, user_id: int, form_id: str, 
                            completion_time: float, success: bool,
                            validation_errors: List[str] = None, 
                            session_id: Optional[str] = None) -> str:
        """Track form submission event"""
        metadata = {
            "form_id": form_id,
            "completion_time": completion_time,
            "success": success,
            "validation_errors": validation_errors or [],
            "error_count": len(validation_errors) if validation_errors else 0,
            "timestamp": datetime.now().isoformat()
        }
        
        event_type = AnalyticsEventType.FORM_SUBMITTED if success else AnalyticsEventType.VALIDATION_FAILED
        
        return self.track_event(event_type, user_id, metadata, session_id)
    
    def track_template_usage(self, user_id: int, template_id: str, 
                           document_type: str, generation_time: float,
                           session_id: Optional[str] = None) -> str:
        """Track template usage event"""
        metadata = {
            "template_id": template_id,
            "document_type": document_type,
            "generation_time": generation_time,
            "timestamp": datetime.now().isoformat()
        }
        
        return self.track_event(
            AnalyticsEventType.TEMPLATE_USED,
            user_id,
            metadata,
            session_id
        )
    
    def track_ocr_processing(self, user_id: int, image_format: str, 
                           confidence_score: float, text_length: int,
                           processing_time: float, session_id: Optional[str] = None) -> str:
        """Track OCR processing event"""
        metadata = {
            "image_format": image_format,
            "confidence_score": confidence_score,
            "text_length": text_length,
            "processing_time": processing_time,
            "timestamp": datetime.now().isoformat()
        }
        
        return self.track_event(
            AnalyticsEventType.OCR_PERFORMED,
            user_id,
            metadata,
            session_id
        )
    
    def get_processing_metrics(self, days: int = 30) -> ProcessingMetrics:
        """Get document processing metrics for the last N days"""
        cutoff_date = datetime.now() - timedelta(days=days)
        
        processing_events = [
            e for e in self.events.values()
            if e.event_type == AnalyticsEventType.DOCUMENT_PROCESSED
            and e.timestamp >= cutoff_date
        ]
        
        if not processing_events:
            return ProcessingMetrics(
                total_documents=0,
                successful_processes=0,
                failed_processes=0,
                avg_processing_time=0,
                total_processing_time=0,
                success_rate=0,
                most_common_format="",
                formats_processed={}
            )
        
        total_documents = len(processing_events)
        successful_processes = len([e for e in processing_events if e.metadata.get('success', False)])
        failed_processes = total_documents - successful_processes
        
        processing_times = [e.metadata.get('processing_time', 0) for e in processing_events]
        total_processing_time = sum(processing_times)
        avg_processing_time = total_processing_time / len(processing_times) if processing_times else 0
        
        success_rate = (successful_processes / total_documents) * 100 if total_documents > 0 else 0
        
        # Count formats
        formats = [e.metadata.get('file_type', 'unknown') for e in processing_events]
        format_counts = Counter(formats)
        most_common_format = format_counts.most_common(1)[0][0] if format_counts else ""
        
        return ProcessingMetrics(
            total_documents=total_documents,
            successful_processes=successful_processes,
            failed_processes=failed_processes,
            avg_processing_time=avg_processing_time,
            total_processing_time=total_processing_time,
            success_rate=success_rate,
            most_common_format=most_common_format,
            formats_processed=dict(format_counts)
        )
    
    def get_form_metrics(self, days: int = 30) -> FormMetrics:
        """Get form submission metrics for the last N days"""
        cutoff_date = datetime.now() - timedelta(days=days)
        
        form_events = [
            e for e in self.events.values()
            if e.event_type in [AnalyticsEventType.FORM_SUBMITTED, AnalyticsEventType.VALIDATION_FAILED]
            and e.timestamp >= cutoff_date
        ]
        
        if not form_events:
            return FormMetrics(
                total_submissions=0,
                successful_submissions=0,
                validation_failures=0,
                avg_completion_time=0,
                completion_rate=0,
                most_popular_form="",
                submissions_by_form={}
            )
        
        total_submissions = len(form_events)
        successful_submissions = len([e for e in form_events if e.event_type == AnalyticsEventType.FORM_SUBMITTED])
        validation_failures = total_submissions - successful_submissions
        
        completion_times = [e.metadata.get('completion_time', 0) for e in form_events if e.metadata.get('completion_time', 0) > 0]
        avg_completion_time = sum(completion_times) / len(completion_times) if completion_times else 0
        
        completion_rate = (successful_submissions / total_submissions) * 100 if total_submissions > 0 else 0
        
        # Count forms
        forms = [e.metadata.get('form_id', 'unknown') for e in form_events]
        form_counts = Counter(forms)
        most_popular_form = form_counts.most_common(1)[0][0] if form_counts else ""
        
        return FormMetrics(
            total_submissions=total_submissions,
            successful_submissions=successful_submissions,
            validation_failures=validation_failures,
            avg_completion_time=avg_completion_time,
            completion_rate=completion_rate,
            most_popular_form=most_popular_form,
            submissions_by_form=dict(form_counts)
        )
    
    def get_template_metrics(self, days: int = 30) -> TemplateMetrics:
        """Get template usage metrics for the last N days"""
        cutoff_date = datetime.now() - timedelta(days=days)
        
        template_events = [
            e for e in self.events.values()
            if e.event_type == AnalyticsEventType.TEMPLATE_USED
            and e.timestamp >= cutoff_date
        ]
        
        if not template_events:
            return TemplateMetrics(
                total_generations=0,
                most_used_template="",
                templates_by_usage={},
                documents_by_type={},
                avg_generation_time=0
            )
        
        total_generations = len(template_events)
        
        # Count templates
        templates = [e.metadata.get('template_id', 'unknown') for e in template_events]
        template_counts = Counter(templates)
        most_used_template = template_counts.most_common(1)[0][0] if template_counts else ""
        
        # Count document types
        doc_types = [e.metadata.get('document_type', 'unknown') for e in template_events]
        doc_type_counts = Counter(doc_types)
        
        # Calculate average generation time
        generation_times = [e.metadata.get('generation_time', 0) for e in template_events]
        avg_generation_time = sum(generation_times) / len(generation_times) if generation_times else 0
        
        return TemplateMetrics(
            total_generations=total_generations,
            most_used_template=most_used_template,
            templates_by_usage=dict(template_counts),
            documents_by_type=dict(doc_type_counts),
            avg_generation_time=avg_generation_time
        )
    
    def get_user_engagement_metrics(self, days: int = 30) -> UserEngagementMetrics:
        """Get user engagement metrics for the last N days"""
        cutoff_date = datetime.now() - timedelta(days=days)
        
        recent_events = [
            e for e in self.events.values()
            if e.timestamp >= cutoff_date
        ]
        
        if not recent_events:
            return UserEngagementMetrics(
                active_users=0,
                total_sessions=0,
                avg_session_duration=0,
                documents_per_user=0,
                most_active_user=0
            )
        
        # Count unique active users
        active_users = len(set(e.user_id for e in recent_events))
        
        # Count sessions
        recent_sessions = [
            s for s in self.sessions.values()
            if s['start_time'] >= cutoff_date
        ]
        total_sessions = len(recent_sessions)
        
        # Calculate average session duration
        session_durations = []
        for session in recent_sessions:
            duration = (session['last_activity'] - session['start_time']).total_seconds() / 60  # minutes
            session_durations.append(duration)
        
        avg_session_duration = sum(session_durations) / len(session_durations) if session_durations else 0
        
        # Calculate documents per user
        user_document_counts = Counter(e.user_id for e in recent_events if e.event_type == AnalyticsEventType.DOCUMENT_PROCESSED)
        documents_per_user = sum(user_document_counts.values()) / len(user_document_counts) if user_document_counts else 0
        
        # Find most active user
        most_active_user = user_document_counts.most_common(1)[0][0] if user_document_counts else 0
        
        return UserEngagementMetrics(
            active_users=active_users,
            total_sessions=total_sessions,
            avg_session_duration=avg_session_duration,
            documents_per_user=documents_per_user,
            most_active_user=most_active_user
        )
    
    def get_comprehensive_report(self, days: int = 30) -> Dict[str, Any]:
        """Get comprehensive analytics report"""
        processing_metrics = self.get_processing_metrics(days)
        form_metrics = self.get_form_metrics(days)
        template_metrics = self.get_template_metrics(days)
        engagement_metrics = self.get_user_engagement_metrics(days)
        
        # Calculate trends
        trends = self._calculate_trends(days)
        
        # Generate insights
        insights = self._generate_insights(processing_metrics, form_metrics, template_metrics, engagement_metrics)
        
        return {
            "report_period": f"Last {days} days",
            "generated_at": datetime.now().isoformat(),
            "processing_metrics": asdict(processing_metrics),
            "form_metrics": asdict(form_metrics),
            "template_metrics": asdict(template_metrics),
            "engagement_metrics": asdict(engagement_metrics),
            "trends": trends,
            "insights": insights,
            "summary": {
                "total_events": len([e for e in self.events.values() if e.timestamp >= datetime.now() - timedelta(days=days)]),
                "active_users": engagement_metrics.active_users,
                "success_rate": processing_metrics.success_rate,
                "most_used_feature": self._get_most_used_feature(days)
            }
        }
    
    def _calculate_trends(self, days: int) -> Dict[str, Any]:
        """Calculate trends over time"""
        cutoff_date = datetime.now() - timedelta(days=days)
        recent_events = [e for e in self.events.values() if e.timestamp >= cutoff_date]
        
        # Group events by day
        daily_events = defaultdict(int)
        for event in recent_events:
            day = event.timestamp.date()
            daily_events[day] += 1
        
        # Calculate daily averages
        if len(daily_events) > 1:
            daily_counts = list(daily_events.values())
            avg_daily_events = sum(daily_counts) / len(daily_counts)
            
            # Simple trend calculation (last half vs first half)
            mid_point = len(daily_counts) // 2
            first_half_avg = sum(daily_counts[:mid_point]) / mid_point if mid_point > 0 else 0
            second_half_avg = sum(daily_counts[mid_point:]) / (len(daily_counts) - mid_point) if len(daily_counts) - mid_point > 0 else 0
            
            trend_direction = "increasing" if second_half_avg > first_half_avg else "decreasing" if second_half_avg < first_half_avg else "stable"
            trend_percentage = ((second_half_avg - first_half_avg) / first_half_avg * 100) if first_half_avg > 0 else 0
        else:
            avg_daily_events = 0
            trend_direction = "stable"
            trend_percentage = 0
        
        return {
            "avg_daily_events": avg_daily_events,
            "trend_direction": trend_direction,
            "trend_percentage": round(trend_percentage, 2),
            "daily_breakdown": {str(k): v for k, v in daily_events.items()}
        }
    
    def _generate_insights(self, processing: ProcessingMetrics, forms: FormMetrics, 
                          templates: TemplateMetrics, engagement: UserEngagementMetrics) -> List[str]:
        """Generate actionable insights from metrics"""
        insights = []
        
        # Processing insights
        if processing.success_rate < 90:
            insights.append(f"Document processing success rate is {processing.success_rate:.1f}% - consider improving error handling")
        elif processing.success_rate > 95:
            insights.append("Excellent document processing success rate - system is performing well")
        
        # Form insights
        if forms.completion_rate < 80:
            insights.append(f"Form completion rate is {forms.completion_rate:.1f}% - consider simplifying forms or improving UX")
        
        if forms.avg_completion_time > 300:  # 5 minutes
            insights.append("Average form completion time is high - consider reducing form complexity")
        
        # Template insights
        if templates.total_generations > 0:
            insights.append(f"Most popular template: {templates.most_used_template}")
        
        # Engagement insights
        if engagement.avg_session_duration < 5:  # 5 minutes
            insights.append("Short average session duration - consider improving user engagement")
        elif engagement.avg_session_duration > 30:  # 30 minutes
            insights.append("High user engagement - users are finding value in the platform")
        
        if engagement.documents_per_user < 2:
            insights.append("Low documents per user - consider promoting template usage")
        
        return insights
    
    def _get_most_used_feature(self, days: int) -> str:
        """Get the most used feature in the last N days"""
        cutoff_date = datetime.now() - timedelta(days=days)
        recent_events = [e for e in self.events.values() if e.timestamp >= cutoff_date]
        
        if not recent_events:
            return "None"
        
        feature_counts = Counter(e.event_type.value for e in recent_events)
        return feature_counts.most_common(1)[0][0] if feature_counts else "None"
    
    def export_analytics_data(self, days: int = 30, format: str = "json") -> str:
        """Export analytics data in specified format"""
        report = self.get_comprehensive_report(days)
        
        if format.lower() == "json":
            return json.dumps(report, indent=2, default=str)
        elif format.lower() == "csv":
            # Simple CSV export of events
            cutoff_date = datetime.now() - timedelta(days=days)
            recent_events = [e for e in self.events.values() if e.timestamp >= cutoff_date]
            
            csv_lines = ["event_id,event_type,user_id,timestamp,metadata"]
            for event in recent_events:
                metadata_str = json.dumps(event.metadata).replace(',', ';')  # Escape commas
                csv_lines.append(f"{event.id},{event.event_type.value},{event.user_id},{event.timestamp},{metadata_str}")
            
            return "\n".join(csv_lines)
        else:
            return json.dumps(report, indent=2, default=str)
    
    def get_real_time_stats(self) -> Dict[str, Any]:
        """Get real-time statistics for dashboard"""
        now = datetime.now()
        today = now.date()
        
        # Today's events
        today_events = [e for e in self.events.values() if e.timestamp.date() == today]
        
        # Active sessions (last 30 minutes)
        active_cutoff = now - timedelta(minutes=30)
        active_sessions = [s for s in self.sessions.values() if s['last_activity'] >= active_cutoff]
        
        return {
            "events_today": len(today_events),
            "active_sessions": len(active_sessions),
            "total_events": len(self.events),
            "total_users": len(set(e.user_id for e in self.events.values())),
            "last_event_time": max([e.timestamp for e in self.events.values()]).isoformat() if self.events else None,
            "system_uptime": "System running normally"
        }

# Global instance
document_analytics = DocumentAnalyticsSystem()

def get_document_analytics() -> DocumentAnalyticsSystem:
    """Get the global document analytics instance"""
    return document_analytics
