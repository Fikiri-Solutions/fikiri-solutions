# Complete Codebase Walkthrough - Fikiri Solutions
## AI-Powered Business Automation Platform

This document provides a detailed, line-by-line explanation of every important component in the Fikiri Solutions platform. Each module is broken down by purpose, structure, dependencies, and how it fits into the overall workflow.

---

## Table of Contents

1. [Foundation Files](#foundation-files)
   - [config.py](#configpy)
   - [core/database_optimization.py](#coredatabase_optimizationpy)
   - [app.py](#apppy)
2. [Core AI Pipeline](#core-ai-pipeline)
   - [core/ai/llm_router.py](#coreaillm_routerpy)
   - [core/ai/llm_client.py](#coreaillm_clientpy)
   - [email_automation/ai_assistant.py](#email_automationai_assistantpy)
3. [CRM System](#crm-system)
   - [crm/service.py](#crmservicepy)
   - [core/enhanced_crm_service.py](#coreenhanced_crm_servicepy)
4. [Automation Engine](#automation-engine)
   - [services/automation_engine.py](#servicesautomation_enginepy)
   - [core/automation_safety.py](#coreautomation_safetypy)
5. [Email Processing](#email-processing)
   - [email_automation/parser.py](#email_automationparserpy)
   - [routes/business.py (Email Endpoints)](#routesbusinesspy-email-endpoints)
6. [API Routes](#api-routes)
   - [routes/auth.py](#routesauthpy)
   - [routes/business.py](#routesbusinesspy)
   - [routes/user.py](#routesuserpy)
   - [routes/monitoring.py](#routesmonitoringpy)
7. [Frontend Architecture](#frontend-architecture)
   - [frontend/src/services/apiClient.ts](#frontendsrcservicesapiclientts)
   - [frontend/src/pages/Dashboard.tsx](#frontendsrcpagesdashboardtsx)
   - [frontend/src/pages/EmailInbox.tsx](#frontendsrcpagesemailinboxtsx)
8. [Integrations](#integrations)
   - [integrations/gmail/gmail_client.py](#integrationsgmailgmail_clientpy)
   - [core/oauth_token_manager.py](#coreoauth_token_managerpy)
9. [Data Storage & Management](#data-storage--management)
   - [Database Schema](#database-schema)
   - [Data Flow](#data-flow)
10. [Common Patterns](#common-patterns)

---

## Foundation Files

### config.py

**Purpose:** Centralized configuration management. Loads all credentials and settings from environment variables and provides them to other scripts in a structured way.

**Pipeline Role:** Foundation layer - every other script depends on this to get database, OAuth, and API credentials.

**Structure:**
- Environment-aware configuration (development vs production)
- OAuth redirect URLs
- Database URLs
- CORS settings
- Security settings

**Line-by-Line Breakdown:**

```python
import os
from typing import Optional
```
- **os:** Accesses environment variables (`os.getenv`)
- **Optional:** Type hint for values that might be `None`

```python
ENV = os.getenv("ENVIRONMENT", "development")
IS_PRODUCTION = ENV == "production"
```
- **What:** Detects environment mode (development/production)
- **Why:** Different settings for dev vs prod (URLs, security, etc.)
- **Default:** Development mode if not set

```python
class Config:
    """Centralized configuration management"""
```
- **What:** Configuration class with class methods
- **Why:** Centralized place for all settings

```python
OAUTH_REDIRECT_URL = (
    os.getenv("OAUTH_REDIRECT_URL_PROD") if IS_PRODUCTION 
    else os.getenv("OAUTH_REDIRECT_URL_DEV", "http://localhost:3000/api/oauth/gmail/callback")
)
```
- **What:** OAuth redirect URL (where Google redirects after auth)
- **Production:** Uses `OAUTH_REDIRECT_URL_PROD` env var
- **Development:** Uses `OAUTH_REDIRECT_URL_DEV` or defaults to localhost
- **Why:** OAuth requires exact URL match - different for dev/prod

```python
JWT_ACCESS_EXPIRY = int(os.getenv("JWT_ACCESS_EXPIRY", 30 * 60))  # 30 minutes
JWT_REFRESH_EXPIRY = int(os.getenv("JWT_REFRESH_EXPIRY", 7 * 24 * 60 * 60))  # 7 days
```
- **What:** JWT token expiration times
- **Access Token:** Short-lived (30 min) - used for API requests
- **Refresh Token:** Long-lived (7 days) - used to get new access tokens
- **Why:** Security - short access tokens limit damage if stolen

```python
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///data/fikiri.db")
```
- **What:** Database connection string
- **Default:** SQLite database at `data/fikiri.db`
- **Production:** Can be PostgreSQL URL (e.g., `postgresql://user:pass@host/db`)
- **Why:** SQLite for dev (simple), PostgreSQL for prod (scalable)

```python
REDIS_URL = os.getenv("REDIS_URL")
```
- **What:** Redis connection URL (optional)
- **Why:** Used for caching, sessions, queues (falls back to memory if not set)

```python
CORS_ORIGINS = [
    "https://fikirisolutions.com",
    "https://www.fikirisolutions.com",
    "http://localhost:5173",
    "http://127.0.0.1:5173"
]
```
- **What:** Allowed origins for CORS (Cross-Origin Resource Sharing)
- **Why:** Browser security - only these domains can call API
- **Production:** Production domains
- **Development:** Localhost ports (Vite dev server)

```python
SESSION_COOKIE_DOMAIN = (
    ".fikirisolutions.com" if IS_PRODUCTION
    else None
)
```
- **What:** Cookie domain for session cookies
- **Production:** `.fikirisolutions.com` (works for all subdomains)
- **Development:** `None` (localhost)
- **Why:** Cookies need domain match for security

**Dependencies:**
- `os` module (built-in)
- Environment variables (`.env` file or system env)

**How Other Scripts Use It:**
```python
from config import config
db_url = config.DATABASE_URL
oauth_url = config.get_oauth_redirect_url()
```

---

### core/database_optimization.py

**Purpose:** Provides safe, reusable functions for connecting to SQLite/PostgreSQL and executing queries. Handles connection management, error handling, query performance tracking, and result formatting.

**Pipeline Role:** Foundation layer - all scripts that need database access use this module.

**Structure:**
- Connection pooling (for PostgreSQL)
- Context manager for automatic connection cleanup
- Query executor that returns dictionaries (not raw tuples)
- Performance metrics tracking
- Automatic table creation

**Line-by-Line Breakdown:**

```python
import sqlite3
import json
import time
import logging
import os
import threading
from typing import Dict, List, Any, Optional, Tuple, Union
from dataclasses import dataclass
from datetime import datetime, timezone
from contextlib import contextmanager
```
- **sqlite3:** Built-in SQLite library
- **threading:** Thread-safe connection management
- **contextmanager:** Decorator for `with` statements
- **dataclasses:** Structured data types

```python
class DatabaseOptimizer:
    """Database optimization and performance monitoring with enterprise features"""
    
    def __init__(self, db_path: str = None, db_type: str = "sqlite"):
        if db_path is None:
            if os.path.exists("/opt/render/project/data"):
                db_path = "/opt/render/project/data/fikiri.db"
            else:
                db_path = "data/fikiri.db"
```
- **What:** Initializes database optimizer
- **Render Detection:** Checks if running on Render.com (production)
- **Render Path:** `/opt/render/project/data/fikiri.db` (persistent disk)
- **Local Path:** `data/fikiri.db` (development)
- **Why:** Different paths for different deployment environments

```python
self._check_and_repair_database()
self._initialize_database()
```
- **What:** Checks database integrity and initializes schema
- **Why:** Ensures database is healthy and tables exist

```python
def _check_and_repair_database(self):
    """Check database integrity and repair if corrupted"""
    result = conn.execute("PRAGMA integrity_check").fetchone()
    if result and result[0] == 'ok':
        logger.info("✅ Database integrity check passed")
    else:
        self._repair_database()
```
- **What:** Runs SQLite integrity check
- **PRAGMA integrity_check:** SQLite command to verify database
- **Repair:** If corrupted, backs up and recreates database
- **Why:** Prevents data corruption issues

```python
def _create_optimized_tables(self, cursor):
    """Create tables with optimized structure"""
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT NOT NULL UNIQUE,
            name TEXT NOT NULL,
            password_hash TEXT NOT NULL,
            ...
        )
    """)
```
- **What:** Creates all database tables
- **IF NOT EXISTS:** Safe to run multiple times
- **Tables Created:**
  - `users` - User accounts
  - `gmail_tokens` - OAuth tokens (encrypted)
  - `leads` - CRM leads
  - `lead_activities` - Lead interaction history
  - `automation_rules` - Automation configurations
  - `synced_emails` - Cached email data
  - And 20+ more tables

```python
def execute_query(
    self,
    sql: str,
    params: Optional[Tuple] = None,
    fetch: bool = True
) -> Union[List[Dict[str, Any]], int]:
```
- **What:** Executes SQL query with parameters
- **sql:** SQL query (can have `?` placeholders)
- **params:** Values for placeholders (prevents SQL injection)
- **fetch:** If `True`, returns results; if `False`, returns row count
- **Returns:** List of dictionaries (one per row) or row count

```python
def get_connection(self) -> sqlite3.Connection:
    """Get database connection"""
    conn = sqlite3.connect(self.db_path)
    conn.row_factory = sqlite3.Row  # Return rows as dictionaries
    return conn
```
- **What:** Creates database connection
- **row_factory:** Makes rows accessible as dictionaries (`row['column_name']`)
- **Why:** Easier to work with than tuples

```python
@contextmanager
def get_connection(self):
    """Context manager for automatic connection cleanup"""
    conn = self.get_connection()
    try:
        yield conn
    finally:
        conn.close()
```
- **What:** Context manager for connections
- **Usage:** `with db_optimizer.get_connection() as conn: ...`
- **Why:** Automatically closes connection even if error occurs

**Key Tables Created:**

1. **users** - User accounts and profiles
2. **gmail_tokens** - OAuth tokens (encrypted)
3. **leads** - CRM leads with stages and scores
4. **lead_activities** - Activity history
5. **automation_rules** - Automation configurations
6. **automation_executions** - Execution logs
7. **synced_emails** - Cached email data
8. **email_sync** - Sync job tracking
9. **onboarding_info** - User onboarding data
10. **oauth_states** - OAuth CSRF protection
11. **user_sessions** - Session management
12. **query_performance_log** - Query performance metrics

**Dependencies:**
- `sqlite3` (built-in)
- Optional: `psycopg2` for PostgreSQL support

**How Other Scripts Use It:**
```python
from core.database_optimization import db_optimizer

# Execute query
rows = db_optimizer.execute_query(
    "SELECT * FROM leads WHERE user_id = ?",
    (user_id,)
)

# Insert data
db_optimizer.execute_query(
    "INSERT INTO leads (user_id, email, name) VALUES (?, ?, ?)",
    (user_id, email, name),
    fetch=False
)
```

---

### app.py

**Purpose:** Main Flask application entry point. Initializes all services, registers blueprints, sets up middleware, and configures the application.

**Pipeline Role:** The "orchestrator" - brings everything together and starts the web server.

**Structure:**
- Application factory pattern (`create_app()`)
- Service initialization
- Blueprint registration
- Middleware setup (CORS, logging, error handling)
- Health checks

**Line-by-Line Breakdown:**

```python
from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
```
- **Flask:** Web framework
- **CORS:** Cross-Origin Resource Sharing (allows frontend to call API)

```python
from dotenv import load_dotenv
load_dotenv()
```
- **What:** Loads `.env` file for local development
- **Why:** Environment variables for local dev (not needed in production)

```python
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("logs/app.log", mode='a', encoding='utf-8')
    ]
)
```
- **What:** Configures logging
- **Format:** Timestamp, level, module name, message
- **Handlers:** Console + file logging
- **Why:** Debugging and monitoring

```python
def create_app():
    """Flask Application Factory Pattern"""
    app = Flask(__name__)
    app.secret_key = os.getenv('FLASK_SECRET_KEY', 'dev-secret-key')
```
- **What:** Creates Flask app instance
- **Factory Pattern:** Allows creating multiple app instances (testing)
- **secret_key:** Used for session encryption

```python
CORS(app, 
     resources={r"/api/*": {"origins": get_cors_origins()}},
     methods=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS', 'PATCH', 'HEAD'],
     allow_headers=['Content-Type', 'Authorization', ...],
     supports_credentials=True,
     max_age=3600
)
```
- **What:** Configures CORS
- **origins:** Allowed frontend domains
- **supports_credentials:** Allows cookies/auth headers
- **Why:** Browser security - only allows requests from approved domains

```python
def initialize_services(app):
    """Initialize all core services"""
    services['config'] = get_config()
    services['parser'] = MinimalEmailParser()
    services['gmail'] = MinimalGmailService()
    services['actions'] = MinimalEmailActions()
    services['ai_assistant'] = MinimalAIEmailAssistant()
    services['ml_scoring'] = MinimalMLScoring()
    services['vector_search'] = MinimalVectorSearch()
```
- **What:** Initializes all core services
- **Services Dictionary:** Global registry of services
- **Why:** Services available throughout app lifecycle

```python
def register_blueprints(app):
    """Register all route blueprints"""
    app.register_blueprint(auth_bp)
    app.register_blueprint(business_bp)
    app.register_blueprint(user_bp)
    app.register_blueprint(monitoring_bp)
    app.register_blueprint(onboarding_bp)
    app.register_blueprint(oauth)
    # ... more blueprints
```
- **What:** Registers all API route modules
- **Blueprints:** Flask's way to organize routes
- **Why:** Modular code organization

```python
if __name__ == "__main__":
    app = create_app()
    app.run(host='0.0.0.0', port=5000, debug=True)
```
- **What:** Entry point for local development
- **Production:** Uses Gunicorn (configured in `render.yaml`)

**Dependencies:**
- Flask and Flask extensions
- All core services
- All route blueprints

**How It's Used:**
- **Development:** `python app.py` (runs Flask dev server)
- **Production:** Gunicorn runs `app:create_app()` (WSGI server)

---

## Core AI Pipeline

### core/ai/llm_router.py

**Purpose:** Central router for all LLM operations. Implements the required 8-step pipeline: preprocess → detect_intent → choose_model → call_llm → postprocess → validate → log → return.

**Pipeline Role:** The "AI gateway" - ALL LLM calls MUST go through this router (rulepack requirement).

**Structure:**
- `LLMRouter` class
- 8-step pipeline method (`process()`)
- Model selection logic
- Cost and latency tracking

**Line-by-Line Breakdown:**

```python
from core.ai.llm_client import LLMClient
from core.ai.validators import SchemaValidator
```
- **LLMClient:** Handles actual API calls to OpenAI
- **SchemaValidator:** Validates LLM output against schemas

```python
class LLMRouter:
    """
    Central router for all LLM operations.
    Implements the required pipeline: preprocess → detect_intent → choose_model → call_llm → postprocess → validate → log → return
    """
    
    def __init__(self, api_key: Optional[str] = None):
        self.client = LLMClient(api_key)
        self.validator = SchemaValidator()
        self.trace_id = None
```
- **What:** Initializes router with client and validator
- **trace_id:** Unique ID for tracking requests
- **Why:** All LLM calls go through one place (enforces rulepack)

```python
def process(
    self,
    input_data: str,
    intent: Optional[str] = None,
    cost_budget: Optional[float] = None,
    latency_requirement: Optional[str] = None,
    output_schema: Optional[Dict[str, Any]] = None,
    context: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
```
- **What:** Main pipeline method - processes input through all 8 steps
- **input_data:** Text/prompt to process
- **intent:** Optional pre-detected intent (skips detection step)
- **cost_budget:** Maximum cost in USD
- **latency_requirement:** 'low', 'medium', or 'high'
- **output_schema:** Optional schema for validation
- **Returns:** Structured result with content, cost, latency, etc.

**Step 1: Preprocess**
```python
preprocessed = self.preprocess(input_data, context)
```
- **What:** Sanitizes input, truncates if needed, adds context
- **Why:** Ensures input is safe and formatted correctly

**Step 2: Detect Intent**
```python
if not intent:
    intent = self.detect_intent(preprocessed)
```
- **What:** Detects intent if not provided
- **Intents:** 'classification', 'email_reply', 'extraction', 'summarization'
- **Why:** Different intents use different models

**Step 3: Choose Model**
```python
model_config = self.choose_model(intent, cost_budget, latency_requirement)
model = model_config['model']
max_tokens = model_config['max_tokens']
temperature = model_config['temperature']
```
- **What:** Selects appropriate model based on intent and requirements
- **GPT-3.5-turbo:** Fast, cheap - for classification, extraction
- **GPT-4-turbo:** Smart, expensive - for complex responses
- **Why:** Cost optimization - use cheaper model when possible

**Step 4: Call LLM**
```python
llm_result = self.client.call_llm(
    model=model,
    prompt=preprocessed,
    max_tokens=max_tokens,
    temperature=temperature,
    trace_id=self.trace_id
)
```
- **What:** Makes actual API call to OpenAI
- **Returns:** Content, tokens used, cost, latency

**Step 5: Postprocess**
```python
postprocessed = self.postprocess(llm_result['content'], intent, context)
```
- **What:** Cleans up LLM output, formats for use
- **Why:** LLM output may need formatting/cleaning

**Step 6: Validate Schema**
```python
if output_schema:
    validated = self.validator.validate_schema(postprocessed, output_schema)
```
- **What:** Validates output matches expected schema
- **Why:** Ensures structured output (not free text)

**Step 7: Log Cost + Latency**
```python
logger.info(
    f"✅ AI pipeline completed",
    extra={
        'event': 'ai_pipeline_complete',
        'trace_id': self.trace_id,
        'cost_usd': llm_result['cost_usd'],
        'latency_ms': total_latency,
        ...
    }
)
```
- **What:** Logs metrics for monitoring
- **Why:** Track costs and performance

**Step 8: Return Structured Result**
```python
return {
    'success': True,
    'content': postprocessed,
    'intent': intent,
    'model': model,
    'tokens_used': llm_result['tokens_used'],
    'cost_usd': llm_result['cost_usd'],
    'latency_ms': total_latency,
    'trace_id': self.trace_id,
    'validated': validated
}
```

**Model Selection Logic:**
```python
def choose_model(self, intent: str, cost_budget: Optional[float], latency_requirement: Optional[str]) -> Dict[str, Any]:
    """Choose appropriate model based on intent and requirements"""
    
    # Classification and extraction use GPT-3.5 (cheaper)
    if intent in ['classification', 'extraction']:
        return {
            'model': 'gpt-3.5-turbo',
            'max_tokens': 500,
            'temperature': 0.3
        }
    
    # Complex responses use GPT-4 (smarter)
    if intent == 'email_reply':
        return {
            'model': 'gpt-4-turbo',
            'max_tokens': 1000,
            'temperature': 0.7
        }
    
    # Default to GPT-3.5
    return {
        'model': 'gpt-3.5-turbo',
        'max_tokens': 500,
        'temperature': 0.5
    }
```

**Dependencies:**
- `core.ai.llm_client` - OpenAI API client
- `core.ai.validators` - Schema validation

**How Other Scripts Use It:**
```python
from core.ai.llm_router import LLMRouter

router = LLMRouter()
result = router.process(
    input_data="Classify this email: ...",
    intent='classification',
    cost_budget=0.01
)

if result['success']:
    content = result['content']
    cost = result['cost_usd']
```

---

### core/ai/llm_client.py

**Purpose:** Handles actual HTTP requests to OpenAI API. Provides retry logic, error handling, and cost calculation.

**Pipeline Role:** Low-level API client - called by `LLMRouter`.

**Key Features:**
- Exponential backoff retry
- Cost calculation per model
- Token counting
- Error handling

**Structure:**
- `LLMClient` class
- `call_llm()` method
- Retry logic with exponential backoff
- Cost calculation

**Key Methods:**

**`call_llm`:**
```python
def call_llm(
    self,
    model: str,
    prompt: str,
    max_tokens: int = 500,
    temperature: float = 0.7,
    trace_id: Optional[str] = None
) -> Dict[str, Any]:
```
- **What:** Makes API call to OpenAI
- **Returns:** Content, tokens, cost, latency, success status

**Retry Logic:**
```python
max_retries = 3
for attempt in range(max_retries):
    try:
        response = openai.ChatCompletion.create(...)
        break
    except Exception as e:
        if attempt < max_retries - 1:
            wait_time = (2 ** attempt) + random.uniform(0, 1)  # Exponential backoff
            time.sleep(wait_time)
        else:
            raise
```
- **What:** Retries failed requests with exponential backoff
- **Why:** API can be temporarily unavailable

**Cost Calculation:**
```python
COST_PER_TOKEN = {
    'gpt-3.5-turbo': {'input': 0.0000015, 'output': 0.000002},
    'gpt-4-turbo': {'input': 0.00001, 'output': 0.00003}
}

cost = (input_tokens * COST_PER_TOKEN[model]['input'] + 
        output_tokens * COST_PER_TOKEN[model]['output'])
```
- **What:** Calculates cost based on tokens used
- **Why:** Track API costs per customer

**Dependencies:**
- `openai` package
- `time`, `random` for retry logic

---

### email_automation/ai_assistant.py

**Purpose:** AI-powered email assistant. Classifies emails, generates responses, extracts contact information, and summarizes threads.

**Pipeline Role:** High-level AI service - uses `LLMRouter` for all LLM calls.

**Structure:**
- `MinimalAIEmailAssistant` class
- Classification, response generation, extraction methods
- Business context loading
- Auto-lead capture

**Line-by-Line Breakdown:**

```python
from core.ai.llm_router import LLMRouter
```
- **What:** Imports LLM router (required by rulepack)
- **Why:** All LLM calls MUST go through router

```python
class MinimalAIEmailAssistant:
    def __init__(self, api_key: Optional[str] = None, services: Dict[str, Any] = None):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.router = LLMRouter(api_key=self.api_key)
        self.enabled = self.router.client.is_enabled()
```
- **What:** Initializes AI assistant with router
- **enabled:** Checks if OpenAI API key is configured
- **Why:** Can disable AI if no API key

```python
def classify_email_intent(self, email_content: str, subject: str = "") -> Dict[str, Any]:
    """Classify email intent using AI"""
    if not self.is_enabled():
        return self._fallback_classification(email_content, subject)
```
- **What:** Classifies email into categories
- **Categories:** lead_inquiry, support_request, general_info, complaint, spam
- **Fallback:** Rule-based classification if AI disabled

```python
prompt = f"""
Classify this email into one of these categories:
- lead_inquiry: Someone interested in services/products
- support_request: Technical help or issue
...

Email Subject: {subject}
Email Content: {email_content[:500]}

Respond with JSON format:
{{
    "intent": "category",
    "confidence": 0.0-1.0,
    "urgency": "low|medium|high",
    "suggested_action": "action_to_take"
}}
"""
```
- **What:** Builds classification prompt
- **Truncates:** First 500 chars (token limit)
- **JSON Format:** Structured output

```python
result = self.router.process(
    input_data=prompt,
    intent='classification',
    context={'operation': 'email_classification', 'subject': subject}
)
```
- **What:** Calls LLM router (required by rulepack)
- **intent='classification':** Uses GPT-3.5 (cheaper)
- **Why:** All LLM calls go through router

```python
if parsed_result.get("intent") == "lead_inquiry" and self.crm_service:
    self._auto_capture_lead(email_content, subject)
```
- **What:** Auto-creates lead in CRM if email is lead inquiry
- **Why:** Automatically capture leads from emails

```python
def generate_response(self, email_content: str, sender_name: str, subject: str, intent: str = "general") -> str:
    """Generate AI-powered email response"""
    business_context = self._load_business_context()
    
    prompt = f"""
    You are a professional email assistant for {business_context['company_name']}.
    
    Business Context:
    - Company: {business_context['company_name']}
    - Industry: {business_context['industry']}
    - Services: {business_context['services']}
    - Tone: {business_context['tone']}
    
    Email Details:
    - From: {sender_name}
    - Subject: {subject}
    - Content: {email_content}
    - Intent: {intent}
    
    Generate a professional response.
    """
```
- **What:** Generates email reply using business context
- **Business Context:** Loads from onboarding data or defaults
- **Why:** Personalized responses based on company info

```python
result = self.router.process(
    input_data=prompt,
    intent='email_reply',
    context={'sender': sender_name, 'subject': subject}
)
```
- **What:** Calls LLM router with 'email_reply' intent
- **Model:** Uses GPT-4 (smarter, more expensive)
- **Why:** Complex responses need better model

**Dependencies:**
- `core.ai.llm_router` (required)
- `crm.service` (optional, for auto-lead capture)

**How Other Scripts Use It:**
```python
from email_automation.ai_assistant import MinimalAIEmailAssistant

ai = MinimalAIEmailAssistant()

# Classify email
classification = ai.classify_email_intent(email_content, subject)

# Generate response
response = ai.generate_response(email_content, sender_name, subject, intent)
```

---

## CRM System

### crm/service.py

**Purpose:** Enhanced CRM service with real-time Gmail sync. Manages leads, contacts, activities, and provides analytics.

**Pipeline Role:** CRM layer - handles all lead/contact management.

**Structure:**
- `EnhancedCRMService` class
- Lead CRUD operations
- Activity tracking
- Gmail sync
- Analytics

**Key Methods:**

**`get_leads_summary`:**
```python
def get_leads_summary(self, user_id: int, filters: Dict[str, Any] = None, limit: int = 100, offset: int = 0) -> Dict[str, Any]:
    """Get comprehensive leads summary with analytics and pagination"""
    
    base_query = """SELECT id, user_id, email, name, phone, company, source, stage, score, 
                   created_at, updated_at, last_contact, notes, tags, metadata 
                   FROM leads WHERE user_id = ?"""
    
    # Apply filters
    if filters:
        if filters.get('stage'):
            base_query += " AND stage = ?"
            params.append(filters['stage'])
    
    # Add pagination
    base_query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])
```
- **What:** Gets leads with filtering and pagination
- **Pagination:** Required by rulepack (all list endpoints)
- **Filters:** By stage, time period, company
- **Returns:** Leads + analytics + pagination metadata

**`create_lead`:**
```python
def create_lead(self, user_id: int, lead_data: Dict[str, Any]) -> Dict[str, Any]:
    """Create a new lead"""
    
    # Validate required fields
    required_fields = ['email', 'name']
    for field in required_fields:
        if not lead_data.get(field):
            return {'success': False, 'error': f'Missing required field: {field}'}
    
    # Check if lead already exists
    existing = db_optimizer.execute_query(
        "SELECT id FROM leads WHERE user_id = ? AND email = ?",
        (user_id, lead_data['email'])
    )
    
    if existing:
        return {'success': False, 'error': 'Lead with this email already exists'}
    
    # Calculate lead score
    score = self._calculate_lead_score(lead_data)
    
    # Create lead
    lead_id = db_optimizer.execute_query(
        """INSERT INTO leads 
           (user_id, email, name, phone, company, source, stage, score, notes, tags, metadata) 
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (user_id, lead_data['email'], lead_data['name'], ...),
        fetch=False
    )
```
- **What:** Creates new lead with validation
- **Validation:** Required fields, duplicate check
- **Scoring:** Calculates lead score automatically
- **Returns:** Success status + lead_id

**`sync_gmail_leads`:**
```python
def sync_gmail_leads(self, user_id: int) -> Dict[str, Any]:
    """Sync leads from Gmail emails"""
    
    # Check if Gmail is connected
    gmail_token_check = db_optimizer.execute_query("""
        SELECT id, user_id, access_token_enc, refresh_token_enc, is_active
        FROM gmail_tokens 
        WHERE user_id = ? AND is_active = TRUE
    """, (user_id,))
    
    if not gmail_token_check:
        return {'success': False, 'error': 'Gmail not connected'}
    
    # Get recent email activities
    activities_data = db_optimizer.execute_query("""
        SELECT DISTINCT la.lead_id, l.email, l.name, l.company
        FROM lead_activities la
        JOIN leads l ON la.lead_id = l.id
        WHERE l.user_id = ? AND la.activity_type = 'email_received'
        AND la.timestamp >= datetime('now', '-7 days')
    """, (user_id,))
```
- **What:** Syncs leads from Gmail email activities
- **Process:** Finds email activities, creates/updates leads
- **Returns:** Sync results

**Dependencies:**
- `core.database_optimization` for database access
- `integrations.gmail.gmail_client` for Gmail sync

**How Other Scripts Use It:**
```python
from crm.service import enhanced_crm_service

# Get leads
result = enhanced_crm_service.get_leads_summary(user_id, filters={'stage': 'new'})

# Create lead
result = enhanced_crm_service.create_lead(user_id, {
    'email': 'lead@example.com',
    'name': 'John Doe',
    'company': 'Acme Corp'
})
```

---

## Automation Engine

### services/automation_engine.py

**Purpose:** Automation engine for rule-based workflows. Handles triggers, actions, and rule execution.

**Pipeline Role:** Automation layer - executes workflows based on triggers.

**Structure:**
- `AutomationEngine` class
- Trigger types (6 types)
- Action types (14 types)
- Rule execution logic

**Key Concepts:**

**Trigger Types:**
```python
class TriggerType(Enum):
    EMAIL_RECEIVED = "email_received"
    EMAIL_SENT = "email_sent"
    LEAD_CREATED = "lead_created"
    LEAD_STAGE_CHANGED = "lead_stage_changed"
    TIME_BASED = "time_based"
    KEYWORD_DETECTED = "keyword_detected"
```
- **What:** Types of events that trigger automations
- **Why:** Different triggers need different handling

**Action Types:**
```python
class ActionType(Enum):
    SEND_EMAIL = "send_email"
    UPDATE_LEAD_STAGE = "update_lead_stage"
    ADD_LEAD_ACTIVITY = "add_lead_activity"
    APPLY_LABEL = "apply_label"
    ARCHIVE_EMAIL = "archive_email"
    CREATE_TASK = "create_task"
    SEND_NOTIFICATION = "send_notification"
    SCHEDULE_FOLLOW_UP = "schedule_follow_up"
    CREATE_CALENDAR_EVENT = "create_calendar_event"
    UPDATE_CRM_FIELD = "update_crm_field"
    TRIGGER_WEBHOOK = "trigger_webhook"
    GENERATE_DOCUMENT = "generate_document"
    SEND_SMS = "send_sms"
    CREATE_INVOICE = "create_invoice"
    ASSIGN_TEAM_MEMBER = "assign_team_member"
```
- **What:** Actions that can be executed
- **Status:** Some fully implemented, some stubs (see production readiness audit)

**Rule Execution:**
```python
def execute_automation_rules(self, trigger_type: TriggerType, trigger_data: Dict[str, Any], user_id: int) -> Dict[str, Any]:
    """Execute automation rules based on trigger"""
    
    # Get active rules for trigger type
    rules_data = db_optimizer.execute_query(
        """SELECT id, user_id, name, description, trigger_type, trigger_conditions, 
           action_type, action_parameters, status, created_at, updated_at, 
           last_executed, execution_count, success_count, error_count 
           FROM automation_rules 
           WHERE user_id = ? AND trigger_type = ? AND status = ?""",
        (user_id, trigger_type.value, AutomationStatus.ACTIVE.value)
    )
    
    executed_rules = []
    failed_rules = []
    
    for rule_data in rules_data:
        rule = self._format_rule(rule_data)
        
        # Check if trigger conditions are met
        if self._check_trigger_conditions(rule, trigger_data):
            # Execute rule
            execution_result = self._execute_rule(rule, trigger_data)
            
            if execution_result['success']:
                executed_rules.append({
                    'rule_id': rule.id,
                    'rule_name': rule.name,
                    'result': execution_result['data']
                })
            else:
                failed_rules.append({
                    'rule_id': rule.id,
                    'rule_name': rule.name,
                    'error': execution_result['error']
                })
```
- **What:** Executes all active rules for a trigger
- **Process:**
  1. Get active rules for trigger type
  2. Check if conditions are met
  3. Execute action
  4. Log results
- **Returns:** List of executed/failed rules

**Action Handlers:**
```python
self.action_handlers = {
    ActionType.SEND_EMAIL: self._execute_send_email,
    ActionType.UPDATE_LEAD_STAGE: self._execute_update_lead_stage,
    ActionType.ADD_LEAD_ACTIVITY: self._execute_add_lead_activity,
    # ... more handlers
}
```
- **What:** Maps action types to handler functions
- **Status:** Some handlers are stubs (see production readiness audit)

**Dependencies:**
- `core.database_optimization` for database access
- `crm.service` for CRM operations
- `integrations.gmail.gmail_client` for email actions (if implemented)

**How Other Scripts Use It:**
```python
from services.automation_engine import automation_engine, TriggerType

# Execute rules when email received
result = automation_engine.execute_automation_rules(
    TriggerType.EMAIL_RECEIVED,
    {
        'sender_email': 'lead@example.com',
        'subject': 'Interested in services',
        'text': 'Hi, I need help'
    },
    user_id
)
```

---

## Email Processing

### email_automation/parser.py

**Purpose:** Parses email content from Gmail API. Extracts headers, body, attachments, and formats for use.

**Pipeline Role:** Email processing layer - converts Gmail API format to internal format.

**Key Features:**
- HTML/plain text extraction
- Header parsing
- Attachment detection
- Thread handling

**Structure:**
- `MinimalEmailParser` class
- `parse_email()` method
- Header extraction
- Body extraction (HTML/plain text)

**Key Methods:**

**`parse_email`:**
```python
def parse_email(self, message: Dict[str, Any]) -> Dict[str, Any]:
    """Parse Gmail API message into structured format"""
    
    headers = message['payload'].get('headers', [])
    subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject')
    from_header = next((h['value'] for h in headers if h['name'] == 'From'), 'Unknown')
    date = next((h['value'] for h in headers if h['name'] == 'Date'), '')
    
    # Extract body
    body = self._extract_body(message['payload'])
    
    return {
        'id': message['id'],
        'subject': subject,
        'from': from_header,
        'date': date,
        'body': body,
        'unread': 'UNREAD' in message.get('labelIds', []),
        'has_attachments': self._has_attachments(message['payload'])
    }
```
- **What:** Parses Gmail API message
- **Returns:** Structured email data

**`_extract_body`:**
```python
def _extract_body(self, payload: Dict[str, Any]) -> str:
    """Extract body from message payload (prefers HTML, falls back to plain text)"""
    
    body_html = ''
    body_text = ''
    
    def extract_from_part(part):
        nonlocal body_html, body_text
        mime_type = part.get('mimeType', '')
        
        if mime_type == 'text/html':
            data = part.get('body', {}).get('data', '')
            if data and not body_html:
                body_html = base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
        elif mime_type == 'text/plain':
            data = part.get('body', {}).get('data', '')
            if data and not body_text:
                body_text = base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
        
        # Recursively check nested parts
        if 'parts' in part:
            for subpart in part['parts']:
                extract_from_part(subpart)
    
    if 'parts' in payload:
        for part in payload['parts']:
            extract_from_part(part)
    else:
        extract_from_part(payload)
    
    return body_html if body_html else body_text
```
- **What:** Extracts email body (prefers HTML)
- **Recursive:** Handles multipart messages
- **Base64:** Decodes Gmail API base64 encoding
- **Why:** HTML emails can contain images and formatting

**Dependencies:**
- `base64` (built-in) for decoding
- Gmail API message format

**How Other Scripts Use It:**
```python
from email_automation.parser import MinimalEmailParser

parser = MinimalEmailParser()
parsed = parser.parse_email(gmail_message)
```

---

### routes/business.py (Email Endpoints)

**Purpose:** API endpoints for email operations. Handles email fetching, syncing, archiving, and AI analysis.

**Pipeline Role:** API layer - exposes email functionality to frontend.

**Key Endpoints:**

**`GET /api/business/emails`:**
```python
@business_bp.route('/business/emails', methods=['GET'])
def get_emails():
    """Get emails for authenticated user"""
    
    user_id = get_current_user_id()
    filter_type = request.args.get('filter', 'all')  # all, unread, read
    limit = request.args.get('limit', 50, type=int)
    offset = request.args.get('offset', 0, type=int)
    use_synced = request.args.get('use_synced', 'true').lower() == 'true'
    
    # Try synced emails first (faster)
    if use_synced:
        synced_emails_data = db_optimizer.execute_query("""
            SELECT gmail_id, subject, sender, recipient, date, body, labels
            FROM synced_emails 
            WHERE user_id = ?
            ORDER BY date DESC
            LIMIT ? OFFSET ?
        """, (user_id, limit, offset))
        
        if synced_emails_data:
            return create_success_response({'emails': emails, 'source': 'synced'})
    
    # Fallback to Gmail API
    gmail_service = gmail_client.get_gmail_service_for_user(user_id)
    results = gmail_service.users().messages().list(userId='me', q=query, maxResults=limit).execute()
    
    # Process messages...
```
- **What:** Gets emails for user
- **Synced First:** Uses cached emails if available (faster)
- **Fallback:** Uses Gmail API if no cached data
- **Pagination:** Required by rulepack

**`POST /api/ai/analyze-email`:**
```python
@business_bp.route('/ai/analyze-email', methods=['POST'])
def analyze_email():
    """Analyze email with AI"""
    
    data = request.get_json()
    email_content = data.get('content', '')
    subject = data.get('subject', '')
    
    ai_assistant = MinimalAIEmailAssistant()
    classification = ai_assistant.classify_email_intent(email_content, subject)
    
    return create_success_response(classification)
```
- **What:** Analyzes email with AI
- **Returns:** Intent, urgency, suggested action

**`POST /api/ai/generate-reply`:**
```python
@business_bp.route('/ai/generate-reply', methods=['POST'])
def generate_reply():
    """Generate AI reply for email"""
    
    data = request.get_json()
    content = data.get('content', '')
    sender_name = data.get('from', '').split('<')[0].strip()
    subject = data.get('subject', '')
    
    ai_assistant = MinimalAIEmailAssistant()
    classification = ai_assistant.classify_email_intent(content, subject)
    intent = classification.get('intent', 'general')
    
    reply = ai_assistant.generate_response(content, sender_name, subject, intent)
    
    return create_success_response({'reply': reply})
```
- **What:** Generates AI reply
- **Process:** Classifies email, then generates response
- **Returns:** Generated reply text

**Dependencies:**
- `email_automation.ai_assistant` for AI
- `integrations.gmail.gmail_client` for Gmail API
- `core.database_optimization` for synced emails

---

## API Routes

### routes/auth.py

**Purpose:** Authentication endpoints. Handles login, signup, password reset, and OAuth flows.

**Pipeline Role:** Authentication layer - secures all other endpoints.

**Key Endpoints:**

**`POST /api/auth/signup`:**
```python
@auth_bp.route('/auth/signup', methods=['POST'])
def signup():
    """Create new user account"""
    
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')
    name = data.get('name')
    
    # Validate
    if not all([email, password, name]):
        return create_error_response("Missing required fields", 400)
    
    # Check if user exists
    existing = db_optimizer.execute_query(
        "SELECT id FROM users WHERE email = ?",
        (email,)
    )
    
    if existing:
        return create_error_response("User already exists", 409)
    
    # Hash password
    password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    
    # Create user
    user_id = db_optimizer.execute_query(
        """INSERT INTO users (email, name, password_hash) 
           VALUES (?, ?, ?)""",
        (email, name, password_hash),
        fetch=False
    )
    
    # Generate JWT token
    token = jwt_manager.generate_access_token(user_id)
    
    return create_success_response({'token': token, 'user_id': user_id})
```
- **What:** Creates new user account
- **Validation:** Checks required fields, duplicate email
- **Password:** Hashed with bcrypt
- **Returns:** JWT token for authentication

**`POST /api/auth/login`:**
```python
@auth_bp.route('/auth/login', methods=['POST'])
def login():
    """Authenticate user and return JWT token"""
    
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')
    
    # Get user
    user = db_optimizer.execute_query(
        "SELECT id, email, password_hash FROM users WHERE email = ? AND is_active = 1",
        (email,)
    )
    
    if not user:
        return create_error_response("Invalid credentials", 401)
    
    # Verify password
    if not bcrypt.checkpw(password.encode(), user[0]['password_hash'].encode()):
        return create_error_response("Invalid credentials", 401)
    
    # Generate tokens
    access_token = jwt_manager.generate_access_token(user[0]['id'])
    refresh_token = jwt_manager.generate_refresh_token(user[0]['id'])
    
    return create_success_response({
        'access_token': access_token,
        'refresh_token': refresh_token,
        'user_id': user[0]['id']
    })
```
- **What:** Authenticates user
- **Password:** Verified with bcrypt
- **Returns:** Access + refresh tokens

**Dependencies:**
- `core.jwt_auth` for JWT tokens
- `core.database_optimization` for user storage
- `bcrypt` for password hashing

---

### routes/business.py

**Purpose:** Business logic endpoints. Handles CRM, automations, emails, and AI operations.

**Pipeline Role:** Business API layer - exposes core functionality.

**Key Endpoints:**

**CRM Endpoints:**
- `GET /api/crm/leads` - Get leads with pagination
- `POST /api/crm/leads` - Create lead
- `PUT /api/crm/leads/<id>` - Update lead
- `DELETE /api/crm/leads/<id>` - Delete lead
- `POST /api/crm/sync-gmail` - Sync Gmail to CRM

**Automation Endpoints:**
- `GET /api/automation/rules` - Get automation rules
- `POST /api/automation/rules` - Create automation rule
- `PUT /api/automation/rules/<id>` - Update automation rule
- `DELETE /api/automation/rules/<id>` - Delete automation rule
- `POST /api/automation/execute` - Execute automation rules
- `GET /api/automation/logs` - Get execution logs

**Email Endpoints:**
- `GET /api/business/emails` - Get emails
- `POST /api/email/archive` - Archive email
- `POST /api/ai/analyze-email` - Analyze email with AI
- `POST /api/ai/generate-reply` - Generate AI reply

**Dependencies:**
- `crm.service` for CRM operations
- `services.automation_engine` for automations
- `email_automation.ai_assistant` for AI
- `integrations.gmail.gmail_client` for Gmail

---

### routes/user.py

**Purpose:** User management endpoints. Handles profile, onboarding, dashboard data, and data export.

**Pipeline Role:** User API layer - user-specific operations.

**Key Endpoints:**

**`GET /api/user/profile`:**
```python
@user_bp.route('/user/profile', methods=['GET'])
def get_profile():
    """Get user profile"""
    
    user_id = get_current_user_id()
    user = db_optimizer.execute_query(
        "SELECT id, email, name, business_name, industry, onboarding_completed FROM users WHERE id = ?",
        (user_id,)
    )
    
    return create_success_response(user[0] if user else {})
```

**`GET /api/user/dashboard-data`:**
```python
@user_bp.route('/user/dashboard-data', methods=['GET'])
def get_dashboard_data():
    """Get aggregated dashboard data"""
    
    user_id = get_current_user_id()
    
    # Get CRM stats
    leads = enhanced_crm_service.get_leads(user_id)
    dashboard_data['quick_stats']['total_leads'] = len(leads or [])
    
    # Get Gmail status
    gmail_status = oauth_token_manager.get_token_status(user_id, 'gmail')
    dashboard_data['quick_stats']['gmail_connected'] = gmail_status['success']
    
    return create_success_response(dashboard_data)
```

**`POST /api/user/export-data`:**
```python
@user_bp.route('/user/export-data', methods=['POST'])
def export_user_data():
    """Export user's data for GDPR compliance"""
    
    user_id = get_current_user_id()
    
    # Export all user data
    data = {
        'user': get_user_data(user_id),
        'leads': get_leads_data(user_id),
        'emails': get_emails_data(user_id),
        'activities': get_activities_data(user_id)
    }
    
    return create_success_response(data)
```

---

## Frontend Architecture

### frontend/src/services/apiClient.ts

**Purpose:** TypeScript API client for connecting React frontend to Flask backend. Handles all HTTP requests, authentication, error handling, and caching.

**Pipeline Role:** Frontend API layer - all frontend → backend communication goes through this.

**Structure:**
- `ApiClient` class
- Axios instance with interceptors
- Type-safe API methods
- Error handling
- Cache management

**Line-by-Line Breakdown:**

```typescript
import axios, { AxiosInstance, AxiosResponse } from 'axios'
import { config } from '../config'
```
- **axios:** HTTP client library
- **config:** Frontend configuration (API URL, etc.)

```typescript
const API_BASE_URL = config.apiUrl
```
- **What:** Base URL for API (e.g., `https://fikirisolutions.onrender.com`)
- **Why:** Centralized configuration

```typescript
class ApiClient {
  private client: AxiosInstance

  constructor() {
    this.client = axios.create({
      baseURL: API_BASE_URL,
      timeout: 10000,
      withCredentials: true,
      headers: {
        'Content-Type': 'application/json',
        ...cacheManager.getCacheHeaders()
      },
    })
```
- **What:** Creates Axios instance
- **withCredentials:** Sends cookies/auth headers
- **timeout:** 10 second timeout
- **Cache Headers:** Cache invalidation headers

```typescript
this.client.interceptors.request.use(
  (config) => {
    // Add JWT token to requests
    const token = localStorage.getItem('fikiri-token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  }
)
```
- **What:** Request interceptor - adds auth token
- **Why:** Automatically includes token in all requests

```typescript
this.client.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Handle unauthorized - redirect to login
      localStorage.removeItem('fikiri-token')
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)
```
- **What:** Response interceptor - handles errors
- **401:** Unauthorized - clears token, redirects to login
- **Why:** Automatic error handling

**Key Methods:**

**`getLeads`:**
```typescript
async getLeads(filters?: { stage?: string }): Promise<LeadData[]> {
  const response = await this.client.get('/api/crm/leads', { params: filters })
  return response.data.data.leads || []
}
```

**`getEmails`:**
```typescript
async getEmails(options?: { filter?: string, limit?: number, use_synced?: boolean }): Promise<{ emails: Email[], source: string }> {
  const response = await this.client.get('/api/business/emails', { params: options })
  return response.data.data
}
```

**`getMetrics`:**
```typescript
async getMetrics(): Promise<MetricData> {
  const response = await this.client.get('/api/dashboard/metrics')
  return response.data.data
}
```

**Dependencies:**
- `axios` package
- `config.ts` for API URL
- `localStorage` for token storage

**How Components Use It:**
```typescript
import { apiClient } from '../services/apiClient'

const leads = await apiClient.getLeads({ stage: 'new' })
const emails = await apiClient.getEmails({ filter: 'unread' })
```

---

### frontend/src/pages/Dashboard.tsx

**Purpose:** Main dashboard page. Displays metrics, service status, activity feed, and charts.

**Pipeline Role:** Frontend dashboard - displays aggregated data.

**Structure:**
- React functional component
- React Query for data fetching
- Real-time updates (WebSocket optional)
- Charts (Recharts)

**Key Features:**

**Data Fetching:**
```typescript
const { data: servicesData = [], isLoading: servicesLoading } = useQuery({
  queryKey: ['services'],
  queryFn: () => apiClient.getServices(),
  staleTime: 2 * 60 * 1000, // 2 minutes
  refetchInterval: 5 * 60 * 1000, // Auto-refresh every 5 minutes
})

const { data: metricsData = mockMetrics, isLoading: metricsLoading } = useQuery({
  queryKey: ['metrics'],
  queryFn: () => apiClient.getMetrics(),
  staleTime: 30 * 1000, // 30 seconds
  refetchInterval: 60 * 1000, // Auto-refresh every minute
})
```
- **React Query:** Handles caching, refetching, loading states
- **staleTime:** How long data is considered fresh
- **refetchInterval:** Auto-refresh interval

**Metrics Display:**
```typescript
<EnhancedMetricCard
  title="Total Leads"
  value={metrics?.activeLeads || 0}
  icon={<Users className="h-5 w-5" />}
  onClick={() => navigate('/crm')}
  description="Total active leads in your CRM"
  businessImpact="More leads = More opportunities"
  color="blue"
>
  <MiniTrend data={transformedTimeseriesData.map(d => d.leads)} />
</EnhancedMetricCard>
```
- **What:** Displays metric card with trend
- **Clickable:** Navigates to CRM page
- **Trend:** Shows mini trend chart

**Dependencies:**
- `@tanstack/react-query` for data fetching
- `apiClient` for API calls
- `recharts` for charts

---

### frontend/src/pages/EmailInbox.tsx

**Purpose:** Email inbox page. Displays emails, allows viewing, searching, filtering, AI analysis, and replying.

**Pipeline Role:** Frontend email interface - email management UI.

**Key Features:**

**Email Loading:**
```typescript
const { 
  data: emailsData, 
  isLoading: loading, 
  refetch: refetchEmails 
} = useQuery({
  queryKey: ['emails', user?.id, filter],
  queryFn: async () => {
    // Try synced emails first (faster)
    try {
      const syncedData = await apiClient.getEmails({ filter, limit: 50, use_synced: true })
      if (syncedData?.emails && syncedData.emails.length > 0) {
        return { ...syncedData, source: 'synced' }
      }
    } catch (e) {
      // Fallback to Gmail API
    }
    
    const data = await apiClient.getEmails({ filter, limit: 50 })
    return { ...data, source: 'gmail_api' }
  },
  staleTime: 1 * 60 * 1000, // 1 minute
  refetchInterval: 2 * 60 * 1000, // Auto-refresh every 2 minutes
})
```
- **Synced First:** Uses cached emails for speed
- **Fallback:** Uses Gmail API if no cache
- **Auto-refresh:** Refetches every 2 minutes

**AI Analysis:**
```typescript
const analyzeEmail = async (email: Email) => {
  setAiLoading(true)
  try {
    const result = await apiClient.analyzeEmail({
      content: email.body || '',
      subject: email.subject
    })
    setAiAnalysis(result)
  } catch (error) {
    addToast({ type: 'error', title: 'Analysis Failed' })
  } finally {
    setAiLoading(false)
  }
}
```
- **What:** Analyzes email with AI
- **Shows:** Intent, urgency, suggested action

**Email Rendering:**
```typescript
const EmailBodyRenderer: React.FC<{ content: string }> = ({ content }) => {
  const isHTML = /<[a-z][\s\S]*>/i.test(content)
  
  if (isHTML) {
    const sanitizedHTML = DOMPurify.sanitize(content, {
      ALLOWED_TAGS: ['p', 'br', 'div', 'strong', 'em', 'a', 'img', ...],
      ALLOWED_ATTR: ['href', 'src', 'alt', ...]
    })
    
    return <div dangerouslySetInnerHTML={{ __html: sanitizedHTML }} />
  } else {
    return <div className="whitespace-pre-wrap">{content}</div>
  }
}
```
- **What:** Renders email body (HTML or plain text)
- **DOMPurify:** Sanitizes HTML for security
- **Why:** Prevents XSS attacks

**Dependencies:**
- `@tanstack/react-query` for data fetching
- `apiClient` for API calls
- `DOMPurify` for HTML sanitization

---

## Integrations

### integrations/gmail/gmail_client.py

**Purpose:** Gmail API client. Handles OAuth, email fetching, sending, and Gmail operations.

**Pipeline Role:** Gmail integration layer - all Gmail operations go through this.

**Structure:**
- `GmailClient` class
- OAuth token management
- Email operations
- Label management

**Key Methods:**

**`get_gmail_service_for_user`:**
```python
def get_gmail_service_for_user(user_id: int):
    """Get Gmail API service for user"""
    
    # Get tokens from database
    tokens = db_optimizer.execute_query("""
        SELECT access_token_enc, refresh_token_enc, expires_at, is_active
        FROM gmail_tokens 
        WHERE user_id = ? AND is_active = 1
        ORDER BY updated_at DESC LIMIT 1
    """, (user_id,))
    
    if not tokens:
        raise RuntimeError("Gmail not connected for user")
    
    # Decrypt tokens
    access_token = decrypt_token(tokens[0]['access_token_enc'])
    refresh_token = decrypt_token(tokens[0]['refresh_token_enc'])
    
    # Build credentials
    credentials = Credentials(
        token=access_token,
        refresh_token=refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=os.getenv("GOOGLE_CLIENT_ID"),
        client_secret=os.getenv("GOOGLE_CLIENT_SECRET")
    )
    
    # Refresh if expired
    if credentials.expired:
        credentials.refresh(Request())
        # Save refreshed token
    
    # Build service
    return build('gmail', 'v1', credentials=credentials)
```
- **What:** Gets Gmail API service for user
- **Token Management:** Gets, decrypts, refreshes tokens
- **Returns:** Gmail API service object

**`sync_emails`:**
```python
def sync_emails(self, user_id: int, max_results: int = 100) -> Dict[str, Any]:
    """Sync emails from Gmail to local database"""
    
    service = self.get_gmail_service_for_user(user_id)
    
    # Get messages
    results = service.users().messages().list(
        userId='me',
        maxResults=max_results
    ).execute()
    
    messages = results.get('messages', [])
    synced_count = 0
    
    for msg in messages:
        # Get full message
        msg_detail = service.users().messages().get(
            userId='me',
            id=msg['id'],
            format='full'
        ).execute()
        
        # Parse and store
        parsed = parser.parse_email(msg_detail)
        
        db_optimizer.execute_query("""
            INSERT OR REPLACE INTO synced_emails 
            (user_id, gmail_id, subject, sender, recipient, date, body, labels)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (user_id, parsed['id'], parsed['subject'], ...), fetch=False)
        
        synced_count += 1
    
    return {'success': True, 'synced': synced_count}
```
- **What:** Syncs emails from Gmail to local database
- **Why:** Faster loading (uses cached data)

**Dependencies:**
- `googleapiclient.discovery` for Gmail API
- `google.oauth2.credentials` for OAuth
- `core.database_optimization` for token storage

---

### core/oauth_token_manager.py

**Purpose:** OAuth token management. Handles token storage, refresh, and validation.

**Pipeline Role:** OAuth layer - manages all OAuth tokens.

**Key Methods:**

**`store_tokens`:**
```python
def store_tokens(self, user_id: int, provider: str, access_token: str, refresh_token: str, expires_at: datetime):
    """Store OAuth tokens (encrypted)"""
    
    # Encrypt tokens
    access_token_enc = encrypt_token(access_token)
    refresh_token_enc = encrypt_token(refresh_token)
    
    # Store in database
    db_optimizer.execute_query("""
        INSERT OR REPLACE INTO oauth_tokens 
        (user_id, provider, access_token_enc, refresh_token_enc, expires_at, updated_at)
        VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
    """, (user_id, provider, access_token_enc, refresh_token_enc, expires_at.isoformat()), fetch=False)
```

**`refresh_tokens`:**
```python
def refresh_tokens(self, user_id: int, provider: str) -> Dict[str, Any]:
    """Refresh expired OAuth tokens"""
    
    # Get refresh token
    tokens = db_optimizer.execute_query("""
        SELECT refresh_token_enc FROM oauth_tokens 
        WHERE user_id = ? AND provider = ?
    """, (user_id, provider))
    
    refresh_token = decrypt_token(tokens[0]['refresh_token_enc'])
    
    # Refresh via OAuth provider
    new_tokens = oauth_client.refresh_access_token(refresh_token)
    
    # Store new tokens
    self.store_tokens(user_id, provider, new_tokens['access_token'], ...)
    
    return {'success': True}
```

**Dependencies:**
- `core.database_optimization` for token storage
- `cryptography` for encryption

---

## Data Storage & Management

### Database Schema

**Core Tables:**

1. **users** - User accounts
   - `id`, `email`, `name`, `password_hash`
   - `business_name`, `industry`, `team_size`
   - `onboarding_completed`, `onboarding_step`

2. **gmail_tokens** - OAuth tokens (encrypted)
   - `user_id`, `access_token_enc`, `refresh_token_enc`
   - `expires_at`, `is_active`

3. **leads** - CRM leads
   - `id`, `user_id`, `email`, `name`, `phone`, `company`
   - `source`, `stage`, `score`
   - `created_at`, `updated_at`, `last_contact`

4. **lead_activities** - Activity history
   - `id`, `lead_id`, `activity_type`, `description`
   - `timestamp`, `metadata`

5. **automation_rules** - Automation configurations
   - `id`, `user_id`, `name`, `description`
   - `trigger_type`, `trigger_conditions`
   - `action_type`, `action_parameters`
   - `status`, `execution_count`, `success_count`, `error_count`

6. **synced_emails** - Cached email data
   - `id`, `user_id`, `gmail_id`, `subject`, `sender`, `recipient`
   - `date`, `body`, `labels`

7. **onboarding_info** - User onboarding data
   - `id`, `user_id`, `company`, `industry`, `team_size`

**Storage Locations:**
- **Development:** `data/fikiri.db` (SQLite)
- **Production:** `/opt/render/project/data/fikiri.db` (Render persistent disk)
- **PostgreSQL:** Can use `DATABASE_URL` env var for PostgreSQL

---

### Data Flow

**Email Processing Flow:**
```
1. User connects Gmail → OAuth flow → Store tokens
2. User clicks "Sync Emails" → Gmail API → Parse emails → Store in synced_emails
3. User views inbox → Load from synced_emails (fast) or Gmail API (fallback)
4. User clicks "AI Analyze" → AI Assistant → LLM Router → OpenAI API → Display results
5. User clicks "Generate Reply" → AI Assistant → LLM Router → OpenAI API → Display reply
```

**CRM Flow:**
```
1. Email received → AI classifies as "lead_inquiry" → Auto-create lead
2. User views CRM → Load leads from database → Display pipeline
3. User updates lead stage → Update database → Trigger automations
4. Automation triggered → Execute rules → Update lead/activities
```

**Automation Flow:**
```
1. Event occurs (email received, lead created, etc.)
2. Automation engine checks active rules
3. If trigger conditions met → Execute action
4. Log execution → Update rule stats
5. Return results
```

---

## Common Patterns

### Configuration Loading
```python
from config import config
db_url = config.DATABASE_URL
oauth_url = config.get_oauth_redirect_url()
```

### Database Queries
```python
from core.database_optimization import db_optimizer

# Select with pagination
rows = db_optimizer.execute_query(
    "SELECT id, email, name FROM leads WHERE user_id = ? LIMIT ? OFFSET ?",
    (user_id, limit, offset)
)

# Insert
db_optimizer.execute_query(
    "INSERT INTO leads (user_id, email, name) VALUES (?, ?, ?)",
    (user_id, email, name),
    fetch=False
)
```

### AI Calls (Required Pattern)
```python
from core.ai.llm_router import LLMRouter

router = LLMRouter()
result = router.process(
    input_data=prompt,
    intent='classification',
    cost_budget=0.01
)

if result['success']:
    content = result['content']
    cost = result['cost_usd']
```

### API Endpoints
```python
from flask import Blueprint, request, jsonify
from core.api_validation import handle_api_errors, create_success_response, create_error_response
from core.secure_sessions import get_current_user_id

@business_bp.route('/api/endpoint', methods=['GET'])
@handle_api_errors
def endpoint():
    user_id = get_current_user_id()
    if not user_id:
        return create_error_response("Authentication required", 401)
    
    # Business logic
    result = some_service.do_something(user_id)
    
    return create_success_response(result, 'Success message')
```

### Frontend API Calls
```typescript
import { apiClient } from '../services/apiClient'

const { data, isLoading } = useQuery({
  queryKey: ['resource', id],
  queryFn: () => apiClient.getResource(id),
  staleTime: 2 * 60 * 1000,
  refetchInterval: 5 * 60 * 1000
})
```

---

## Dependencies Summary

**Python Packages (requirements.txt):**
- `flask` - Web framework
- `flask-cors` - CORS support
- `sqlite3` - Database (built-in)
- `psycopg2` - PostgreSQL support (optional)
- `openai` - OpenAI API client
- `google-api-python-client` - Google APIs
- `bcrypt` - Password hashing
- `python-dotenv` - Environment variables
- `redis` - Redis client (optional)
- `sentence-transformers` - Vector embeddings (optional)

**Frontend Packages (package.json):**
- `react` - UI framework
- `react-router-dom` - Routing
- `@tanstack/react-query` - Data fetching
- `axios` - HTTP client
- `dompurify` - HTML sanitization
- `recharts` - Charts
- `lucide-react` - Icons

**External Services:**
- OpenAI API (for AI)
- Gmail API (for email)
- Render.com (hosting)
- Vercel (frontend hosting)
- Redis Cloud (optional, for caching)

---

## Pipeline Flow Summary

**User Onboarding:**
1. User signs up → `routes/auth.py` → Create user → Store in database
2. User completes onboarding → `routes/user.py` → Store onboarding data
3. User connects Gmail → `core/app_oauth.py` → OAuth flow → Store tokens

**Email Processing:**
1. User syncs emails → `routes/business.py` → `integrations/gmail/gmail_client.py` → Gmail API → Parse → Store
2. User views inbox → `routes/business.py` → Load from `synced_emails` → Return to frontend
3. User analyzes email → `routes/business.py` → `email_automation/ai_assistant.py` → `core/ai/llm_router.py` → OpenAI API → Return classification

**CRM Operations:**
1. User views CRM → `routes/business.py` → `crm/service.py` → Query `leads` table → Return leads
2. User creates lead → `routes/business.py` → `crm/service.py` → Insert into `leads` → Return success
3. User updates lead → `routes/business.py` → `crm/service.py` → Update `leads` → Trigger automations

**Automation Execution:**
1. Event occurs → `services/automation_engine.py` → Check active rules → Execute actions
2. Action executed → Log to `automation_executions` → Update rule stats → Return results

---

## Next Steps for Development

1. **Complete Automation Actions:** Implement email sending, SMS, calendar, webhooks (see production readiness audit)
2. **Add Integration UI:** Build UI for managing integrations
3. **Enhance AI Context:** Connect onboarding data to AI prompts
4. **Add Data Cleanup:** Implement automatic cleanup of old data
5. **Add Backups:** Implement automated database backups
6. **Complete Chatbot:** Add web widget and deployment (see production readiness audit)

---

*End of Codebase Walkthrough*
