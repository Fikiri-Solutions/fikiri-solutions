"""
Flask helpers for Fikiri integration
"""

from flask import Blueprint, request, jsonify, render_template_string
from typing import Optional
from .client import FikiriClient


class FikiriFlaskHelper:
    """Helper class for Flask integration"""
    
    def __init__(self, api_key: str, api_url: str = "https://api.fikirisolutions.com"):
        """
        Initialize Flask helper
        
        Args:
            api_key: Your Fikiri API key
            api_url: Fikiri API base URL
        """
        self.client = FikiriClient(api_key, api_url)
    
    def create_blueprint(self, url_prefix: str = "/fikiri") -> Blueprint:
        """
        Create Flask blueprint with Fikiri endpoints
        
        Args:
            url_prefix: URL prefix for routes (default: '/fikiri')
        
        Returns:
            Flask Blueprint
        """
        bp = Blueprint('fikiri', __name__, url_prefix=url_prefix)
        
        @bp.route('/chatbot', methods=['POST'])
        def chatbot_query():
            """Chatbot query endpoint"""
            data = request.get_json()
            query = data.get('query')
            if not query:
                return jsonify({"success": False, "error": "Query is required"}), 400
            
            result = self.client.chatbot.query(
                query=query,
                conversation_id=data.get('conversation_id'),
                context=data.get('context'),
                lead=data.get('lead')
            )
            return jsonify(result)
        
        @bp.route('/leads/capture', methods=['POST'])
        def capture_lead():
            """Lead capture endpoint"""
            data = request.get_json()
            email = data.get('email')
            if not email:
                return jsonify({"success": False, "error": "Email is required"}), 400
            
            result = self.client.leads.create(
                email=email,
                name=data.get('name'),
                phone=data.get('phone'),
                source=data.get('source', 'replit_app'),
                metadata=data.get('metadata')
            )
            return jsonify(result)
        
        @bp.route('/forms/submit', methods=['POST'])
        def submit_form():
            """Form submission endpoint"""
            data = request.get_json()
            form_id = data.get('form_id', 'custom-form')
            fields = data.get('fields', {})
            
            if not fields.get('email'):
                return jsonify({"success": False, "error": "Email is required"}), 400
            
            result = self.client.forms.submit(
                form_id=form_id,
                fields=fields,
                source=data.get('source', 'replit_app'),
                metadata=data.get('metadata')
            )
            return jsonify(result)
        
        return bp
    
    def render_chatbot_widget(self, theme: str = "light", 
                              position: str = "bottom-right",
                              title: str = "Chat with us") -> str:
        """
        Render chatbot widget HTML
        
        Args:
            theme: Widget theme ('light' or 'dark')
            position: Widget position
            title: Widget title
        
        Returns:
            HTML string
        """
        return f"""
        <script src="https://cdn.fikirisolutions.com/sdk/v1/fikiri-sdk.js"></script>
        <script>
            Fikiri.init({{
                apiKey: '{self.client.api_key}',
                features: ['chatbot']
            }});
            
            window.addEventListener('load', function() {{
                Fikiri.Chatbot.show({{
                    theme: '{theme}',
                    position: '{position}',
                    title: '{title}'
                }});
            }});
        </script>
        """
    
    def render_lead_capture_form(self, fields: list = None, 
                                 title: str = "Get in Touch") -> str:
        """
        Render lead capture form HTML
        
        Args:
            fields: List of fields to include (default: ['email', 'name'])
            title: Form title
        
        Returns:
            HTML string
        """
        if fields is None:
            fields = ['email', 'name']
        
        has_name = 'name' in fields
        has_phone = 'phone' in fields
        
        return f"""
        <div class="fikiri-lead-capture" style="max-width: 400px; margin: 20px 0;">
            <h3>{title}</h3>
            <form id="fikiri-lead-form">
                {'<p><label>Name:</label><br><input type="text" name="name" required style="width: 100%; padding: 8px; box-sizing: border-box;"></p>' if has_name else ''}
                <p><label>Email:</label><br><input type="email" name="email" required style="width: 100%; padding: 8px; box-sizing: border-box;"></p>
                {'<p><label>Phone:</label><br><input type="tel" name="phone" style="width: 100%; padding: 8px; box-sizing: border-box;"></p>' if has_phone else ''}
                <p><button type="submit" style="padding: 10px 20px; background: #0f766e; color: white; border: none; cursor: pointer; border-radius: 4px;">Submit</button></p>
                <div id="fikiri-form-message"></div>
            </form>
        </div>
        <script src="https://cdn.fikirisolutions.com/sdk/v1/fikiri-sdk.js"></script>
        <script>
            Fikiri.init({{ apiKey: '{self.client.api_key}' }});
            
            document.getElementById('fikiri-lead-form').addEventListener('submit', function(e) {{
                e.preventDefault();
                var formData = new FormData(this);
                
                Fikiri.LeadCapture.capture({{
                    email: formData.get('email'),
                    name: formData.get('name') || '',
                    phone: formData.get('phone') || '',
                    source: 'replit_app'
                }}).then(function(result) {{
                    var msg = document.getElementById('fikiri-form-message');
                    if (result.success) {{
                        msg.innerHTML = '<p style="color: green;">Thank you! We\\'ll be in touch soon.</p>';
                        this.reset();
                    }} else {{
                        msg.innerHTML = '<p style="color: red;">Error: ' + (result.error || 'Unknown error') + '</p>';
                    }}
                }}.bind(this));
            }});
        </script>
        """
