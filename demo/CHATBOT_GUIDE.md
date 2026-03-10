# Fikiri Chatbot Implementation Guide

**Complete guide to implementing Fikiri's AI-powered chatbot**

---

## 🎯 What We Built

### 1. **Backend API** ✅
- **Endpoint:** `POST /api/public/chatbot/query`
- **Authentication:** API Key (`X-API-Key` header)
- **Features:**
  - FAQ search
  - Knowledge Base search
  - Vector similarity search
  - Multi-turn conversation context
  - Expert escalation
  - Lead capture
  - Feedback collection

### 2. **JavaScript SDK** ✅
- **File:** `integrations/universal/fikiri-sdk.js`
- **Methods:**
  - `Fikiri.Chatbot.query(message, options)`
  - `Fikiri.Chatbot.show(options)`
  - `Fikiri.Chatbot.hide()`

### 3. **Demo Pages** ✅
- **Full Demo:** `demo/chatbot-demo.html`
- **Simple Demo:** `demo/simple-chatbot.html`
- **Access:** `http://localhost:5000/demo/chatbot` or `/demo/simple`

---

## 🚀 Quick Start

### Step 1: Get API Key

1. Log into Fikiri dashboard
2. Go to **Settings** → **API Keys**
3. Create new API key with scope: `chatbot:query`
4. Copy the key (starts with `fik_`)

### Step 2: Initialize SDK

```html
<script src="https://cdn.fikirisolutions.com/sdk/v1/fikiri-sdk.js"></script>
<script>
  Fikiri.init({
    apiKey: 'fik_your_api_key_here',
    apiUrl: 'https://api.fikirisolutions.com', // or your API URL
    features: ['chatbot']
  });
</script>
```

### Step 3: Query Chatbot

```javascript
// Simple query
const response = await Fikiri.Chatbot.query('What are your business hours?');

if (response.success) {
  console.log('Answer:', response.response);
  console.log('Confidence:', response.confidence);
  console.log('Sources:', response.sources);
}

// With conversation context
const response = await Fikiri.Chatbot.query('Tell me more', {
  conversationId: 'conversation-123'
});
```

### Step 4: Show Widget (Optional)

```javascript
// Show chatbot widget
Fikiri.Chatbot.show({
  theme: 'light',
  position: 'bottom-right',
  title: 'Need Help?'
});
```

---

## 📋 API Reference

### Endpoint: `POST /api/public/chatbot/query`

**Headers:**
```
X-API-Key: fik_your_api_key_here
Content-Type: application/json
```

**Request Body:**
```json
{
  "query": "What are your business hours?",
  "conversation_id": "optional-conversation-id",
  "context": {
    "user_id": "optional",
    "session_id": "optional"
  },
  "lead": {
    "email": "user@example.com",
    "name": "John Doe",
    "phone": "+1234567890"
  }
}
```

**Response:**
```json
{
  "success": true,
  "query": "What are your business hours?",
  "response": "We're open Monday-Friday 9am-5pm EST.",
  "answer": "We're open Monday-Friday 9am-5pm EST.",
  "confidence": 0.95,
  "fallback_used": false,
  "sources": [
    "FAQ: Business Hours",
    "Knowledge Base: Company Information"
  ],
  "conversation_id": "conv_123456",
  "follow_up": "Would you like to schedule a call?",
  "escalated": false
}
```

**Error Response:**
```json
{
  "success": false,
  "error": "Query is required",
  "error_code": "MISSING_QUERY"
}
```

---

## 🎨 SDK Methods

### `Fikiri.Chatbot.query(text, options)`

Send a message to the chatbot.

**Parameters:**
- `text` (string): The user's message
- `options` (object, optional):
  - `conversationId` (string): Conversation ID for context
  - `context` (object): Additional context
  - `lead` (object): Lead information

**Returns:** Promise resolving to response object

**Example:**
```javascript
const response = await Fikiri.Chatbot.query('Hello!', {
  conversationId: 'chat-123',
  lead: {
    email: 'user@example.com',
    name: 'John Doe'
  }
});
```

### `Fikiri.Chatbot.show(options)`

Show the chatbot widget.

**Parameters:**
- `options` (object, optional):
  - `theme` (string): 'light' or 'dark'
  - `position` (string): 'bottom-right', 'bottom-left', 'top-right', 'top-left'
  - `title` (string): Widget title
  - `accentColor` (string): Primary color (hex)

**Example:**
```javascript
Fikiri.Chatbot.show({
  theme: 'light',
  position: 'bottom-right',
  title: 'Chat with Us',
  accentColor: '#0f766e'
});
```

### `Fikiri.Chatbot.hide()`

Hide the chatbot widget.

**Example:**
```javascript
Fikiri.Chatbot.hide();
```

---

## 💡 Implementation Examples

### Example 1: Simple Chat Interface

```html
<!DOCTYPE html>
<html>
<head>
    <title>Simple Chat</title>
</head>
<body>
    <div id="messages"></div>
    <input type="text" id="input" placeholder="Type a message...">
    <button onclick="sendMessage()">Send</button>

    <script src="https://cdn.fikirisolutions.com/sdk/v1/fikiri-sdk.js"></script>
    <script>
        Fikiri.init({
            apiKey: 'fik_your_api_key_here',
            features: ['chatbot']
        });

        let conversationId = null;

        async function sendMessage() {
            const input = document.getElementById('input');
            const message = input.value;
            input.value = '';

            // Add user message to UI
            addMessage('user', message);

            // Query chatbot
            const response = await Fikiri.Chatbot.query(message, {
                conversationId: conversationId
            });

            if (response.success) {
                addMessage('bot', response.response);
                conversationId = response.conversation_id;
            } else {
                addMessage('bot', 'Error: ' + response.error);
            }
        }

        function addMessage(type, text) {
            const messages = document.getElementById('messages');
            const div = document.createElement('div');
            div.className = type;
            div.textContent = text;
            messages.appendChild(div);
        }
    </script>
</body>
</html>
```

### Example 2: Using Widget

```html
<!DOCTYPE html>
<html>
<head>
    <title>Chatbot Widget</title>
</head>
<body>
    <h1>My Website</h1>
    <p>Content here...</p>

    <script src="https://cdn.fikirisolutions.com/sdk/v1/fikiri-sdk.js"></script>
    <script>
        Fikiri.init({
            apiKey: 'fik_your_api_key_here',
            features: ['chatbot']
        });

        // Show chatbot widget
        Fikiri.Chatbot.show({
            theme: 'light',
            position: 'bottom-right',
            title: 'Need Help?'
        });
    </script>
</body>
</html>
```

### Example 3: React Component

```jsx
import { useState, useEffect } from 'react';

function Chatbot() {
    const [messages, setMessages] = useState([]);
    const [input, setInput] = useState('');
    const [conversationId, setConversationId] = useState(null);

    useEffect(() => {
        // Initialize SDK
        window.Fikiri.init({
            apiKey: process.env.REACT_APP_FIKIRI_API_KEY,
            features: ['chatbot']
        });
    }, []);

    const sendMessage = async () => {
        if (!input.trim()) return;

        const userMessage = input;
        setInput('');
        setMessages(prev => [...prev, { type: 'user', text: userMessage }]);

        try {
            const response = await window.Fikiri.Chatbot.query(userMessage, {
                conversationId: conversationId
            });

            if (response.success) {
                setMessages(prev => [...prev, { type: 'bot', text: response.response }]);
                if (response.conversation_id) {
                    setConversationId(response.conversation_id);
                }
            }
        } catch (error) {
            setMessages(prev => [...prev, { type: 'bot', text: 'Error: ' + error.message }]);
        }
    };

    return (
        <div className="chatbot">
            <div className="messages">
                {messages.map((msg, i) => (
                    <div key={i} className={msg.type}>
                        {msg.text}
                    </div>
                ))}
            </div>
            <div className="input-area">
                <input
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    onKeyPress={(e) => e.key === 'Enter' && sendMessage()}
                    placeholder="Type a message..."
                />
                <button onClick={sendMessage}>Send</button>
            </div>
        </div>
    );
}
```

---

## 🔐 Security

### API Key Security

1. **Never expose API keys** in client-side code for production
2. **Use environment variables** for API keys
3. **Restrict API key scopes** to only what's needed
4. **Use origin restrictions** to limit where API keys can be used

### Best Practices

```javascript
// ✅ Good: Use environment variable
Fikiri.init({
    apiKey: process.env.FIKIRI_API_KEY, // Server-side only
    features: ['chatbot']
});

// ❌ Bad: Hardcoded API key
Fikiri.init({
    apiKey: 'fik_abc123...', // Don't do this!
    features: ['chatbot']
});
```

---

## 🎯 Features

### 1. Multi-Turn Conversations

The chatbot maintains conversation context:

```javascript
// First message
const response1 = await Fikiri.Chatbot.query('What are your hours?');
// conversation_id: 'conv_123'

// Follow-up (uses context)
const response2 = await Fikiri.Chatbot.query('And on weekends?', {
    conversationId: response1.conversation_id
});
```

### 2. Lead Capture

Capture leads during conversation:

```javascript
const response = await Fikiri.Chatbot.query('I want to sign up', {
    lead: {
        email: 'user@example.com',
        name: 'John Doe',
        phone: '+1234567890'
    }
});
```

### 3. Expert Escalation

Chatbot can escalate to human experts:

```javascript
const response = await Fikiri.Chatbot.query('I need technical support');

if (response.escalated) {
    console.log('Escalated to expert:', response.expert_name);
}
```

### 4. Feedback Collection

Collect feedback on responses:

```javascript
// After getting a response
await Fikiri.Chatbot.feedback({
    conversationId: conversationId,
    messageId: messageId,
    helpful: true,
    feedbackText: 'Very helpful!'
});
```

---

## 🐛 Troubleshooting

### "API key is required"
- Make sure you've called `Fikiri.init()` with an API key
- Check that the API key starts with `fik_`

### "Network error"
- Check that your API URL is correct
- Verify CORS is configured on your API
- Check browser console for detailed error

### "Chatbot not responding"
- Check API key has `chatbot:query` scope
- Verify API endpoint is accessible
- Check Flask server logs for errors

### "Conversation context lost"
- Make sure you're passing `conversationId` in options
- Store `conversation_id` from response
- Use same `conversationId` for follow-up messages

---

## 📊 Response Structure

### Success Response

```typescript
{
  success: true,
  query: string,
  response: string,        // Main answer
  answer: string,          // Alias for response
  confidence: number,      // 0.0 - 1.0
  fallback_used: boolean,  // True if fallback answer used
  sources: string[],       // Source documents
  conversation_id: string, // For context
  follow_up?: string,      // Suggested follow-up
  escalated?: boolean,     // True if escalated to expert
  expert_name?: string     // Expert name if escalated
}
```

### Error Response

```typescript
{
  success: false,
  error: string,
  error_code: string
}
```

**Error Codes:**
- `MISSING_QUERY` - Query parameter missing
- `INVALID_API_KEY` - API key invalid or expired
- `INSUFFICIENT_SCOPE` - API key lacks required scope
- `RATE_LIMITED` - Too many requests
- `INTERNAL_ERROR` - Server error

---

## 🚀 Next Steps

1. **Test the demo** - Visit `/demo/chatbot` or `/demo/simple`
2. **Get your API key** - From dashboard settings
3. **Integrate into your site** - Use Install page (`/install`)
4. **Customize styling** - Match your brand
5. **Add lead capture** - Integrate with CRM

---

*Last updated: February 2026*
