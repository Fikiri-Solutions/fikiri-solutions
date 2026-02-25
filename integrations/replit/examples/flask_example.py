"""
Flask Example with Fikiri Integration
Complete example showing how to integrate Fikiri into a Flask app
"""

from flask import Flask, render_template_string, request, jsonify
from fikiri_replit import FikiriFlaskHelper
import os

app = Flask(__name__)

# Get API key from environment variable (set in Replit Secrets)
API_KEY = os.getenv('FIKIRI_API_KEY', '')
if not API_KEY:
    print("⚠️ Warning: FIKIRI_API_KEY not set. Set it in Replit Secrets.")

# Initialize Fikiri helper
fikiri = FikiriFlaskHelper(api_key=API_KEY)

# Register Fikiri blueprint (provides /fikiri/chatbot, /fikiri/leads/capture, etc.)
app.register_blueprint(fikiri.create_blueprint())

# HTML template
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>My Flask App with Fikiri</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
        }
        .section {
            margin: 40px 0;
            padding: 20px;
            border: 1px solid #ddd;
            border-radius: 8px;
        }
        form {
            max-width: 400px;
        }
        input, button {
            width: 100%;
            padding: 10px;
            margin: 8px 0;
            box-sizing: border-box;
        }
        button {
            background: #0f766e;
            color: white;
            border: none;
            cursor: pointer;
            border-radius: 4px;
        }
        .message {
            margin-top: 10px;
            padding: 10px;
            border-radius: 4px;
        }
        .success {
            background: #d4edda;
            color: #155724;
        }
        .error {
            background: #f8d7da;
            color: #721c24;
        }
    </style>
</head>
<body>
    <h1>Welcome to My Flask App</h1>
    
    <!-- Lead Capture Form -->
    <div class="section">
        <h2>Get in Touch</h2>
        {{ lead_form|safe }}
    </div>
    
    <!-- Chatbot Query Form -->
    <div class="section">
        <h2>Ask a Question</h2>
        <form id="chatbot-form">
            <input type="text" id="chatbot-query" placeholder="What are your business hours?" required>
            <button type="submit">Ask</button>
        </form>
        <div id="chatbot-response"></div>
    </div>
    
    <script src="https://cdn.fikirisolutions.com/sdk/v1/fikiri-sdk.js"></script>
    <script>
        // Initialize Fikiri SDK
        Fikiri.init({
            apiKey: '{{ api_key }}',
            features: ['chatbot', 'leadCapture']
        });
        
        // Show chatbot widget
        Fikiri.Chatbot.show();
        
        // Handle chatbot query
        document.getElementById('chatbot-form').addEventListener('submit', function(e) {
            e.preventDefault();
            var query = document.getElementById('chatbot-query').value;
            var responseDiv = document.getElementById('chatbot-response');
            responseDiv.innerHTML = '<p>Thinking...</p>';
            
            Fikiri.Chatbot.query(query).then(function(result) {
                if (result.success) {
                    responseDiv.innerHTML = '<div class="message success"><strong>Bot:</strong> ' + result.response + '</div>';
                } else {
                    responseDiv.innerHTML = '<div class="message error">Error: ' + (result.error || 'Unknown error') + '</div>';
                }
            }).catch(function(error) {
                responseDiv.innerHTML = '<div class="message error">Error querying chatbot.</div>';
            });
        });
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    """Render homepage with Fikiri integration"""
    lead_form = fikiri.render_lead_capture_form(fields=['email', 'name', 'phone'])
    return render_template_string(HTML_TEMPLATE, api_key=API_KEY, lead_form=lead_form)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
