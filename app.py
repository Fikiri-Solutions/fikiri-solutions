#!/usr/bin/env python3
"""
Fikiri Solutions - Flask Web Application
Web interface for testing and deploying Fikiri services.
"""

from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from flask_cors import CORS
from flask_socketio import SocketIO, emit
import json
import os
import time
from datetime import datetime
from pathlib import Path

# Import our core services
from core.minimal_config import get_config
from core.minimal_auth import MinimalAuthenticator
from core.minimal_email_parser import MinimalEmailParser
from core.minimal_gmail_utils import MinimalGmailService
from core.minimal_email_actions import MinimalEmailActions
from core.minimal_crm_service import MinimalCRMService
from core.minimal_ai_assistant import MinimalAIEmailAssistant
from core.minimal_ml_scoring import MinimalMLScoring
from core.minimal_vector_search import MinimalVectorSearch
# from core.strategic_hybrid_service import StrategicHybridService  # Removed - causing issues
from core.feature_flags import get_feature_flags
from core.email_service_manager import EmailServiceManager

# Import enterprise features
from core.enterprise_logging import log_api_request, log_service_action, log_security_event
from core.enterprise_security import security_manager, UserRole, Permission

# Import monitoring and performance tracking
from core.structured_logging import logger, monitor, error_handler, performance_monitor
from core.performance_monitoring import monitor_performance, PerformanceBudget

# Lightweight TensorFlow feature flag - make it optional, never a blocker
# TensorFlow removed to avoid compatibility issues - using lightweight alternatives
TENSORFLOW_ENABLED = False
print("ℹ️  Using lightweight alternatives (TensorFlow disabled for compatibility)")

# Initialize Flask app
app = Flask(__name__)
CORS(app, origins=[
    'http://localhost:3000',  # Local development
    'https://fikirisolutions.vercel.app',  # Vercel deployment
    'https://fikirisolutions.com',  # Custom domain
    'https://www.fikirisolutions.com'  # Custom domain with www
])

# Initialize SocketIO for real-time updates
socketio = SocketIO(app, cors_allowed_origins=[
    'http://localhost:3000',
    'https://fikirisolutions.vercel.app',
    'https://fikirisolutions.com',
    'https://www.fikirisolutions.com'
])
app.secret_key = 'fikiri-secret-key-2024'

# Global service instances
services = {
    'config': None,
    'auth': None,
    'parser': None,
    'gmail': None,
    'actions': None,
    'crm': None,
    'ai_assistant': None,
    'ml_scoring': None,
    'vector_search': None,
    'hybrid': None,  # Removed - causing issues
    'feature_flags': None,
    'email_manager': None
}

def initialize_services():
    """Initialize all services."""
    global services
    
    try:
        services['config'] = get_config()
        services['auth'] = MinimalAuthenticator()
        services['parser'] = MinimalEmailParser()
        services['gmail'] = MinimalGmailService()
        services['actions'] = MinimalEmailActions()
        services['crm'] = MinimalCRMService()
        services['ai_assistant'] = MinimalAIEmailAssistant()
        services['ml_scoring'] = MinimalMLScoring()
        services['vector_search'] = MinimalVectorSearch()
        # services['hybrid'] = StrategicHybridService()  # Removed - causing issues
        services['feature_flags'] = get_feature_flags()
        services['email_manager'] = EmailServiceManager()
        
        print("✅ All services initialized successfully")
        return True
    except Exception as e:
        print(f"❌ Error initializing services: {e}")
        return False

# Initialize services on startup
initialize_services()

# Add request logging middleware
@app.before_request
def log_request():
    """Log all incoming requests."""
    request.start_time = time.time()

@app.after_request
def log_response(response):
    """Log all outgoing responses."""
    if hasattr(request, 'start_time'):
        response_time = time.time() - request.start_time
        log_api_request(
            endpoint=request.endpoint or request.path,
            method=request.method,
            status_code=response.status_code,
            response_time=response_time,
            user_agent=request.headers.get('User-Agent')
        )
    return response

# Add security endpoints
@app.route('/api/auth/login', methods=['POST'])
def api_login():
    """User login endpoint."""
    try:
        data = request.get_json()
        email = data.get('email')
        password = data.get('password')  # In production, use proper password hashing
        
        # For demo purposes, accept any password
        user = security_manager.authenticate_user(email, password)
        
        if user:
            session_obj = security_manager.create_session(
                user, 
                request.remote_addr, 
                request.headers.get('User-Agent', '')
            )
            
            session['session_id'] = session_obj.session_id
            session['user_id'] = user.id
            
            log_security_event(
                event_type="user_login",
                severity="info",
                details={"user_id": user.id, "email": user.email}
            )
            
            return jsonify({
                'success': True,
                'user': {
                    'id': user.id,
                    'email': user.email,
                    'name': user.name,
                    'role': user.role.value
                },
                'session_id': session_obj.session_id
            })
        else:
            log_security_event(
                event_type="failed_login",
                severity="warning",
                details={"email": email, "ip": request.remote_addr}
            )
            return jsonify({'success': False, 'error': 'Invalid credentials'}), 401
            
    except Exception as e:
        log_security_event(
            event_type="login_error",
            severity="error",
            details={"error": str(e)}
        )
        return jsonify({'error': str(e)}), 500

@app.route('/api/auth/logout', methods=['POST'])
def api_logout():
    """User logout endpoint."""
    try:
        session_id = session.get('session_id')
        if session_id:
            security_manager.revoke_session(session_id)
            session.clear()
            
            log_security_event(
                event_type="user_logout",
                severity="info",
                details={"session_id": session_id}
            )
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/auth/status')
def api_auth_status():
    """Check authentication status."""
    try:
        session_id = session.get('session_id')
        if session_id:
            session_obj = security_manager.validate_session(session_id)
            if session_obj:
                user = security_manager.get_user_by_id(session_obj.user_id)
                if user:
                    return jsonify({
                        'authenticated': True,
                        'user': {
                            'id': user.id,
                            'email': user.email,
                            'name': user.name,
                            'role': user.role.value
                        }
                    })
        
        return jsonify({'authenticated': False})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/users')
def api_admin_users():
    """Admin endpoint to list users."""
    try:
        session_id = session.get('session_id')
        if not session_id:
            return jsonify({'error': 'Authentication required'}), 401
        
        session_obj = security_manager.validate_session(session_id)
        if not session_obj:
            return jsonify({'error': 'Invalid session'}), 401
        
        user = security_manager.get_user_by_id(session_obj.user_id)
        if not user or not security_manager.check_permission(user, Permission.MANAGE_USERS):
            return jsonify({'error': 'Permission denied'}), 403
        
        users = security_manager.list_users()
        return jsonify({
            'users': [
                {
                    'id': u.id,
                    'email': u.email,
                    'name': u.name,
                    'role': u.role.value,
                    'is_active': u.is_active,
                    'created_at': u.created_at,
                    'last_login': u.last_login
                }
                for u in users
            ]
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/security-stats')
def api_admin_security_stats():
    """Admin endpoint for security statistics."""
    try:
        session_id = session.get('session_id')
        if not session_id:
            return jsonify({'error': 'Authentication required'}), 401
        
        session_obj = security_manager.validate_session(session_id)
        if not session_obj:
            return jsonify({'error': 'Invalid session'}), 401
        
        user = security_manager.get_user_by_id(session_obj.user_id)
        if not user or not security_manager.check_permission(user, Permission.SYSTEM_CONFIG):
            return jsonify({'error': 'Permission denied'}), 403
        
        stats = security_manager.get_security_stats()
        return jsonify(stats)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/')
def index():
    """Main dashboard page."""
    return render_template('dashboard.html')

@app.route('/api/health-old')
def api_health_old():
    """Comprehensive health check endpoint for system monitoring."""
    try:
        health_status = {
            'timestamp': datetime.now().isoformat(),
            'status': 'healthy',
            'version': '1.0.0',
            'uptime': 'running',
            'checks': {
                'gmail_auth': {'status': 'unknown', 'details': ''},
                'vector_db': {'status': 'unknown', 'details': ''},
                'crm_leads': {'status': 'unknown', 'details': ''},
                'openai_key': {'status': 'unknown', 'details': ''},
                'services': {'status': 'unknown', 'details': ''},
                'feature_flags': {'status': 'unknown', 'details': ''}
            },
            'metrics': {
                'total_services': len(services),
                'initialized_services': 0,
                'authenticated_services': 0,
                'enabled_features': 0
            }
        }
        
        # Check Gmail Authentication
        try:
            if services['auth'] and services['auth'].is_authenticated():
                health_status['checks']['gmail_auth'] = {
                    'status': 'healthy',
                    'details': 'Gmail OAuth authenticated successfully'
                }
            else:
                health_status['checks']['gmail_auth'] = {
                    'status': 'unhealthy',
                    'details': 'Gmail authentication required'
                }
        except Exception as e:
            health_status['checks']['gmail_auth'] = {
                'status': 'error',
                'details': f'Gmail auth check failed: {str(e)}'
            }
        
        # Check Vector DB
        try:
            if services['vector_search']:
                stats = services['vector_search'].get_stats()
                if stats.get('document_count', 0) > 0:
                    health_status['checks']['vector_db'] = {
                        'status': 'healthy',
                        'details': f'Vector DB loaded with {stats["document_count"]} documents'
                    }
                else:
                    health_status['checks']['vector_db'] = {
                        'status': 'warning',
                        'details': 'Vector DB initialized but no documents loaded'
                    }
            else:
                health_status['checks']['vector_db'] = {
                    'status': 'unhealthy',
                    'details': 'Vector search service not initialized'
                }
        except Exception as e:
            health_status['checks']['vector_db'] = {
                'status': 'error',
                'details': f'Vector DB check failed: {str(e)}'
            }
        
        # Check CRM Leads
        try:
            if services['crm']:
                stats = services['crm'].get_lead_stats()
                lead_count = stats.get('total_leads', 0)
                if lead_count > 0:
                    health_status['checks']['crm_leads'] = {
                        'status': 'healthy',
                        'details': f'CRM has {lead_count} leads available'
                    }
                else:
                    health_status['checks']['crm_leads'] = {
                        'status': 'warning',
                        'details': 'CRM initialized but no leads available'
                    }
            else:
                health_status['checks']['crm_leads'] = {
                    'status': 'unhealthy',
                    'details': 'CRM service not initialized'
                }
        except Exception as e:
            health_status['checks']['crm_leads'] = {
                'status': 'error',
                'details': f'CRM check failed: {str(e)}'
            }
        
        # Check OpenAI Key
        try:
            if services['ai_assistant']:
                # Try to get usage stats to verify API key
                stats = services['ai_assistant'].get_usage_stats()
                health_status['checks']['openai_key'] = {
                    'status': 'healthy',
                    'details': f'OpenAI API key valid (calls: {stats.get("total_calls", 0)})'
                }
            else:
                health_status['checks']['openai_key'] = {
                    'status': 'unhealthy',
                    'details': 'AI Assistant service not initialized'
                }
        except Exception as e:
            health_status['checks']['openai_key'] = {
                'status': 'error',
                'details': f'OpenAI key check failed: {str(e)}'
            }
        
        # Check All Services
        initialized_count = 0
        authenticated_count = 0
        
        for service_name, service in services.items():
            if service:
                initialized_count += 1
                if hasattr(service, 'is_authenticated') and service.is_authenticated():
                    authenticated_count += 1
        
        health_status['metrics']['initialized_services'] = initialized_count
        health_status['metrics']['authenticated_services'] = authenticated_count
        
        if initialized_count == len(services):
            health_status['checks']['services'] = {
                'status': 'healthy',
                'details': f'All {initialized_count} services initialized'
            }
        else:
            health_status['checks']['services'] = {
                'status': 'warning',
                'details': f'{initialized_count}/{len(services)} services initialized'
            }
        
        # Check Feature Flags
        try:
            if services['feature_flags']:
                flags_status = services['feature_flags'].get_status_report()
                enabled_count = sum(1 for flag in flags_status.get('flags', {}).values() if flag.get('enabled', False))
                health_status['metrics']['enabled_features'] = enabled_count
                
                health_status['checks']['feature_flags'] = {
                    'status': 'healthy',
                    'details': f'Feature flags system active ({enabled_count} enabled)'
                }
            else:
                health_status['checks']['feature_flags'] = {
                    'status': 'unhealthy',
                    'details': 'Feature flags service not initialized'
                }
        except Exception as e:
            health_status['checks']['feature_flags'] = {
                'status': 'error',
                'details': f'Feature flags check failed: {str(e)}'
            }
        
        # Determine overall health status
        unhealthy_checks = [check for check in health_status['checks'].values() 
                          if check['status'] in ['unhealthy', 'error']]
        
        if unhealthy_checks:
            health_status['status'] = 'unhealthy'
        elif any(check['status'] == 'warning' for check in health_status['checks'].values()):
            health_status['status'] = 'degraded'
        
        return jsonify(health_status)
    except Exception as e:
        return jsonify({
            'timestamp': datetime.now().isoformat(),
            'status': 'error',
            'error': str(e)
        }), 500

@app.route('/api/status')
def api_status():
    """Legacy status endpoint - redirects to health."""
    return redirect(url_for('api_health'))

@app.route('/api/test/email-parser', methods=['POST'])
def api_test_email_parser():
    """Test email parser with sample data."""
    try:
        data = request.get_json()
        
        # Create sample email if none provided
        if not data:
            data = {
                "id": "test123",
                "threadId": "thread123",
                "snippet": "Test email snippet",
                "labelIds": ["UNREAD", "INBOX"],
                "payload": {
                    "headers": [
                        {"name": "From", "value": "test@example.com"},
                        {"name": "To", "value": "info@fikirisolutions.com"},
                        {"name": "Subject", "value": "Test Subject"},
                        {"name": "Date", "value": "Mon, 1 Jan 2024 12:00:00 +0000"}
                    ],
                    "mimeType": "text/plain",
                    "body": {
                        "data": "SGVsbG8gd29ybGQ="  # "Hello world" in base64
                    }
                }
            }
        
        # Parse email
        parsed = services['parser'].parse_message(data)
        
        return jsonify({
            'success': True,
            'parsed_email': parsed,
            'sender': services['parser'].get_sender(parsed),
            'subject': services['parser'].get_subject(parsed),
            'body': services['parser'].get_body_text(parsed),
            'is_unread': services['parser'].is_unread(parsed)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/test/email-actions', methods=['POST'])
def api_test_email_actions():
    """Test email actions."""
    try:
        data = request.get_json()
        
        # Create sample parsed email
        sample_email = {
            "message_id": "test123",
            "headers": {
                "from": data.get('sender', 'test@example.com'),
                "subject": data.get('subject', 'Test Subject')
            },
            "labels": ["UNREAD"]
        }
        
        # Test different actions
        results = {}
        actions = ['auto_reply', 'mark_read', 'add_label']
        
        for action in actions:
            result = services['actions'].process_email(sample_email, action)
            results[action] = result
        
        # Get stats
        stats = services['actions'].get_stats()
        
        return jsonify({
            'success': True,
            'results': results,
            'stats': stats
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/test/crm', methods=['POST'])
def api_test_crm():
    """Test CRM service."""
    try:
        data = request.get_json()
        
        # Add test lead
        email = data.get('email', 'test@example.com')
        name = data.get('name', 'Test User')
        
        lead = services['crm'].add_lead(email, name, 'web_test')
        
        # Update lead
        services['crm'].update_lead_stage(lead.id, 'qualified')
        services['crm'].add_note(lead.id, 'Test note from web interface')
        services['crm'].add_tag(lead.id, 'web-test')
        services['crm'].record_contact(lead.id, 'web')
        
        # Get stats
        stats = services['crm'].get_lead_stats()
        
        return jsonify({
            'success': True,
            'lead': lead.to_dict(),
            'stats': stats
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/test/ai-assistant', methods=['POST'])
def api_test_ai_assistant():
    """Test AI assistant."""
    try:
        data = request.get_json()
        
        email_content = data.get('content', 'Hi, I need help with your services.')
        sender_name = data.get('sender', 'Test User')
        subject = data.get('subject', 'Test Subject')
        
        # Test classification
        classification = services['ai_assistant'].classify_email_intent(email_content, subject)
        
        # Test response generation
        response = services['ai_assistant'].generate_response(
            email_content, sender_name, subject, classification['intent']
        )
        
        # Test contact extraction
        contact_info = services['ai_assistant'].extract_contact_info(email_content)
        
        # Get usage stats
        stats = services['ai_assistant'].get_usage_stats()
        
        return jsonify({
            'success': True,
            'classification': classification,
            'response': response,
            'contact_info': contact_info,
            'stats': stats
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/ai/chat', methods=['POST'])
def api_ai_chat():
    """Handle AI chat messages."""
    try:
        data = request.get_json()
        
        user_message = data.get('message', '')
        context = data.get('context', {})
        
        if not user_message.strip():
            return jsonify({'error': 'Message cannot be empty'}), 400
        
        # Check if AI assistant is available
        if not services['ai_assistant'] or not services['ai_assistant'].is_enabled():
            return jsonify({
                'response': 'AI Assistant is currently unavailable. Please check your OpenAI API key configuration.',
                'error': 'AI service not available'
            }), 503
        
        # Generate AI response
        ai_response = services['ai_assistant'].generate_chat_response(
            user_message, 
            context.get('conversation_history', [])
        )
        
        return jsonify({
            'response': ai_response,
            'timestamp': datetime.now().isoformat(),
            'success': True
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/test/ml-scoring', methods=['POST'])
def api_test_ml_scoring():
    """Test ML scoring service."""
    try:
        data = request.get_json()
        
        email_data = {
            'content': data.get('content', 'I need urgent pricing for your premium services.'),
            'subject': data.get('subject', 'Urgent: Pricing Request'),
            'timestamp': datetime.now().isoformat()
        }
        
        lead_data = {
            'email': data.get('email', 'test@example.com'),
            'contact_count': data.get('contact_count', 1)
        }
        
        # Calculate score
        score_result = services['ml_scoring'].calculate_lead_score(email_data, lead_data)
        
        # Get stats
        stats = services['ml_scoring'].get_scoring_stats()
        
        return jsonify({
            'success': True,
            'score_result': score_result,
            'stats': stats
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/test/vector-search', methods=['POST'])
def api_test_vector_search():
    """Test vector search service."""
    try:
        data = request.get_json()
        
        # Add test documents
        documents = [
            {
                'text': 'Fikiri Solutions provides Gmail automation and lead management services.',
                'metadata': {'category': 'services', 'type': 'description'}
            },
            {
                'text': 'Our AI-powered email assistant can automatically respond to customer inquiries.',
                'metadata': {'category': 'features', 'type': 'ai_assistant'}
            },
            {
                'text': 'Contact us at info@fikirisolutions.com for pricing information.',
                'metadata': {'category': 'contact', 'type': 'pricing'}
            }
        ]
        
        # Add documents
        doc_ids = []
        for doc in documents:
            doc_id = services['vector_search'].add_document(doc['text'], doc['metadata'])
            doc_ids.append(doc_id)
        
        # Test search
        query = data.get('query', 'How can I get pricing for your services?')
        results = services['vector_search'].search_similar(query, top_k=3)
        
        # Test RAG context
        context = services['vector_search'].get_context_for_rag(query)
        
        # Get stats
        stats = services['vector_search'].get_stats()
        
        return jsonify({
            'success': True,
            'doc_ids': doc_ids,
            'search_results': results,
            'context': context,
            'stats': stats
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# @app.route('/api/test/hybrid', methods=['POST'])  # Removed - causing issues
# def api_test_hybrid():
#     """Test strategic hybrid service."""
#     try:
#         data = request.get_json()
#         
#         email_data = {
#             'sender': data.get('sender', 'test@example.com'),
#             'subject': data.get('subject', 'Test Subject'),
#             'content': data.get('content', 'Test email content')
#         }
#         
#         # Process strategically
#         result = services['hybrid'].process_email_strategically(email_data)
#         
#         # Get strategic report
#         report = services['hybrid'].get_strategic_report()
#         
#         return jsonify({
#             'success': True,
#             'processing_result': result,
#             'strategic_report': report
#         })
#     except Exception as e:
#         return jsonify({'error': str(e)}), 500

@app.route('/api/feature-flags')
def api_feature_flags():
    """Get feature flags status."""
    try:
        if services['feature_flags']:
            status = services['feature_flags'].get_status_report()
            return jsonify(status)
        else:
            return jsonify({'error': 'Feature flags not initialized'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/feature-flags/<feature_name>', methods=['POST'])
def api_toggle_feature_flag(feature_name):
    """Toggle a feature flag."""
    try:
        data = request.get_json()
        enabled = data.get('enabled', True)
        
        if services['feature_flags']:
            if enabled:
                services['feature_flags'].enable_feature(feature_name)
            else:
                services['feature_flags'].disable_feature(feature_name)
            
            return jsonify({'success': True, 'feature': feature_name, 'enabled': enabled})
        else:
            return jsonify({'error': 'Feature flags not initialized'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# WebSocket Event Handlers for Real-Time Updates
@socketio.on('connect')
def handle_connect():
    """Handle client connection."""
    print(f"Client connected: {request.sid}")
    emit('status', {'message': 'Connected to Fikiri Solutions'})

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection."""
    print(f"Client disconnected: {request.sid}")

@socketio.on('subscribe_dashboard')
def handle_dashboard_subscription():
    """Subscribe to dashboard updates."""
    print(f"Client {request.sid} subscribed to dashboard updates")
    emit('dashboard_subscribed', {'status': 'success'})

@socketio.on('request_metrics_update')
def handle_metrics_update():
    """Send real-time metrics update."""
    try:
        # Get current metrics
        total_emails = 0
        active_leads = 0
        ai_responses = 0
        avg_response_time = 0.0
        
        if services['crm']:
            try:
                leads = services['crm'].get_all_leads()
                active_leads = len(leads)
            except:
                active_leads = 0
        
        if services['ai_assistant']:
            try:
                stats = services['ai_assistant'].get_usage_stats()
                ai_responses = stats.get('successful_responses', 0)
                avg_response_time = stats.get('avg_response_time', 0.0)
            except:
                ai_responses = 0
                avg_response_time = 0.0
        
        if services['gmail'] and services['gmail'].is_authenticated():
            total_emails = 42  # Placeholder
        
        metrics = {
            'totalEmails': total_emails,
            'activeLeads': active_leads,
            'aiResponses': ai_responses,
            'avgResponseTime': round(avg_response_time, 2),
            'timestamp': datetime.now().isoformat()
        }
        
        emit('metrics_update', metrics)
        
    except Exception as e:
        emit('error', {'message': f'Failed to update metrics: {str(e)}'})

@socketio.on('request_services_update')
def handle_services_update():
    """Send real-time services status update."""
    try:
        service_list = []
        
        # Gmail Service
        gmail_status = 'active' if services['gmail'] and services['gmail'].is_authenticated() else 'inactive'
        service_list.append({
            'id': 'gmail',
            'name': 'Gmail Integration',
            'status': gmail_status,
            'description': 'Connect and manage Gmail accounts for email automation'
        })
        
        # AI Assistant Service
        ai_status = 'active' if services['ai_assistant'] and services['ai_assistant'].is_enabled() else 'inactive'
        service_list.append({
            'id': 'ai_assistant',
            'name': 'AI Assistant',
            'status': ai_status,
            'description': 'AI-powered email responses and lead analysis'
        })
        
        # CRM Service
        crm_status = 'active' if services['crm'] else 'inactive'
        service_list.append({
            'id': 'crm',
            'name': 'CRM System',
            'status': crm_status,
            'description': 'Customer relationship management and lead tracking'
        })
        
        emit('services_update', {
            'services': service_list,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        emit('error', {'message': f'Failed to update services: {str(e)}'})

def broadcast_activity_update(activity_type: str, message: str, status: str = 'success'):
    """Broadcast activity update to all connected clients."""
    activity = {
        'id': int(time.time()),
        'type': activity_type,
        'message': message,
        'timestamp': datetime.now().isoformat(),
        'status': status
    }
    socketio.emit('activity_update', activity)

if __name__ == '__main__':
    # Create templates directory if it doesn't exist
    templates_dir = Path('templates')
    templates_dir.mkdir(exist_ok=True)
    
    # Create basic dashboard template

# Dashboard Data Endpoints
@app.route('/api/services', methods=['GET'])
def api_get_services():
    """Get all available services and their status."""
    try:
        service_list = []
        
        # Gmail Service
        gmail_status = 'active' if services['gmail'] and services['gmail'].is_authenticated() else 'inactive'
        service_list.append({
            'id': 'gmail',
            'name': 'Gmail Integration',
            'status': gmail_status,
            'description': 'Connect and manage Gmail accounts for email automation'
        })
        
        # Outlook Service (placeholder for future integration)
        service_list.append({
            'id': 'outlook',
            'name': 'Outlook Integration',
            'status': 'inactive',
            'description': 'Microsoft Outlook integration (coming soon)'
        })
        
        # AI Assistant Service
        ai_status = 'active' if services['ai_assistant'] and services['ai_assistant'].is_enabled() else 'inactive'
        service_list.append({
            'id': 'ai_assistant',
            'name': 'AI Assistant',
            'status': ai_status,
            'description': 'AI-powered email responses and lead analysis'
        })
        
        # CRM Service
        crm_status = 'active' if services['crm'] else 'inactive'
        service_list.append({
            'id': 'crm',
            'name': 'CRM System',
            'status': crm_status,
            'description': 'Customer relationship management and lead tracking'
        })
        
        # Email Parser Service
        parser_status = 'active' if services['parser'] else 'inactive'
        service_list.append({
            'id': 'email_parser',
            'name': 'Email Parser',
            'status': parser_status,
            'description': 'Intelligent email content analysis and extraction'
        })
        
        # ML Scoring Service
        ml_status = 'active' if services['ml_scoring'] else 'inactive'
        service_list.append({
            'id': 'ml_scoring',
            'name': 'Lead Scoring',
            'status': ml_status,
            'description': 'Machine learning-powered lead qualification'
        })
        
        return jsonify(service_list)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/metrics', methods=['GET'])
def api_get_metrics():
    """Get dashboard metrics."""
    try:
        # Get real data from services
        total_emails = 0
        active_leads = 0
        ai_responses = 0
        avg_response_time = 0.0
        
        # Count leads from CRM
        if services['crm']:
            try:
                leads = services['crm'].get_all_leads()
                active_leads = len(leads)
            except:
                active_leads = 0
        
        # Get AI stats
        if services['ai_assistant']:
            try:
                stats = services['ai_assistant'].get_usage_stats()
                ai_responses = stats.get('successful_responses', 0)
                avg_response_time = stats.get('avg_response_time', 0.0)
            except:
                ai_responses = 0
                avg_response_time = 0.0
        
        # Simulate email count (would come from Gmail API in real implementation)
        if services['gmail'] and services['gmail'].is_authenticated():
            total_emails = 42  # Placeholder - would query Gmail API
        
        metrics = {
            'totalEmails': total_emails,
            'activeLeads': active_leads,
            'aiResponses': ai_responses,
            'avgResponseTime': round(avg_response_time, 2)
        }
        
        return jsonify(metrics)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/activity', methods=['GET'])
def api_get_activity():
    """Get recent activity feed."""
    try:
        activity_list = []
        
        # Add AI Assistant activity
        if services['ai_assistant']:
            try:
                stats = services['ai_assistant'].get_usage_stats()
                if stats.get('successful_responses', 0) > 0:
                    activity_list.append({
                        'id': 1,
                        'type': 'ai_response',
                        'message': f'AI Assistant generated {stats.get("successful_responses", 0)} responses',
                        'timestamp': datetime.now().isoformat(),
                        'status': 'success'
                    })
            except:
                pass
        
        # Add CRM activity
        if services['crm']:
            try:
                leads = services['crm'].get_all_leads()
                if leads:
                    activity_list.append({
                        'id': 2,
                        'type': 'lead_added',
                        'message': f'{len(leads)} leads in CRM system',
                        'timestamp': datetime.now().isoformat(),
                        'status': 'success'
                    })
            except:
                pass
        
        # Add Gmail activity
        if services['gmail'] and services['gmail'].is_authenticated():
            activity_list.append({
                'id': 3,
                'type': 'email_sync',
                'message': 'Gmail account connected successfully',
                'timestamp': datetime.now().isoformat(),
                'status': 'success'
            })
        else:
            activity_list.append({
                'id': 4,
                'type': 'email_sync',
                'message': 'Gmail integration not configured',
                'timestamp': datetime.now().isoformat(),
                'status': 'warning'
            })
        
        # Sort by timestamp (newest first)
        activity_list.sort(key=lambda x: x['timestamp'], reverse=True)
        
        return jsonify(activity_list)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Email Service Integration Endpoints
@app.route('/api/email/providers', methods=['GET'])
def api_get_email_providers():
    """Get all available email providers and their status."""
    try:
        if not services['email_manager']:
            return jsonify({'error': 'Email manager not initialized'}), 500
        
        status = services['email_manager'].get_provider_status()
        return jsonify({
            'providers': status,
            'active_provider': services['email_manager'].active_provider
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/email/switch-provider', methods=['POST'])
def api_switch_email_provider():
    """Switch to a different email provider."""
    try:
        data = request.get_json()
        provider_name = data.get('provider')
        
        if not services['email_manager']:
            return jsonify({'error': 'Email manager not initialized'}), 500
        
        if services['email_manager'].switch_provider(provider_name):
            return jsonify({
                'success': True,
                'active_provider': provider_name,
                'message': f'Switched to {provider_name}'
            })
        else:
            return jsonify({'error': f'Provider {provider_name} not available'}), 400
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/email/messages', methods=['GET'])
def api_get_email_messages():
    """Get recent messages from the active email provider."""
    try:
        if not services['email_manager']:
            return jsonify({'error': 'Email manager not initialized'}), 500
        
        limit = request.args.get('limit', 10, type=int)
        messages = services['email_manager'].get_all_messages(limit)
        
        return jsonify({
            'messages': messages,
            'count': len(messages),
            'provider': services['email_manager'].active_provider
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/email/send', methods=['POST'])
def api_send_email():
    """Send an email via the active provider."""
    try:
        data = request.get_json()
        to = data.get('to')
        subject = data.get('subject')
        body = data.get('body')
        
        if not all([to, subject, body]):
            return jsonify({'error': 'Missing required fields: to, subject, body'}), 400
        
        if not services['email_manager']:
            return jsonify({'error': 'Email manager not initialized'}), 500
        
        success = services['email_manager'].send_message(to, subject, body)
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Email sent successfully',
                'provider': services['email_manager'].active_provider
            })
        else:
            return jsonify({'error': 'Failed to send email'}), 500
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/health', methods=['GET'])
def api_health():
    """Health check endpoint for deployment monitoring."""
    try:
        health_status = {
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'version': '1.0.0',
            'services': {}
        }
        
        # Check each service
        service_checks = {
            'config': lambda: services['config'] is not None,
            'auth': lambda: services['auth'] is not None,
            'parser': lambda: services['parser'] is not None,
            'gmail': lambda: services['gmail'] is not None,
            'actions': lambda: services['actions'] is not None,
            'crm': lambda: services['crm'] is not None,
            'ai_assistant': lambda: services['ai_assistant'] is not None,
            'ml_scoring': lambda: services['ml_scoring'] is not None,
            'vector_search': lambda: services['vector_search'] is not None,
            'feature_flags': lambda: services['feature_flags'] is not None
        }
        
        # Service-specific status checks
        service_status_checks = {
            'auth': lambda: {
                'authenticated': services['auth'].check_token_file() if services['auth'] else False,
                'enabled': True
            },
            'ai_assistant': lambda: {
                'authenticated': services['ai_assistant'].is_enabled() if services['ai_assistant'] else False,
                'enabled': services['ai_assistant'].is_enabled() if services['ai_assistant'] else False
            },
            'gmail': lambda: {
                'authenticated': services['gmail'].is_authenticated() if services['gmail'] else False,
                'enabled': True
            }
        }
        
        all_healthy = True
        for service_name, check_func in service_checks.items():
            try:
                is_healthy = check_func()
                
                # Base status
                service_status = {
                    'status': 'healthy' if is_healthy else 'unhealthy',
                    'available': is_healthy,
                    'initialized': is_healthy
                }
                
                # Add service-specific status if available
                if service_name in service_status_checks:
                    try:
                        specific_status = service_status_checks[service_name]()
                        service_status.update(specific_status)
                    except Exception as e:
                        print(f"Warning: Could not get specific status for {service_name}: {e}")
                
                health_status['services'][service_name] = service_status
                
                if not is_healthy:
                    all_healthy = False
            except Exception as e:
                health_status['services'][service_name] = {
                    'status': 'error',
                    'error': str(e),
                    'available': False,
                    'initialized': False
                }
                all_healthy = False
        
        # Overall status
        if not all_healthy:
            health_status['status'] = 'degraded'
        
        status_code = 200 if all_healthy else 503
        return jsonify(health_status), status_code
        
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'timestamp': datetime.now().isoformat(),
            'error': str(e)
        }), 500

    dashboard_html = '''<!DOCTYPE html>
<html>
<head>
    <title>Fikiri Solutions - Dashboard</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .container { max-width: 1200px; margin: 0 auto; }
        .header { background: #2c3e50; color: white; padding: 20px; border-radius: 5px; }
        .section { margin: 20px 0; padding: 20px; border: 1px solid #ddd; border-radius: 5px; }
        .status { display: flex; gap: 20px; flex-wrap: wrap; }
        .status-item { background: #f8f9fa; padding: 15px; border-radius: 5px; flex: 1; min-width: 200px; }
        .test-section { margin: 10px 0; }
        .test-button { background: #007bff; color: white; padding: 10px 20px; border: none; border-radius: 3px; cursor: pointer; margin: 5px; }
        .test-button:hover { background: #0056b3; }
        .result { background: #f8f9fa; padding: 10px; margin: 10px 0; border-radius: 3px; white-space: pre-wrap; }
        .success { border-left: 4px solid #28a745; }
        .error { border-left: 4px solid #dc3545; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚀 Fikiri Solutions - Strategic Dashboard</h1>
            <p>Test all core services with strategic feature flags</p>
        </div>
        
        <div class="section">
            <h2>📊 System Status</h2>
            <div id="status" class="status"></div>
        </div>
        
        <div class="section">
            <h2>🧪 Service Tests</h2>
            
            <div class="test-section">
                <h3>Email Parser</h3>
                <button class="test-button" onclick="testEmailParser()">Test Email Parser</button>
                <div id="email-parser-result" class="result" style="display:none;"></div>
            </div>
            
            <div class="test-section">
                <h3>Email Actions</h3>
                <button class="test-button" onclick="testEmailActions()">Test Email Actions</button>
                <div id="email-actions-result" class="result" style="display:none;"></div>
            </div>
            
            <div class="test-section">
                <h3>CRM Service</h3>
                <button class="test-button" onclick="testCRM()">Test CRM Service</button>
                <div id="crm-result" class="result" style="display:none;"></div>
            </div>
            
            <div class="test-section">
                <h3>AI Assistant</h3>
                <button class="test-button" onclick="testAIAssistant()">Test AI Assistant</button>
                <div id="ai-assistant-result" class="result" style="display:none;"></div>
            </div>
            
            <div class="test-section">
                <h3>ML Scoring</h3>
                <button class="test-button" onclick="testMLScoring()">Test ML Scoring</button>
                <div id="ml-scoring-result" class="result" style="display:none;"></div>
            </div>
            
            <div class="test-section">
                <h3>Vector Search</h3>
                <button class="test-button" onclick="testVectorSearch()">Test Vector Search</button>
                <div id="vector-search-result" class="result" style="display:none;"></div>
            </div>
            
            <!-- <div class="test-section">  Removed - causing issues
                <h3>Strategic Hybrid</h3>
                <button class="test-button" onclick="testHybrid()">Test Hybrid Service</button>
                <div id="hybrid-result" class="result" style="display:none;"></div>
            </div> -->
        </div>
    </div>
    
    <script>
        // Load system status
        async function loadStatus() {
            try {
                const response = await fetch('/api/status');
                const data = await response.json();
                
                const statusDiv = document.getElementById('status');
                statusDiv.innerHTML = '';
                
                for (const [service, info] of Object.entries(data.services)) {
                    const statusItem = document.createElement('div');
                    statusItem.className = 'status-item';
                    statusItem.innerHTML = `
                        <h4>${service}</h4>
                        <p>Initialized: ${info.initialized ? '✅' : '❌'}</p>
                        ${info.authenticated !== undefined ? `<p>Authenticated: ${info.authenticated ? '✅' : '❌'}</p>` : ''}
                        ${info.enabled !== undefined ? `<p>Enabled: ${info.enabled ? '✅' : '❌'}</p>` : ''}
                    `;
                    statusDiv.appendChild(statusItem);
                }
            } catch (error) {
                console.error('Error loading status:', error);
            }
        }
        
        // Test functions
        async function testEmailParser() {
            const resultDiv = document.getElementById('email-parser-result');
            resultDiv.style.display = 'block';
            resultDiv.textContent = 'Testing...';
            
            try {
                const response = await fetch('/api/test/email-parser', { 
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({})
                });
                const data = await response.json();
                resultDiv.textContent = JSON.stringify(data, null, 2);
                resultDiv.className = 'result success';
            } catch (error) {
                resultDiv.textContent = 'Error: ' + error.message;
                resultDiv.className = 'result error';
            }
        }
        
        async function testEmailActions() {
            const resultDiv = document.getElementById('email-actions-result');
            resultDiv.style.display = 'block';
            resultDiv.textContent = 'Testing...';
            
            try {
                const response = await fetch('/api/test/email-actions', { 
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({})
                });
                const data = await response.json();
                resultDiv.textContent = JSON.stringify(data, null, 2);
                resultDiv.className = 'result success';
            } catch (error) {
                resultDiv.textContent = 'Error: ' + error.message;
                resultDiv.className = 'result error';
            }
        }
        
        async function testCRM() {
            const resultDiv = document.getElementById('crm-result');
            resultDiv.style.display = 'block';
            resultDiv.textContent = 'Testing...';
            
            try {
                const response = await fetch('/api/test/crm', { 
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({})
                });
                const data = await response.json();
                resultDiv.textContent = JSON.stringify(data, null, 2);
                resultDiv.className = 'result success';
            } catch (error) {
                resultDiv.textContent = 'Error: ' + error.message;
                resultDiv.className = 'result error';
            }
        }
        
        async function testAIAssistant() {
            const resultDiv = document.getElementById('ai-assistant-result');
            resultDiv.style.display = 'block';
            resultDiv.textContent = 'Testing...';
            
            try {
                const response = await fetch('/api/test/ai-assistant', { 
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({})
                });
                const data = await response.json();
                resultDiv.textContent = JSON.stringify(data, null, 2);
                resultDiv.className = 'result success';
            } catch (error) {
                resultDiv.textContent = 'Error: ' + error.message;
                resultDiv.className = 'result error';
            }
        }
        
        async function testMLScoring() {
            const resultDiv = document.getElementById('ml-scoring-result');
            resultDiv.style.display = 'block';
            resultDiv.textContent = 'Testing...';
            
            try {
                const response = await fetch('/api/test/ml-scoring', { 
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({})
                });
                const data = await response.json();
                resultDiv.textContent = JSON.stringify(data, null, 2);
                resultDiv.className = 'result success';
            } catch (error) {
                resultDiv.textContent = 'Error: ' + error.message;
                resultDiv.className = 'result error';
            }
        }
        
        async function testVectorSearch() {
            const resultDiv = document.getElementById('vector-search-result');
            resultDiv.style.display = 'block';
            resultDiv.textContent = 'Testing...';
            
            try {
                const response = await fetch('/api/test/vector-search', { 
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({})
                });
                const data = await response.json();
                resultDiv.textContent = JSON.stringify(data, null, 2);
                resultDiv.className = 'result success';
            } catch (error) {
                resultDiv.textContent = 'Error: ' + error.message;
                resultDiv.className = 'result error';
            }
        }
        
        // async function testHybrid() {  Removed - causing issues
        //     const resultDiv = document.getElementById('hybrid-result');
        //     resultDiv.style.display = 'block';
        //     resultDiv.textContent = 'Testing...';
        //     
        //     try {
        //         const response = await fetch('/api/test/hybrid', { method: 'POST' });
        //         const data = await response.json();
        //         resultDiv.textContent = JSON.stringify(data, null, 2);
        //         resultDiv.className = 'result success';
        //     } catch (error) {
        //         resultDiv.textContent = 'Error: ' + error.message;
        //         resultDiv.className = 'result error';
        //     }
        // }
        
        // Load status on page load
        loadStatus();
    </script>
</body>
</html>'''
    
    # Write dashboard template
    with open('templates/dashboard.html', 'w') as f:
        f.write(dashboard_html)
    
    print("🚀 Starting Fikiri Flask Application...")
    print("📊 Dashboard: http://localhost:8081")
    print("🔧 API Endpoints: http://localhost:8081/api/")
    
    # Run with SocketIO for real-time updates
    socketio.run(app, debug=True, host='0.0.0.0', port=8081)
