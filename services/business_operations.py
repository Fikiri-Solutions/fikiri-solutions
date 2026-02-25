"""
Business Operations System
Legal pages, analytics, and business intelligence for Fikiri Solutions
"""

from flask import Blueprint, render_template_string, request, jsonify
import json
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import time

logger = logging.getLogger(__name__)

# ============================================================================
# LEGAL PAGES TEMPLATES
# ============================================================================

PRIVACY_POLICY_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Privacy Policy - Fikiri Solutions</title>
    <style>
        body { font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; line-height: 1.6; }
        h1 { color: #2563eb; }
        h2 { color: #1e40af; margin-top: 30px; }
        .last-updated { color: #666; font-style: italic; }
    </style>
</head>
<body>
    <h1>Privacy Policy</h1>
    <p class="last-updated">Last updated: {{ last_updated }}</p>
    
    <h2>1. Information We Collect</h2>
    <p>We collect information you provide directly to us, such as when you create an account, use our services, or contact us for support.</p>
    
    <h2>2. How We Use Your Information</h2>
    <p>We use the information we collect to provide, maintain, and improve our services, process transactions, and communicate with you.</p>
    
    <h2>3. Information Sharing</h2>
    <p>We do not sell, trade, or otherwise transfer your personal information to third parties without your consent, except as described in this policy.</p>
    
    <h2>4. Data Security</h2>
    <p>We implement appropriate security measures to protect your personal information against unauthorized access, alteration, disclosure, or destruction.</p>
    
    <h2>5. Your Rights</h2>
    <p>You have the right to access, update, or delete your personal information. You may also opt out of certain communications from us.</p>
    
    <h2>6. Contact Us</h2>
    <p>If you have any questions about this Privacy Policy, please contact us at privacy@fikirisolutions.com</p>
</body>
</html>
"""

TERMS_OF_SERVICE_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Terms of Service - Fikiri Solutions</title>
    <style>
        body { font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; line-height: 1.6; }
        h1 { color: #2563eb; }
        h2 { color: #1e40af; margin-top: 30px; }
        .last-updated { color: #666; font-style: italic; }
    </style>
</head>
<body>
    <h1>Terms of Service</h1>
    <p class="last-updated">Last updated: {{ last_updated }}</p>
    
    <h2>1. Acceptance of Terms</h2>
    <p>By accessing and using Fikiri Solutions, you accept and agree to be bound by the terms and provision of this agreement.</p>
    
    <h2>2. Use License</h2>
    <p>Permission is granted to temporarily download one copy of Fikiri Solutions for personal, non-commercial transitory viewing only.</p>
    
    <h2>3. Service Availability</h2>
    <p>We strive to maintain high service availability but do not guarantee uninterrupted access to our services.</p>
    
    <h2>4. User Responsibilities</h2>
    <p>Users are responsible for maintaining the confidentiality of their account information and for all activities that occur under their account.</p>
    
    <h2>5. Prohibited Uses</h2>
    <p>You may not use our service for any unlawful purpose or to solicit others to perform unlawful acts.</p>
    
    <h2>6. Limitation of Liability</h2>
    <p>In no event shall Fikiri Solutions be liable for any indirect, incidental, special, consequential, or punitive damages.</p>
    
    <h2>7. Contact Information</h2>
    <p>If you have any questions about these Terms of Service, please contact us at legal@fikirisolutions.com</p>
</body>
</html>
"""

# ============================================================================
# BUSINESS ANALYTICS SYSTEM
# ============================================================================

class BusinessAnalytics:
    """Business analytics and reporting system"""
    
    def __init__(self):
        self.metrics: Dict[str, Any] = {}
        self.reports: List[Dict[str, Any]] = []
    
    def track_event(self, event_type: str, properties: Dict[str, Any] = None):
        """Track a business event"""
        event = {
            'type': event_type,
            'properties': properties or {},
            'timestamp': datetime.now().isoformat(),
            'user_id': properties.get('user_id') if properties else None
        }
        
        # Store event (in production, this would go to a proper analytics service)
        if event_type not in self.metrics:
            self.metrics[event_type] = []
        
        self.metrics[event_type].append(event)
        
        logger.info(f"Business event tracked: {event_type}")
    
    def get_analytics_summary(self, days: int = 30) -> Dict[str, Any]:
        """Get analytics summary for the specified period"""
        cutoff_date = datetime.now() - timedelta(days=days)
        
        summary = {
            'period_days': days,
            'total_events': 0,
            'unique_users': set(),
            'event_types': {},
            'daily_breakdown': {},
            'top_events': [],
            'conversion_rates': {}
        }
        
        # Process all events
        for event_type, events in self.metrics.items():
            recent_events = [
                event for event in events 
                if datetime.fromisoformat(event['timestamp']) > cutoff_date
            ]
            
            summary['total_events'] += len(recent_events)
            summary['event_types'][event_type] = len(recent_events)
            
            # Track unique users
            for event in recent_events:
                if event.get('user_id'):
                    summary['unique_users'].add(event['user_id'])
            
            # Daily breakdown
            for event in recent_events:
                event_date = datetime.fromisoformat(event['timestamp']).date()
                if event_date not in summary['daily_breakdown']:
                    summary['daily_breakdown'][event_date.isoformat()] = 0
                summary['daily_breakdown'][event_date.isoformat()] += 1
        
        # Convert set to count
        summary['unique_users'] = len(summary['unique_users'])
        
        # Top events
        summary['top_events'] = sorted(
            summary['event_types'].items(),
            key=lambda x: x[1],
            reverse=True
        )[:10]
        
        return summary
    
    def generate_report(self, report_type: str, parameters: Dict[str, Any] = None) -> Dict[str, Any]:
        """Generate a business report"""
        report = {
            'id': f"report_{int(time.time())}",
            'type': report_type,
            'parameters': parameters or {},
            'generated_at': datetime.now().isoformat(),
            'data': {}
        }
        
        if report_type == 'user_engagement':
            report['data'] = self._generate_user_engagement_report(parameters)
        elif report_type == 'revenue_analysis':
            report['data'] = self._generate_revenue_report(parameters)
        elif report_type == 'feature_usage':
            report['data'] = self._generate_feature_usage_report(parameters)
        else:
            report['data'] = {'error': 'Unknown report type'}
        
        self.reports.append(report)
        return report
    
    def _generate_user_engagement_report(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Generate user engagement report"""
        days = parameters.get('days', 30)
        summary = self.get_analytics_summary(days)
        
        return {
            'total_users': summary['unique_users'],
            'total_events': summary['total_events'],
            'avg_events_per_user': summary['total_events'] / max(summary['unique_users'], 1),
            'daily_breakdown': summary['daily_breakdown'],
            'top_events': summary['top_events']
        }
    
    def _generate_revenue_report(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Generate revenue analysis report"""
        # Mock revenue data - in production, this would come from payment systems
        return {
            'total_revenue': 50000,
            'monthly_recurring_revenue': 15000,
            'customer_acquisition_cost': 150,
            'lifetime_value': 2500,
            'churn_rate': 0.05,
            'growth_rate': 0.25
        }
    
    def _generate_feature_usage_report(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Generate feature usage report"""
        summary = self.get_analytics_summary(30)
        
        return {
            'feature_usage': summary['event_types'],
            'most_popular_features': summary['top_events'][:5],
            'usage_trends': summary['daily_breakdown']
        }

# Global business analytics instance
business_analytics = BusinessAnalytics()

# ============================================================================
# BUSINESS INTELLIGENCE DASHBOARD
# ============================================================================

class BusinessIntelligence:
    """Business intelligence and KPI tracking"""
    
    def __init__(self):
        self.kpis: Dict[str, Any] = {}
        self.goals: Dict[str, Any] = {}
        self._initialize_default_kpis()
    
    def _initialize_default_kpis(self):
        """Initialize default KPIs"""
        self.kpis = {
            'user_registrations': {'value': 0, 'target': 1000, 'unit': 'users'},
            'monthly_active_users': {'value': 0, 'target': 500, 'unit': 'users'},
            'customer_satisfaction': {'value': 0, 'target': 4.5, 'unit': 'rating'},
            'revenue_growth': {'value': 0, 'target': 25, 'unit': '%'},
            'churn_rate': {'value': 0, 'target': 5, 'unit': '%'},
            'support_tickets': {'value': 0, 'target': 50, 'unit': 'tickets'},
            'api_uptime': {'value': 0, 'target': 99.9, 'unit': '%'},
            'response_time': {'value': 0, 'target': 200, 'unit': 'ms'}
        }
    
    def update_kpi(self, kpi_name: str, value: float):
        """Update a KPI value"""
        if kpi_name in self.kpis:
            self.kpis[kpi_name]['value'] = value
            self.kpis[kpi_name]['last_updated'] = datetime.now().isoformat()
    
    def get_kpi_dashboard(self) -> Dict[str, Any]:
        """Get KPI dashboard data"""
        dashboard = {
            'kpis': {},
            'overall_health': 0,
            'goals_met': 0,
            'total_goals': len(self.kpis)
        }
        
        goals_met = 0
        
        for kpi_name, kpi_data in self.kpis.items():
            value = kpi_data['value']
            target = kpi_data['target']
            unit = kpi_data['unit']
            
            # Calculate performance percentage
            if target > 0:
                performance = min((value / target) * 100, 200)  # Cap at 200%
            else:
                performance = 100
            
            # Determine if goal is met
            goal_met = value >= target if kpi_name != 'churn_rate' else value <= target
            if goal_met:
                goals_met += 1
            
            dashboard['kpis'][kpi_name] = {
                'value': value,
                'target': target,
                'unit': unit,
                'performance_percent': round(performance, 1),
                'goal_met': goal_met,
                'status': 'excellent' if performance >= 100 else 'good' if performance >= 80 else 'needs_attention'
            }
        
        dashboard['goals_met'] = goals_met
        dashboard['overall_health'] = round((goals_met / len(self.kpis)) * 100, 1)
        
        return dashboard
    
    def set_goal(self, kpi_name: str, target_value: float, deadline: str = None):
        """Set a goal for a KPI"""
        if kpi_name in self.kpis:
            self.kpis[kpi_name]['target'] = target_value
            if deadline:
                self.kpis[kpi_name]['deadline'] = deadline

# Global business intelligence instance
business_intelligence = BusinessIntelligence()

# ============================================================================
# LEGAL COMPLIANCE SYSTEM
# ============================================================================

class LegalCompliance:
    """Legal compliance and document management"""
    
    def __init__(self):
        self.documents: Dict[str, Dict[str, Any]] = {}
        self.consents: Dict[str, List[Dict[str, Any]]] = {}
        self._initialize_legal_documents()
    
    def _initialize_legal_documents(self):
        """Initialize legal documents"""
        self.documents = {
            'privacy_policy': {
                'version': '1.0',
                'last_updated': '2024-01-01',
                'template': PRIVACY_POLICY_TEMPLATE,
                'required': True
            },
            'terms_of_service': {
                'version': '1.0',
                'last_updated': '2024-01-01',
                'template': TERMS_OF_SERVICE_TEMPLATE,
                'required': True
            },
            'cookie_policy': {
                'version': '1.0',
                'last_updated': '2024-01-01',
                'template': 'Cookie Policy content...',
                'required': True
            }
        }
    
    def get_document(self, document_type: str) -> Dict[str, Any]:
        """Get a legal document"""
        if document_type in self.documents:
            doc = self.documents[document_type].copy()
            # Avoid str.format on HTML/CSS templates containing braces
            doc['rendered'] = doc['template'].replace("{{ last_updated }}", doc['last_updated'])
            return doc
        return {'error': 'Document not found'}
    
    def record_consent(self, user_id: str, document_type: str, consent_given: bool):
        """Record user consent for a legal document"""
        if document_type not in self.consents:
            self.consents[document_type] = []
        
        consent_record = {
            'user_id': user_id,
            'consent_given': consent_given,
            'timestamp': datetime.now().isoformat(),
            'document_version': self.documents.get(document_type, {}).get('version', '1.0')
        }
        
        self.consents[document_type].append(consent_record)
        
        logger.info(f"Consent recorded for user {user_id}: {document_type} = {consent_given}")
    
    def get_consent_status(self, user_id: str) -> Dict[str, Any]:
        """Get consent status for a user"""
        status = {}
        
        for doc_type in self.documents:
            user_consents = [
                consent for consent in self.consents.get(doc_type, [])
                if consent['user_id'] == user_id
            ]
            
            if user_consents:
                latest_consent = max(user_consents, key=lambda x: x['timestamp'])
                status[doc_type] = {
                    'consent_given': latest_consent['consent_given'],
                    'timestamp': latest_consent['timestamp'],
                    'version': latest_consent['document_version']
                }
            else:
                status[doc_type] = {
                    'consent_given': False,
                    'timestamp': None,
                    'version': None
                }
        
        return status

# Global legal compliance instance
legal_compliance = LegalCompliance()

# ============================================================================
# BUSINESS OPERATIONS BLUEPRINT
# ============================================================================

def create_business_blueprint() -> Blueprint:
    """Create business operations blueprint"""
    blueprint = Blueprint('business', __name__, url_prefix='/business')
    
    @blueprint.route('/privacy-policy')
    def privacy_policy():
        """Privacy policy page"""
        doc = legal_compliance.get_document('privacy_policy')
        return doc['rendered']
    
    @blueprint.route('/terms-of-service')
    def terms_of_service():
        """Terms of service page"""
        doc = legal_compliance.get_document('terms_of_service')
        return doc['rendered']
    
    @blueprint.route('/cookie-policy')
    def cookie_policy():
        """Cookie policy page"""
        doc = legal_compliance.get_document('cookie_policy')
        return doc['rendered']
    
    @blueprint.route('/analytics/summary')
    def analytics_summary():
        """Get analytics summary"""
        days = request.args.get('days', 30, type=int)
        summary = business_analytics.get_analytics_summary(days)
        return jsonify({
            'success': True,
            'data': summary
        })
    
    @blueprint.route('/analytics/track', methods=['POST'])
    def track_event():
        """Track a business event"""
        data = request.get_json()
        event_type = data.get('event_type')
        properties = data.get('properties', {})
        
        if not event_type:
            return jsonify({'success': False, 'error': 'Event type required'}), 400
        
        business_analytics.track_event(event_type, properties)
        
        return jsonify({
            'success': True,
            'message': 'Event tracked successfully'
        })
    
    @blueprint.route('/kpi/dashboard')
    def kpi_dashboard():
        """Get KPI dashboard"""
        dashboard = business_intelligence.get_kpi_dashboard()
        return jsonify({
            'success': True,
            'data': dashboard
        })
    
    @blueprint.route('/kpi/update', methods=['POST'])
    def update_kpi():
        """Update a KPI value"""
        data = request.get_json()
        kpi_name = data.get('kpi_name')
        value = data.get('value')
        
        if not kpi_name or value is None:
            return jsonify({'success': False, 'error': 'KPI name and value required'}), 400
        
        business_intelligence.update_kpi(kpi_name, value)
        
        return jsonify({
            'success': True,
            'message': f'KPI {kpi_name} updated to {value}'
        })
    
    @blueprint.route('/reports/generate', methods=['POST'])
    def generate_report():
        """Generate a business report"""
        data = request.get_json()
        report_type = data.get('report_type')
        parameters = data.get('parameters', {})
        
        if not report_type:
            return jsonify({'success': False, 'error': 'Report type required'}), 400
        
        report = business_analytics.generate_report(report_type, parameters)
        
        return jsonify({
            'success': True,
            'data': report
        })
    
    return blueprint

# Export the business operations system
__all__ = [
    'BusinessAnalytics', 'business_analytics',
    'BusinessIntelligence', 'business_intelligence',
    'LegalCompliance', 'legal_compliance',
    'create_business_blueprint'
]
