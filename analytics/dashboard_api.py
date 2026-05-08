"""
Dashboard Metrics API for Fikiri Solutions
Provides /api/dashboard/metrics endpoint for frontend dashboard data
"""

import json
import logging
import threading
import time
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify

from core.api_validation import handle_api_errors, create_success_response, create_error_response
from core.secure_sessions import get_current_user_id
from core.database_optimization import db_optimizer
from core.jwt_auth import jwt_required, get_current_user
from core.billing_manager import FikiriBillingManager

logger = logging.getLogger(__name__)
billing_manager = FikiriBillingManager()

# Short TTL cache: pricing tiers rarely change; k6 + dashboards hit this path heavily on single workers.
_industry_pricing_cache: Optional[Tuple[float, Dict[str, Any]]] = None
_industry_pricing_lock = threading.Lock()
_INDUSTRY_PRICING_CACHE_TTL_SEC = 60.0

# Align dashboard lead counts with CRM active list (withdrawn leads retained in DB)
_LEADS_ACTIVE_FILTER = " AND (withdrawn_at IS NULL)"

# Create Blueprint
dashboard_bp = Blueprint('dashboard', __name__, url_prefix='/api/dashboard')


@dashboard_bp.route('', methods=['GET'])
@handle_api_errors
def get_dashboard_index():
    """Stable entrypoint for clients that probe GET /api/dashboard (sub-routes live under this prefix)."""
    user_id = get_current_user_id()
    if not user_id:
        return create_error_response("Authentication required", 401, 'AUTHENTICATION_REQUIRED')
    return create_success_response(
        {
            "endpoints": {
                "metrics": "/api/dashboard/metrics",
                "activity": "/api/dashboard/activity",
                "timeseries": "/api/dashboard/timeseries",
                "services": "/api/dashboard/services",
            },
            "user_id": user_id,
        },
        "Dashboard API",
    )


INDUSTRY_PROMPTS: Dict[str, Dict[str, Any]] = {
    "real_estate": {
        "industry": "real_estate",
        "tone": "professional",
        "focus_areas": ["property listings", "client consultations", "market analysis", "showings scheduling"],
        "tools": ["calendar", "crm", "property_api", "market_data"],
        "pricing_tier": "business"
    },
    "property_management": {
        "industry": "property_management",
        "tone": "professional",
        "focus_areas": ["tenant communication", "maintenance requests", "lease renewals", "rent collection"],
        "tools": ["calendar", "crm", "payment_processor", "maintenance_tracker"],
        "pricing_tier": "growth"
    },
    "construction": {
        "industry": "construction",
        "tone": "professional",
        "focus_areas": ["project quotes", "client communication", "scheduling", "material orders"],
        "tools": ["calendar", "quote_generator", "project_manager", "inventory"],
        "pricing_tier": "growth"
    },
    "legal_services": {
        "industry": "legal_services",
        "tone": "professional",
        "focus_areas": ["client intake", "appointment scheduling", "document management", "case updates"],
        "tools": ["calendar", "crm", "document_storage", "compliance_checker"],
        "pricing_tier": "business"
    },
    "cleaning_services": {
        "industry": "cleaning_services",
        "tone": "friendly",
        "focus_areas": ["service scheduling", "quote requests", "recurring appointments", "customer follow-up"],
        "tools": ["calendar", "quote_generator", "recurring_scheduler", "crm"],
        "pricing_tier": "starter"
    },
    "auto_services": {
        "industry": "auto_services",
        "tone": "friendly",
        "focus_areas": ["appointment booking", "service reminders", "estimate requests", "customer follow-up"],
        "tools": ["calendar", "quote_generator", "reminder_system", "crm"],
        "pricing_tier": "starter"
    },
    "event_planning": {
        "industry": "event_planning",
        "tone": "friendly",
        "focus_areas": ["client consultations", "vendor coordination", "timeline management", "follow-up"],
        "tools": ["calendar", "crm", "project_manager", "vendor_portal"],
        "pricing_tier": "growth"
    },
    "fitness_wellness": {
        "industry": "fitness_wellness",
        "tone": "motivational",
        "focus_areas": ["class scheduling", "membership inquiries", "appointment booking", "wellness tips"],
        "tools": ["calendar", "crm", "class_scheduler", "payment_processor"],
        "pricing_tier": "starter"
    },
    "beauty_spa": {
        "industry": "beauty_spa",
        "tone": "friendly",
        "focus_areas": ["appointment booking", "service inquiries", "reminders", "promotions"],
        "tools": ["calendar", "crm", "reminder_system", "promotion_manager"],
        "pricing_tier": "starter"
    },
    "accounting_consulting": {
        "industry": "accounting_consulting",
        "tone": "professional",
        "focus_areas": ["client onboarding", "appointment scheduling", "document requests", "tax reminders"],
        "tools": ["calendar", "crm", "document_storage", "reminder_system"],
        "pricing_tier": "business"
    },
    "restaurant": {
        "industry": "restaurant",
        "tone": "friendly",
        "focus_areas": ["reservation management", "menu recommendations", "special promotions", "catering inquiries"],
        "tools": ["reservation_system", "menu_api", "promotion_tracker", "crm"],
        "pricing_tier": "growth"
    },
    "medical_practice": {
        "industry": "medical_practice",
        "tone": "professional",
        "focus_areas": ["appointment scheduling", "patient reminders", "HIPAA compliance", "follow-up care"],
        "tools": ["calendar", "patient_portal", "compliance_checker", "reminder_system"],
        "pricing_tier": "business"
    },
    "enterprise_solutions": {
        "industry": "enterprise_solutions",
        "tone": "professional",
        "focus_areas": ["custom workflows", "multi-industry support", "advanced analytics", "white-label options"],
        "tools": ["custom_api", "white_label", "dedicated_support", "advanced_analytics"],
        "pricing_tier": "enterprise"
    },
}

@dashboard_bp.route('/debug', methods=['GET'])
@handle_api_errors
@jwt_required
def debug_dashboard():
    """Debug endpoint to identify dashboard issues"""
    try:
        # Get user from JWT token
        user_data = get_current_user()
        if not user_data:
            return create_error_response("Authentication required", 401, 'AUTHENTICATION_REQUIRED')
        
        user_id = user_data['user_id']
        
        debug_info = {
            'user_id': user_id,
            'user_data': user_data,
            'database_connected': True,
            'queries_tested': []
        }
        
        active_user_pred = db_optimizer.sql_cast_int_eq_one("is_active")

        # Test basic database query
        try:
            user_data_db = db_optimizer.execute_query(
                "SELECT id, email, name, role, business_name, business_email, industry, team_size, is_active, email_verified, created_at, updated_at, last_login, onboarding_completed, onboarding_step, metadata FROM users WHERE id = ? AND "
                + active_user_pred,
                (user_id,)
            )
            debug_info['queries_tested'].append({
                'query': 'users',
                'result_count': len(user_data_db) if user_data_db else 0,
                'success': True
            })
        except Exception as e:
            debug_info['queries_tested'].append({
                'query': 'users',
                'error': str(e),
                'success': False
            })
        
        # Test leads query
        try:
            leads_data = db_optimizer.execute_query(
                "SELECT COUNT(*) as count FROM leads WHERE user_id = ?" + _LEADS_ACTIVE_FILTER,
                (user_id,)
            )
            debug_info['queries_tested'].append({
                'query': 'leads_count',
                'result_count': len(leads_data) if leads_data else 0,
                'success': True
            })
        except Exception as e:
            debug_info['queries_tested'].append({
                'query': 'leads_count',
                'error': str(e),
                'success': False
            })
        
        return create_success_response(debug_info, "Debug information retrieved")
        
    except Exception as e:
        logger.error(f"Debug dashboard error: {e}")
        import traceback
        logger.error(f"Debug dashboard traceback: {traceback.format_exc()}")
        return create_error_response(f"Debug failed: {str(e)}", 500, "DEBUG_ERROR")

@dashboard_bp.route('/metrics', methods=['GET'])
@handle_api_errors
def get_dashboard_metrics():
    """Get dashboard metrics for authenticated user"""
    try:
        # Prefer authenticated user; fall back to query param or demo user
        user_id = get_current_user_id()
        if not user_id:
            # Allow overriding via query param for debugging, else default to demo user
            user_id = request.args.get('user_id', type=int) or 1
        
        # Default user metadata (used if we can't load from DB)
        user_data = {'user_id': user_id, 'name': 'User', 'email': ''}
        
        # Initialize default metrics
        metrics_data = {
            'user': {
                'id': user_id,
                'name': user_data.get('name', 'User'),
                'email': user_data.get('email', ''),
                'onboarding_completed': False,
                'onboarding_step': 1
            },
            'leads': {
                'total': 0,
                'recent': 0,
                'growth_rate': 0
            },
            'email': {
                'total_emails': 0,
                'unread_emails': 0,
                'emails_today': 0,
                'last_email': None
            },
            'automation': {
                'total_automations': 0,
                'active_automations': 0,
                'automations_executed_today': 0,
                'last_execution': None
            },
            'integrations': {
                'gmail_connected': False,
                'crm_synced': True,
                'analytics_enabled': True
            },
            'performance': {
                'response_time': '2.3s',
                'uptime': '99.9%',
                'last_sync': datetime.now().isoformat()
            },
            'ai': {'total': 0},
            'timestamp': datetime.now().isoformat()
        }
        
        # Try to get user data from database
        try:
            active_user_pred = db_optimizer.sql_cast_int_eq_one("is_active")
            user_data_db = db_optimizer.execute_query(
                "SELECT id, email, name, role, business_name, business_email, industry, team_size, is_active, email_verified, created_at, updated_at, last_login, onboarding_completed, onboarding_step, metadata FROM users WHERE id = ? AND "
                + active_user_pred,
                (user_id,)
            )
            
            if user_data_db and len(user_data_db) > 0:
                user = user_data_db[0]
                # Handle SQLite Row objects by converting to dict
                if hasattr(user, 'keys'):
                    user_dict = dict(user)
                else:
                    user_dict = user if isinstance(user, dict) else {}
                
                # Update metrics with user data
                metrics_data['user'].update({
                    'name': user_dict.get('name', user_data.get('name', 'User')),
                    'email': user_dict.get('email', user_data.get('email', '')),
                    'onboarding_completed': user_dict.get('onboarding_completed', False),
                    'onboarding_step': user_dict.get('onboarding_step', 1)
                })
        except Exception as e:
            logger.warning(f"Could not get user data: {e}")
        
        # Try to get leads count
        try:
            leads_data = db_optimizer.execute_query(
                "SELECT COUNT(*) as count FROM leads WHERE user_id = ?" + _LEADS_ACTIVE_FILTER,
                (user_id,)
            )
            if leads_data and len(leads_data) > 0:
                lead_row = leads_data[0]
                if hasattr(lead_row, 'keys'):
                    lead_dict = dict(lead_row)
                    metrics_data['leads']['total'] = lead_dict.get('count', 0)
                else:
                    metrics_data['leads']['total'] = lead_row.get('count', 0) if isinstance(lead_row, dict) else 0
        except Exception as e:
            logger.warning(f"Could not get leads count: {e}")
        
        # Try to get recent leads
        try:
            recent_pred = db_optimizer.sql_column_newer_than_n_days_ago("created_at", 7)
            recent_leads_data = db_optimizer.execute_query(
                "SELECT COUNT(*) as count FROM leads WHERE user_id = ?"
                + _LEADS_ACTIVE_FILTER
                + f" AND {recent_pred}",
                (user_id,),
            )
            if recent_leads_data and len(recent_leads_data) > 0:
                recent_row = recent_leads_data[0]
                if hasattr(recent_row, 'keys'):
                    recent_dict = dict(recent_row)
                    metrics_data['leads']['recent'] = recent_dict.get('count', 0)
                else:
                    metrics_data['leads']['recent'] = recent_row.get('count', 0) if isinstance(recent_row, dict) else 0
        except Exception as e:
            logger.warning(f"Could not get recent leads: {e}")
        
        # Try to check Gmail connection using canonical gmail_tokens table
        try:
            active_token_pred = db_optimizer.sql_cast_int_eq_one("is_active")
            gmail_token_rows = db_optimizer.execute_query(
                """
                SELECT access_token_enc, access_token, is_active, expiry_timestamp
                FROM gmail_tokens
                WHERE user_id = ? AND """
                + active_token_pred
                + """
                ORDER BY updated_at DESC
                LIMIT 1
                """,
                (user_id,),
            )
            if gmail_token_rows and len(gmail_token_rows) > 0:
                row = gmail_token_rows[0]
                if isinstance(row, dict):
                    has_token = bool(row.get('access_token_enc') or row.get('access_token'))
                    expiry_ts = row.get('expiry_timestamp')
                else:
                    # Fallback if row is a tuple
                    has_token = bool(row[0] or (len(row) > 1 and row[1]))
                    expiry_ts = row[3] if len(row) > 3 else None

                is_expired = False
                if expiry_ts:
                    try:
                        now_ts = int(datetime.utcnow().timestamp())
                        expiry_int = int(expiry_ts)
                        is_expired = expiry_int <= now_ts
                    except Exception:
                        is_expired = False

                metrics_data['integrations']['gmail_connected'] = bool(has_token and not is_expired)
        except Exception as e:
            logger.warning(f"Could not check Gmail connection from gmail_tokens: {e}")
        
        # Try to get AI response count from analytics_events
        try:
            ai_result = db_optimizer.execute_query(
                """SELECT COUNT(*) as count FROM analytics_events
                   WHERE user_id = ? AND (event_type LIKE '%ai%' OR event_type LIKE '%llm%' OR event_type LIKE '%response%')""",
                (user_id,)
            )
            if ai_result and len(ai_result) > 0:
                row = ai_result[0]
                count = row.get('count', 0) if isinstance(row, dict) else (getattr(row, 'count', 0) if hasattr(row, 'count') else 0)
                metrics_data['ai'] = {'total': count}
        except Exception as e:
            logger.warning(f"Could not get AI metrics: {e}")
        
        return create_success_response(metrics_data, "Dashboard metrics retrieved")
        
    except Exception as e:
        logger.error(f"Dashboard metrics error: {e}")
        import traceback
        logger.error(f"Dashboard metrics traceback: {traceback.format_exc()}")
        return create_error_response(f"Failed to get dashboard metrics: {str(e)}", 500, "DASHBOARD_ERROR")

@dashboard_bp.route('/activity', methods=['GET'])
@handle_api_errors
def get_dashboard_activity():
    """Get recent activity for dashboard"""
    try:
        # Get user ID from session
        user_id = get_current_user_id()
        if not user_id:
            return create_error_response("Authentication required", 401, 'AUTHENTICATION_REQUIRED')

        limit = request.args.get('limit', 10, type=int)
        if limit < 1:
            limit = 1
        if limit > 50:
            limit = 50

        activities_query = """
            SELECT la.id, la.activity_type, la.description, la.timestamp, la.metadata,
                   l.name as lead_name, l.email as lead_email
              FROM lead_activities la
              JOIN leads l ON l.id = la.lead_id
             WHERE l.user_id = ?
             ORDER BY la.timestamp DESC
             LIMIT ?
        """
        activities_data = db_optimizer.execute_query(activities_query, (user_id, limit))

        def map_type(activity_type: str) -> str:
            if not activity_type:
                return 'lead'
            activity_type = activity_type.lower()
            if activity_type in ('email_received', 'email_sent'):
                return 'email'
            if activity_type in ('follow_up', 'automation'):
                return 'automation'
            if 'error' in activity_type or 'fail' in activity_type:
                return 'error'
            return 'lead'

        activity_items = []
        for row in activities_data or []:
            activity_type = row.get('activity_type') if isinstance(row, dict) else None
            mapped_type = map_type(activity_type or '')
            description = row.get('description') if isinstance(row, dict) else None
            lead_name = row.get('lead_name') if isinstance(row, dict) else None
            lead_email = row.get('lead_email') if isinstance(row, dict) else None
            meta_raw = row.get('metadata') if isinstance(row, dict) else None
            metadata = {}
            if meta_raw:
                try:
                    metadata = json.loads(meta_raw) if isinstance(meta_raw, str) else meta_raw
                except Exception:
                    metadata = {}

            if not description:
                target = lead_name or lead_email or 'lead'
                if activity_type == 'email_received':
                    description = f"Email received from {target}"
                elif activity_type == 'email_sent':
                    description = f"Email sent to {target}"
                elif mapped_type == 'automation':
                    description = f"Automation activity for {target}"
                else:
                    description = f"Lead activity for {target}"

            timestamp = row.get('timestamp') if isinstance(row, dict) else None
            if isinstance(timestamp, datetime):
                timestamp = timestamp.isoformat()

            status = metadata.get('status') if isinstance(metadata, dict) else None
            if not status:
                status = 'error' if mapped_type == 'error' else 'success'

            activity_items.append({
                'id': row.get('id') if isinstance(row, dict) else None,
                'type': mapped_type,
                'message': description,
                'timestamp': timestamp or datetime.now().isoformat(),
                'status': status
            })

        analytics_query = """
            SELECT id, event_type, event_data, created_at
              FROM analytics_events
             WHERE user_id = ?
             ORDER BY created_at DESC
             LIMIT ?
        """
        analytics_data = db_optimizer.execute_query(analytics_query, (user_id, limit))

        def map_event_type(event_type: str) -> str:
            if not event_type:
                return 'lead'
            event_type = event_type.lower()
            if 'email' in event_type:
                return 'email'
            if 'automation' in event_type:
                return 'automation'
            if 'error' in event_type or 'fail' in event_type:
                return 'error'
            if 'service' in event_type or 'settings' in event_type or 'profile' in event_type or 'api_key' in event_type:
                return 'lead'
            return 'lead'

        for row in analytics_data or []:
            event_type = row.get('event_type') if isinstance(row, dict) else None
            mapped_type = map_event_type(event_type or '')
            event_data_raw = row.get('event_data') if isinstance(row, dict) else None
            event_data = {}
            if event_data_raw:
                try:
                    event_data = json.loads(event_data_raw) if isinstance(event_data_raw, str) else event_data_raw
                except Exception:
                    event_data = {}
            message = event_data.get('message')
            if not message:
                message = (event_type or 'Account activity').replace('_', ' ').title()
            created_at = row.get('created_at') if isinstance(row, dict) else None
            if isinstance(created_at, datetime):
                created_at = created_at.isoformat()
            status = event_data.get('status', 'success')

            activity_items.append({
                'id': row.get('id') if isinstance(row, dict) else None,
                'type': mapped_type,
                'message': message,
                'timestamp': created_at or datetime.now().isoformat(),
                'status': status
            })

        activity_items.sort(key=lambda item: item.get('timestamp', ''), reverse=True)
        activity_items = activity_items[:limit]

        return create_success_response({'activities': activity_items}, "Activity data retrieved")
        
    except Exception as e:
        logger.error(f"Dashboard activity error: {e}")
        return create_error_response("Failed to get activity data", 500, "ACTIVITY_ERROR")

@dashboard_bp.route('/services', methods=['GET'])
@handle_api_errors
def get_dashboard_services():
    """Get service status for dashboard"""
    try:
        # Get user ID from session
        user_id = get_current_user_id()
        if not user_id:
            return create_error_response("Authentication required", 401, 'AUTHENTICATION_REQUIRED')
        
        # Mock service status data
        services_data = [
            {
                'name': 'Email Parser',
                'status': 'active',
                'uptime': '99.9%',
                'last_check': datetime.now().isoformat()
            },
            {
                'name': 'CRM Integration',
                'status': 'active',
                'uptime': '100%',
                'last_check': datetime.now().isoformat()
            },
            {
                'name': 'AI Assistant',
                'status': 'active',
                'uptime': '99.8%',
                'last_check': datetime.now().isoformat()
            },
            {
                'name': 'Automation Engine',
                'status': 'active',
                'uptime': '99.9%',
                'last_check': datetime.now().isoformat()
            }
        ]
        
        return create_success_response({'services': services_data}, "Service status retrieved")
        
    except Exception as e:
        logger.error(f"Dashboard services error: {e}")
        return create_error_response("Failed to get service status", 500, "SERVICES_ERROR")

@dashboard_bp.route('/test', methods=['GET'])
def test_dashboard():
    """Simple test endpoint"""
    return jsonify({'success': True, 'message': 'Dashboard blueprint is working'})

@dashboard_bp.route('/kpi', methods=['GET'])
@handle_api_errors
def get_dashboard_kpi():
    """Get business KPI data for dashboard"""
    try:
        # Return sample KPI data
        kpi_data = {
            'success': True,
            'data': {
                'revenue': {
                    'current': 125000,
                    'previous': 98000,
                    'change': 27.5,
                    'trend': 'up'
                },
                'leads': {
                    'current': 45,
                    'previous': 32,
                    'change': 40.6,
                    'trend': 'up'
                },
                'conversion': {
                    'current': 12.5,
                    'previous': 9.8,
                    'change': 27.5,
                    'trend': 'up'
                },
                'emails_processed': {
                    'current': 1250,
                    'previous': 980,
                    'change': 27.5,
                    'trend': 'up'
                }
            },
            'message': 'KPI data retrieved successfully'
        }
        
        return jsonify(kpi_data)
        
    except Exception as e:
        logger.error(f"KPI dashboard error: {e}")
        return create_error_response(f"KPI failed: {str(e)}", 500, "KPI_ERROR")

@dashboard_bp.route('/timeseries', methods=['GET'])
@handle_api_errors
def get_dashboard_timeseries():
    """Get dashboard timeseries data backed by DB aggregates."""
    try:
        user_id = get_current_user_id() or request.args.get('user_id', type=int) or 1
        period = request.args.get('period', 'week', type=str)

        period_days = {
            'week': 7,
            'month': 30,
            'quarter': 90,
        }.get(period, 7)

        today = datetime.utcnow().date()
        start_date = today - timedelta(days=period_days - 1)
        previous_start = start_date - timedelta(days=period_days)
        previous_end = start_date - timedelta(days=1)

        def _rows_to_daily_map(rows: Optional[List[Dict[str, Any]]]) -> Dict[str, float]:
            mapped: Dict[str, float] = {}
            for row in rows or []:
                day = row.get('day') if isinstance(row, dict) else None
                value = row.get('value') if isinstance(row, dict) else 0
                if day:
                    mapped[str(day)] = float(value or 0)
            return mapped

        leads_daily = _rows_to_daily_map(db_optimizer.execute_query(
            """
            SELECT DATE(created_at) AS day, COUNT(*) AS value
            FROM leads
            WHERE user_id = ? AND DATE(created_at) >= ? AND (withdrawn_at IS NULL)
            GROUP BY DATE(created_at)
            """,
            (user_id, start_date.isoformat())
        ))

        emails_daily = _rows_to_daily_map(db_optimizer.execute_query(
            """
            SELECT DATE(date) AS day, COUNT(*) AS value
            FROM synced_emails
            WHERE user_id = ? AND DATE(date) >= ?
            GROUP BY DATE(date)
            """,
            (user_id, start_date.isoformat())
        ))

        responses_daily = _rows_to_daily_map(db_optimizer.execute_query(
            """
            SELECT DATE(created_at) AS day, COUNT(*) AS value
            FROM analytics_events
            WHERE user_id = ? AND DATE(created_at) >= ?
              AND (event_type LIKE '%ai%' OR event_type LIKE '%llm%' OR event_type LIKE '%response%')
            GROUP BY DATE(created_at)
            """,
            (user_id, start_date.isoformat())
        ))

        revenue_daily = _rows_to_daily_map(db_optimizer.execute_query(
            """
            SELECT DATE(revenue_date) AS day, COALESCE(SUM(amount), 0) AS value
            FROM revenue_tracking
            WHERE user_id = ? AND DATE(revenue_date) >= ?
            GROUP BY DATE(revenue_date)
            """,
            (user_id, start_date.isoformat())
        ))

        timeseries = []
        for i in range(period_days):
            day = start_date + timedelta(days=i)
            day_key = day.isoformat()
            timeseries.append({
                "day": day_key,
                "leads": int(leads_daily.get(day_key, 0)),
                "emails": int(emails_daily.get(day_key, 0)),
                "responses": int(responses_daily.get(day_key, 0)),
                "revenue": round(float(revenue_daily.get(day_key, 0.0)), 2),
            })

        def _range_total(query: str, params: tuple) -> float:
            result = db_optimizer.execute_query(query, params)
            if not result:
                return 0.0
            row = result[0]
            if isinstance(row, dict):
                return float(row.get('value', 0) or 0)
            return 0.0

        def _change(cur: float, prev: float) -> Dict[str, Any]:
            if prev <= 0:
                return {"change_pct": None, "positive": cur >= prev}
            pct = ((cur - prev) / prev) * 100
            return {"change_pct": round(pct, 1), "positive": pct >= 0}

        range_params_current = (user_id, start_date.isoformat(), today.isoformat())
        range_params_previous = (user_id, previous_start.isoformat(), previous_end.isoformat())

        current_leads = _range_total(
            "SELECT COUNT(*) AS value FROM leads WHERE user_id = ? AND DATE(created_at) BETWEEN ? AND ?"
            + _LEADS_ACTIVE_FILTER,
            range_params_current
        )
        previous_leads = _range_total(
            "SELECT COUNT(*) AS value FROM leads WHERE user_id = ? AND DATE(created_at) BETWEEN ? AND ?"
            + _LEADS_ACTIVE_FILTER,
            range_params_previous
        )
        current_emails = _range_total(
            "SELECT COUNT(*) AS value FROM synced_emails WHERE user_id = ? AND DATE(date) BETWEEN ? AND ?",
            range_params_current
        )
        previous_emails = _range_total(
            "SELECT COUNT(*) AS value FROM synced_emails WHERE user_id = ? AND DATE(date) BETWEEN ? AND ?",
            range_params_previous
        )
        current_responses = _range_total(
            """
            SELECT COUNT(*) AS value
            FROM analytics_events
            WHERE user_id = ? AND DATE(created_at) BETWEEN ? AND ?
              AND (event_type LIKE '%ai%' OR event_type LIKE '%llm%' OR event_type LIKE '%response%')
            """,
            range_params_current
        )
        previous_responses = _range_total(
            """
            SELECT COUNT(*) AS value
            FROM analytics_events
            WHERE user_id = ? AND DATE(created_at) BETWEEN ? AND ?
              AND (event_type LIKE '%ai%' OR event_type LIKE '%llm%' OR event_type LIKE '%response%')
            """,
            range_params_previous
        )
        current_revenue = _range_total(
            "SELECT COALESCE(SUM(amount), 0) AS value FROM revenue_tracking WHERE user_id = ? AND DATE(revenue_date) BETWEEN ? AND ?",
            range_params_current
        )
        previous_revenue = _range_total(
            "SELECT COALESCE(SUM(amount), 0) AS value FROM revenue_tracking WHERE user_id = ? AND DATE(revenue_date) BETWEEN ? AND ?",
            range_params_previous
        )

        return create_success_response({
            "timeseries": timeseries,
            "summary": {
                "leads": _change(current_leads, previous_leads),
                "emails": _change(current_emails, previous_emails),
                "responses": _change(current_responses, previous_responses),
                "revenue": _change(current_revenue, previous_revenue),
            }
        })
    except Exception as e:
        logger.error(f"Dashboard timeseries error: {e}")
        import traceback
        logger.error(f"Dashboard timeseries traceback: {traceback.format_exc()}")
        return create_error_response(f"Failed to fetch dashboard data: {str(e)}", 500, 'DASHBOARD_TIMESERIES_ERROR')

@dashboard_bp.route('/industry/prompts', methods=['GET'])
@handle_api_errors
def get_industry_prompts():
    """Get industry prompt configuration used by IndustryAutomation page."""
    return create_success_response({"prompts": INDUSTRY_PROMPTS}, "Industry prompts retrieved")

@dashboard_bp.route('/industry/pricing', methods=['GET'])
@handle_api_errors
def get_industry_pricing():
    """Get pricing tiers for industry automation UI."""
    global _industry_pricing_cache
    now = time.monotonic()
    with _industry_pricing_lock:
        cached = _industry_pricing_cache
        if cached is not None and (now - cached[0]) < _INDUSTRY_PRICING_CACHE_TTL_SEC:
            return create_success_response({"pricing_tiers": cached[1]}, "Industry pricing retrieved")
    try:
        tiers = billing_manager.get_pricing_tiers()
        pricing = {}
        for tier_key, tier_data in tiers.items():
            limits = tier_data.get('limits', {})
            pricing[tier_key] = {
                "name": tier_data.get('name', tier_key.title()),
                "price": tier_data.get('monthly_price', 0),
                "responses_limit": limits.get('ai_responses', 0),
                "features": tier_data.get('features', []),
            }
        with _industry_pricing_lock:
            _industry_pricing_cache = (time.monotonic(), pricing)
        return create_success_response({"pricing_tiers": pricing}, "Industry pricing retrieved")
    except Exception as e:
        logger.error("Industry pricing error: %s", e)
        return create_error_response("Failed to load pricing tiers", 500, "INDUSTRY_PRICING_ERROR")

@dashboard_bp.route('/industry/usage', methods=['GET'])
@handle_api_errors
def get_industry_usage():
    """Get usage analytics for industry automation UI."""
    try:
        user_id = get_current_user_id() or request.args.get('user_id', type=int) or 1
        month_start = datetime.utcnow().strftime('%Y-%m-01')
        month_key = datetime.utcnow().strftime('%Y-%m')

        tier = "starter"
        monthly_cost = 49.0
        try:
            sub_rows = db_optimizer.execute_query(
                "SELECT tier FROM subscriptions WHERE user_id = ? ORDER BY current_period_end DESC, updated_at DESC LIMIT 1",
                (user_id,)
            )
            if sub_rows:
                tier = (sub_rows[0].get('tier') or tier).lower()
        except Exception:
            pass

        pricing_tiers = billing_manager.get_pricing_tiers()
        if tier in pricing_tiers:
            monthly_cost = float(pricing_tiers[tier].get('monthly_price', monthly_cost) or monthly_cost)

        usage_rows = db_optimizer.execute_query(
            """
            SELECT usage_type, SUM(quantity) AS total
            FROM billing_usage
            WHERE user_id = ? AND month = ?
            GROUP BY usage_type
            """,
            (user_id, month_key)
        )
        usage_map: Dict[str, int] = {}
        for row in usage_rows or []:
            usage_type = row.get('usage_type') if isinstance(row, dict) else None
            total = row.get('total') if isinstance(row, dict) else 0
            if usage_type:
                usage_map[usage_type] = int(total or 0)

        responses = usage_map.get('ai_responses', 0)
        if responses == 0:
            ai_rows = db_optimizer.execute_query(
                """
                SELECT COUNT(*) AS value
                FROM analytics_events
                WHERE user_id = ? AND DATE(created_at) >= DATE(?)
                  AND (event_type LIKE '%ai%' OR event_type LIKE '%llm%' OR event_type LIKE '%response%')
                """,
                (user_id, month_start)
            )
            responses = int((ai_rows[0].get('value') if ai_rows else 0) or 0)

        tool_calls_rows = db_optimizer.execute_query(
            "SELECT COUNT(*) AS value FROM automation_executions WHERE user_id = ? AND DATE(executed_at) >= DATE(?)",
            (user_id, month_start)
        )
        tokens = responses * 120
        tool_calls = int((tool_calls_rows[0].get('value') if tool_calls_rows else 0) or 0)

        return create_success_response({
            "usage": {
                "tier": tier,
                "responses": responses,
                "tool_calls": tool_calls,
                "tokens": tokens,
                "monthly_cost": monthly_cost,
            }
        }, "Industry usage retrieved")
    except Exception as e:
        logger.error("Industry usage error: %s", e)
        return create_error_response("Failed to load usage analytics", 500, "INDUSTRY_USAGE_ERROR")

@dashboard_bp.route('/emails', methods=['GET'])
@handle_api_errors
def get_email_metrics():
    """Get email metrics for analytics dashboard"""
    try:
        user_id = get_current_user_id()
        if not user_id:
            user_id = request.args.get('user_id', type=int) or 1
        
        period = request.args.get('period', 'week', type=str)
        
        # Calculate date range based on period
        if period == 'day':
            days = 1
        elif period == 'week':
            days = 7
        elif period == 'month':
            days = 30
        else:
            days = 7
        
        start_date = datetime.now() - timedelta(days=days)
        
        # Get email counts from synced_emails table (column is 'date', not 'received_date')
        try:
            total_result = db_optimizer.execute_query("""
                SELECT COUNT(*) as count 
                FROM synced_emails 
                WHERE user_id = ? AND date >= ?
            """, (user_id, start_date.isoformat()))
            
            total_emails = total_result[0]['count'] if total_result and len(total_result) > 0 else 0
        except Exception as e:
            logger.warning(f"Could not get total email metrics from database: {e}")
            total_emails = 0

        try:
            unread_result = db_optimizer.execute_query("""
                SELECT COUNT(*) as count 
                FROM synced_emails 
                WHERE user_id = ? AND date >= ? AND is_read = FALSE
            """, (user_id, start_date.isoformat()))
            unread_emails = unread_result[0]['count'] if unread_result and len(unread_result) > 0 else 0
        except Exception as e:
            logger.debug("Unread email count not available (is_read column may be missing): %s", e)
            unread_emails = 0
        
        # Get email trends (daily breakdown)
        trends = []
        for i in range(days):
            day = start_date + timedelta(days=i)
            day_start = day.replace(hour=0, minute=0, second=0, microsecond=0)
            day_end = day_start + timedelta(days=1)
            
            try:
                day_result = db_optimizer.execute_query("""
                    SELECT COUNT(*) as count 
                    FROM synced_emails 
                    WHERE user_id = ? AND date >= ? AND date < ?
                """, (user_id, day_start.isoformat(), day_end.isoformat()))
                
                count = day_result[0]['count'] if day_result and len(day_result) > 0 else 0
            except Exception as day_error:
                logger.debug("Email trends query failed for %s: %s", day_start.date(), day_error)
                count = 0
            
            trends.append({
                'date': day_start.strftime('%Y-%m-%d'),
                'count': count
            })
        
        return create_success_response({
            'total_emails': total_emails,
            'unread_emails': unread_emails,
            'period': period,
            'trends': trends,
            'timestamp': datetime.now().isoformat()
        }, 'Email metrics retrieved successfully')
        
    except Exception as e:
        logger.error(f"Email metrics error: {e}")
        import traceback
        logger.error(f"Email metrics traceback: {traceback.format_exc()}")
        return create_error_response(f"Failed to get email metrics: {str(e)}", 500, 'EMAIL_METRICS_ERROR')

@dashboard_bp.route('/ai', methods=['GET'])
@handle_api_errors
def get_ai_metrics():
    """Get AI usage metrics for analytics dashboard"""
    try:
        user_id = get_current_user_id()
        if not user_id:
            user_id = request.args.get('user_id', type=int) or 1
        
        # Get AI usage from analytics_events table
        try:
            # Count AI responses/actions
            ai_events_result = db_optimizer.execute_query("""
                SELECT COUNT(*) as count 
                FROM analytics_events 
                WHERE user_id = ? AND event_type LIKE '%ai%' OR event_type LIKE '%llm%' OR event_type LIKE '%response%'
            """, (user_id,))
            
            total_responses = ai_events_result[0]['count'] if ai_events_result and len(ai_events_result) > 0 else 0
            
            # Get recent AI activity (last 7 days)
            week_ago = datetime.now() - timedelta(days=7)
            recent_result = db_optimizer.execute_query("""
                SELECT COUNT(*) as count 
                FROM analytics_events 
                WHERE user_id = ? AND created_at >= ? 
                AND (event_type LIKE '%ai%' OR event_type LIKE '%llm%' OR event_type LIKE '%response%')
            """, (user_id, week_ago.isoformat()))
            
            recent_responses = recent_result[0]['count'] if recent_result and len(recent_result) > 0 else 0
            
        except Exception as e:
            logger.warning(f"Could not get AI metrics from database: {e}")
            total_responses = 0
            recent_responses = 0
        
        return create_success_response({
            'total_responses': total_responses,
            'recent_responses': recent_responses,
            'last_7_days': recent_responses,
            'timestamp': datetime.now().isoformat()
        }, 'AI metrics retrieved successfully')
        
    except Exception as e:
        logger.error(f"AI metrics error: {e}")
        import traceback
        logger.error(f"AI metrics traceback: {traceback.format_exc()}")
        return create_error_response(f"Failed to get AI metrics: {str(e)}", 500, 'AI_METRICS_ERROR')
