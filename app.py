#!/usr/bin/env python3
"""
Fikiri Solutions - Flask Web Application
Web interface for testing and deploying Fikiri services.
"""

from flask import Flask, render_template, request, jsonify, redirect, url_for
# from flask_cors import CORS  # Commented out - not essential
import json
import os
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

# Initialize Flask app
app = Flask(__name__)
# CORS(app)  # Commented out - not essential
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
    'feature_flags': None
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
        
        print("✅ All services initialized successfully")
        return True
    except Exception as e:
        print(f"❌ Error initializing services: {e}")
        return False

# Initialize services on startup
initialize_services()

@app.route('/')
def index():
    """Main dashboard page."""
    return render_template('dashboard.html')

@app.route('/api/status')
def api_status():
    """Get system status."""
    try:
        status = {
            'timestamp': datetime.now().isoformat(),
            'services': {},
            'feature_flags': {},
            'capabilities': {}
        }
        
        # Check service status
        for service_name, service in services.items():
            if service:
                if hasattr(service, 'is_authenticated'):
                    status['services'][service_name] = {
                        'initialized': True,
                        'authenticated': service.is_authenticated()
                    }
                elif hasattr(service, 'is_enabled'):
                    status['services'][service_name] = {
                        'initialized': True,
                        'enabled': service.is_enabled()
                    }
                else:
                    status['services'][service_name] = {
                        'initialized': True
                    }
            else:
                status['services'][service_name] = {
                    'initialized': False
                }
        
        # Get feature flags status
        if services['feature_flags']:
            status['feature_flags'] = services['feature_flags'].get_status_report()
        
        # Get capabilities
        # if services['hybrid']:  # Removed - causing issues
        #     status['capabilities'] = services['hybrid'].get_strategic_report()
        
        return jsonify(status)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

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

if __name__ == '__main__':
    # Create templates directory if it doesn't exist
    templates_dir = Path('templates')
    templates_dir.mkdir(exist_ok=True)
    
    # Create basic dashboard template
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
    
    app.run(debug=True, host='0.0.0.0', port=8081)
