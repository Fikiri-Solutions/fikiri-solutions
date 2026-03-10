"""
FastAPI Example with Fikiri Integration
Complete example showing how to integrate Fikiri into a FastAPI app
"""

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fikiri_replit import FikiriFastAPIHelper
import os

app = FastAPI(title="My FastAPI App with Fikiri")

# Get API key from environment variable (set in Replit Secrets)
API_KEY = os.getenv('FIKIRI_API_KEY', '')
if not API_KEY:
    print("⚠️ Warning: FIKIRI_API_KEY not set. Set it in Replit Secrets.")

# Initialize Fikiri helper
fikiri = FikiriFastAPIHelper(api_key=API_KEY)

# Register Fikiri router (provides /fikiri/chatbot, /fikiri/leads/capture, etc.)
app.include_router(fikiri.create_router())

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>My FastAPI App with Fikiri</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
        }}
        .section {{
            margin: 40px 0;
            padding: 20px;
            border: 1px solid #ddd;
            border-radius: 8px;
        }}
        form {{
            max-width: 400px;
        }}
        input, button {{
            width: 100%;
            padding: 10px;
            margin: 8px 0;
            box-sizing: border-box;
        }}
        button {{
            background: #0f766e;
            color: white;
            border: none;
            cursor: pointer;
            border-radius: 4px;
        }}
    </style>
</head>
<body>
    <h1>Welcome to My FastAPI App</h1>
    
    <!-- Lead Capture Form -->
    <div class="section">
        <h2>Get in Touch</h2>
        <form id="lead-form">
            <input type="text" name="name" placeholder="Name" required>
            <input type="email" name="email" placeholder="Email" required>
            <input type="tel" name="phone" placeholder="Phone (optional)">
            <button type="submit">Submit</button>
        </form>
        <div id="form-message"></div>
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
        Fikiri.init({{
            apiKey: '{api_key}',
            features: ['chatbot', 'leadCapture']
        }});
        
        // Show chatbot widget
        Fikiri.Chatbot.show();
        
        // Handle lead form
        document.getElementById('lead-form').addEventListener('submit', function(e) {{
            e.preventDefault();
            var formData = new FormData(this);
            
            Fikiri.LeadCapture.capture({{
                email: formData.get('email'),
                name: formData.get('name'),
                phone: formData.get('phone'),
                source: 'replit_app'
            }}).then(function(result) {{
                var msg = document.getElementById('form-message');
                if (result.success) {{
                    msg.innerHTML = '<p style="color: green;">Thank you!</p>';
                    this.reset();
                }} else {{
                    msg.innerHTML = '<p style="color: red;">Error: ' + result.error + '</p>';
                }}
            }}.bind(this));
        }});
        
        // Handle chatbot query
        document.getElementById('chatbot-form').addEventListener('submit', function(e) {{
            e.preventDefault();
            var query = document.getElementById('chatbot-query').value;
            var responseDiv = document.getElementById('chatbot-response');
            responseDiv.innerHTML = '<p>Thinking...</p>';
            
            Fikiri.Chatbot.query(query).then(function(result) {{
                if (result.success) {{
                    responseDiv.innerHTML = '<p><strong>Bot:</strong> ' + result.response + '</p>';
                }} else {{
                    responseDiv.innerHTML = '<p style="color: red;">Error: ' + result.error + '</p>';
                }}
            }});
        }});
    </script>
</body>
</html>
"""

@app.get('/', response_class=HTMLResponse)
def index():
    """Render homepage with Fikiri integration"""
    return HTML_TEMPLATE.format(api_key=API_KEY)

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host='0.0.0.0', port=5000)
