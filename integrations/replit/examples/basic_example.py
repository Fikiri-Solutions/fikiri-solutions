"""
Basic Fikiri Client Example
Simple example without any web framework
"""

from fikiri_replit import FikiriClient
import os

# Get API key from environment variable
API_KEY = os.getenv('FIKIRI_API_KEY', 'fik_your_api_key_here')

# Initialize client
client = FikiriClient(api_key=API_KEY)

# Example 1: Capture a lead
print("Example 1: Capturing a lead...")
result = client.leads.create(
    email='user@example.com',
    name='John Doe',
    phone='+1-555-123-4567',
    source='replit_app',
    metadata={
        'replit_project': 'my-project',
        'referrer': 'example.com'
    }
)

if result['success']:
    print(f"✅ Lead created successfully! Lead ID: {result['lead_id']}")
    if result.get('deduplicated'):
        print("⚠️ Note: This was a duplicate submission (idempotency)")
else:
    print(f"❌ Error: {result['error']}")

print()

# Example 2: Query chatbot
print("Example 2: Querying chatbot...")
response = client.chatbot.query('What are your business hours?')

if response['success']:
    print(f"✅ Bot response: {response['response']}")
    print(f"   Confidence: {response.get('confidence', 'N/A')}")
    if response.get('sources'):
        print(f"   Sources: {', '.join(response['sources'])}")
else:
    print(f"❌ Error: {response['error']}")

print()

# Example 3: Submit a form
print("Example 3: Submitting a form...")
form_result = client.forms.submit(
    form_id='contact-form',
    fields={
        'email': 'contact@example.com',
        'name': 'Jane Smith',
        'phone': '+1-555-987-6543',
        'message': 'I have a question about your services'
    },
    source='replit_app'
)

if form_result['success']:
    print(f"✅ Form submitted successfully! Lead ID: {form_result['lead_id']}")
else:
    print(f"❌ Error: {form_result['error']}")
