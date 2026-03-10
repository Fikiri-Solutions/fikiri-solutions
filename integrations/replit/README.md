# Fikiri Replit Integration

Python package for integrating Fikiri features into Replit projects.

## Installation

```bash
pip install fikiri-replit
```

Or install from source:

```bash
git clone https://github.com/fikirisolutions/fikiri-replit.git
cd fikiri-replit
pip install -e .
```

## Quick Start

### Basic Usage

```python
from fikiri_replit import FikiriClient

# Initialize client
client = FikiriClient(api_key='fik_your_api_key_here')

# Capture a lead
result = client.leads.create(
    email='user@example.com',
    name='John Doe',
    source='replit_app'
)

if result['success']:
    print(f"Lead created: {result['lead_id']}")
else:
    print(f"Error: {result['error']}")

# Query chatbot
response = client.chatbot.query('What are your business hours?')
print(response['response'])
```

### Flask Integration

```python
from flask import Flask
from fikiri_replit import FikiriFlaskHelper

app = Flask(__name__)

# Initialize helper
fikiri = FikiriFlaskHelper(api_key='fik_your_api_key_here')

# Register blueprint
app.register_blueprint(fikiri.create_blueprint())

# Render chatbot widget in template
@app.route('/')
def index():
    chatbot_html = fikiri.render_chatbot_widget()
    return f"""
    <html>
        <head><title>My App</title></head>
        <body>
            <h1>Welcome</h1>
            {chatbot_html}
        </body>
    </html>
    """

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
```

### FastAPI Integration

```python
from fastapi import FastAPI
from fikiri_replit import FikiriFastAPIHelper

app = FastAPI()

# Initialize helper
fikiri = FikiriFastAPIHelper(api_key='fik_your_api_key_here')

# Register router
app.include_router(fikiri.create_router())

@app.get('/')
def index():
    return {"message": "Welcome to my app"}
```

## API Reference

### FikiriClient

Main client class for API interactions.

#### Methods

**Leads:**
- `create(email, name=None, phone=None, source='replit_app', metadata=None)` - Create a lead
- `capture(**kwargs)` - Alias for create()

**Chatbot:**
- `query(query, conversation_id=None, context=None, lead=None)` - Query chatbot

**Forms:**
- `submit(form_id, fields, source='replit_app', metadata=None)` - Submit form

### FikiriFlaskHelper

Helper class for Flask integration.

#### Methods

- `create_blueprint(url_prefix='/fikiri')` - Create Flask blueprint
- `render_chatbot_widget(theme='light', position='bottom-right', title='Chat with us')` - Render widget HTML
- `render_lead_capture_form(fields=None, title='Get in Touch')` - Render form HTML

### FikiriFastAPIHelper

Helper class for FastAPI integration.

#### Methods

- `create_router(prefix='/fikiri')` - Create FastAPI router

## Examples

See `examples/` directory for complete examples:
- `flask_example.py` - Flask app with Fikiri integration
- `fastapi_example.py` - FastAPI app with Fikiri integration
- `basic_example.py` - Basic usage without framework

## Getting Your API Key

1. Log into [Fikiri dashboard](https://app.fikirisolutions.com)
2. Go to **Settings** → **API Keys**
3. Click **Create API Key**
4. Copy the key (starts with `fik_`)

## Environment Variables

You can set your API key as an environment variable:

```bash
export FIKIRI_API_KEY='fik_your_api_key_here'
```

Then use it in your code:

```python
import os
from fikiri_replit import FikiriClient

client = FikiriClient(api_key=os.getenv('FIKIRI_API_KEY'))
```

## Support

For help, visit [Fikiri Support](https://fikirisolutions.com/support) or email support@fikirisolutions.com
