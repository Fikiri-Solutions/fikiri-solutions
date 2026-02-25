"""
Fikiri Replit Integration Example
Demonstrates how to integrate Fikiri features into a Replit Flask app
"""

from flask import Flask, request, jsonify, render_template_string
import requests
import os

app = Flask(__name__)

# Get API key from environment variable (set in Replit Secrets)
FIKIRI_API_KEY = os.getenv('FIKIRI_API_KEY', '')
FIKIRI_API_URL = 'https://api.fikirisolutions.com'

# HTML template with Fikiri SDK
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>My Replit App with Fikiri</title>
    <script src="https://cdn.fikirisolutions.com/sdk/v1/fikiri-sdk.js"></script>
</head>
<body>
    <h1>Welcome to My App</h1>
    
    <!-- Lead Capture Form -->
    <form id="lead-form" style="max-width: 400px; margin: 20px 0;">
        <h3>Get in Touch</h3>
        <p>
            <label>Name:</label><br>
            <input type="text" id="name" required style="width: 100%; padding: 8px;">
        </p>
        <p>
            <label>Email:</label><br>
            <input type="email" id="email" required style="width: 100%; padding: 8px;">
        </p>
        <p>
            <button type="submit" style="padding: 10px 20px; background: #0f766e; color: white; border: none; cursor: pointer;">
                Submit
            </button>
        </p>
        <div id="message" style="margin-top: 10px;"></div>
    </form>
    
    <script>
        // Initialize Fikiri SDK
        Fikiri.init({
            apiKey: '{{ api_key }}',
            features: ['chatbot', 'leadCapture']
        });
        
        // Show chatbot
        Fikiri.Chatbot.show();
        
        // Handle form submission
        document.getElementById('lead-form').addEventListener('submit', function(e) {
            e.preventDefault();
            var email = document.getElementById('email').value;
            var name = document.getElementById('name').value;
            
            Fikiri.LeadCapture.capture({
                email: email,
                name: name,
                source: 'replit_app'
            }).then(function(result) {
                var messageDiv = document.getElementById('message');
                if (result.success) {
                    messageDiv.innerHTML = '<p style="color: green;">Thank you! We\'ll be in touch soon.</p>';
                    document.getElementById('lead-form').reset();
                } else {
                    messageDiv.innerHTML = '<p style="color: red;">Error: ' + (result.error || 'Unknown error') + '</p>';
                }
            }).catch(function(error) {
                document.getElementById('message').innerHTML = '<p style="color: red;">Error submitting form.</p>';
            });
        });
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    """Render homepage with Fikiri integration"""
    return render_template_string(HTML_TEMPLATE, api_key=FIKIRI_API_KEY)

@app.route('/api/capture-lead', methods=['POST'])
def capture_lead():
    """
    Server-side lead capture endpoint
    Uses Fikiri REST API directly
    """
    if not FIKIRI_API_KEY:
        return jsonify({
            "success": False,
            "error": "Fikiri API key not configured"
        }), 500
    
    data = request.get_json()
    email = data.get('email')
    name = data.get('name')
    
    if not email:
        return jsonify({
            "success": False,
            "error": "Email is required"
        }), 400
    
    # Call Fikiri API
    try:
        response = requests.post(
            f'{FIKIRI_API_URL}/api/webhooks/leads/capture',
            headers={
                'Content-Type': 'application/json',
                'X-API-Key': FIKIRI_API_KEY
            },
            json={
                'email': email,
                'name': name,
                'source': 'replit_app',
                'metadata': {
                    'replit_project': os.getenv('REPL_SLUG', 'unknown')
                }
            },
            timeout=10
        )
        
        if response.status_code == 200:
            return jsonify(response.json()), 200
        else:
            return jsonify({
                "success": False,
                "error": f"Fikiri API error: {response.status_code}"
            }), response.status_code
            
    except requests.exceptions.RequestException as e:
        return jsonify({
            "success": False,
            "error": f"Request failed: {str(e)}"
        }), 500

@app.route('/api/chatbot-query', methods=['POST'])
def chatbot_query():
    """
    Server-side chatbot query endpoint
    Proxies requests to Fikiri API
    """
    if not FIKIRI_API_KEY:
        return jsonify({
            "success": False,
            "error": "Fikiri API key not configured"
        }), 500
    
    data = request.get_json()
    query = data.get('query')
    
    if not query:
        return jsonify({
            "success": False,
            "error": "Query is required"
        }), 400
    
    # Call Fikiri API
    try:
        response = requests.post(
            f'{FIKIRI_API_URL}/api/public/chatbot/query',
            headers={
                'Content-Type': 'application/json',
                'X-API-Key': FIKIRI_API_KEY
            },
            json={
                'query': query,
                'context': data.get('context', {})
            },
            timeout=30
        )
        
        if response.status_code == 200:
            return jsonify(response.json()), 200
        else:
            return jsonify({
                "success": False,
                "error": f"Fikiri API error: {response.status_code}"
            }), response.status_code
            
    except requests.exceptions.RequestException as e:
        return jsonify({
            "success": False,
            "error": f"Request failed: {str(e)}"
        }), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
