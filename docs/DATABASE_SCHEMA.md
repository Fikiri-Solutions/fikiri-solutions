# 🗃️ Database Schema

## Core Tables

### Users Table
```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    name VARCHAR(255) NOT NULL,
    role VARCHAR(50) DEFAULT 'user',
    
    -- Business Information
    business_name VARCHAR(255),
    business_email VARCHAR(255),
    industry VARCHAR(100),
    team_size VARCHAR(50),
    
    -- Account Status
    is_active BOOLEAN DEFAULT 1,
    email_verified BOOLEAN DEFAULT 0,
    onboarding_completed BOOLEAN DEFAULT 0,
    onboarding_step INTEGER DEFAULT 1,
    
    -- Metadata
    metadata JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### OAuth Tokens Table
```sql
CREATE TABLE google_oauth_tokens (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    access_token TEXT NOT NULL,
    refresh_token TEXT,
    expires_at INTEGER,
    scope TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (user_id) REFERENCES users (id)
);
```

### OAuth States Table
```sql
CREATE TABLE oauth_states (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    state VARCHAR(255) UNIQUE NOT NULL,
    user_id INTEGER,
    redirect_url TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP DEFAULT (datetime('now', '+15 minutes')),
    
    FOREIGN KEY (user_id) REFERENCES users (id)
);
```

### Onboarding Info Table
```sql
CREATE TABLE onboarding_info (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER UNIQUE NOT NULL,
    company_name VARCHAR(255),
    company_domain VARCHAR(255),
    industry VARCHAR(100),
    team_size VARCHAR(50),
    gmail_connected BOOLEAN DEFAULT 0,
    automations_enabled BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (user_id) REFERENCES users (id)
);
```

### CRM Leads Table
```sql
CREATE TABLE crm_leads (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255) NOT NULL,
    company VARCHAR(255),
    phone VARCHAR(50),
    source VARCHAR(100),
    status VARCHAR(50) DEFAULT 'new',
    score INTEGER DEFAULT 0,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (user_id) REFERENCES users (id)
);
```

### System Alerts Table
```sql
CREATE TABLE system_alerts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    alert_type VARCHAR(100) NOT NULL,
    alert_level VARCHAR(20) DEFAULT 'info',
    message TEXT NOT NULL,
    resolved BOOLEAN DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (user_id) REFERENCES users (id)
);
```

## Service Initialization Dependencies

```
1. DATABASE_URL
   ↓ Initialize SQLite/Postgres connection
   
2. REDIS_URL (optional)
   ↓ Initialize Redis services
   
3. GOOGLE_CLIENT_ID + SECRET
   ↓ Initialize OAuth manager
   
4. OPENAI_API_KEY (optional)
   ↓ Initialize AI assistant
   
5. FERNET_KEY (optional)
   ↓ Initialize token encryption
   
6. SENTRY_DSN (optional)
   ↓ Initialize error tracking
```

## External Service Dependencies

### Required Services
- **Render Database** - User data & OAuth tokens
- **Google OAuth2** - Gmail integration
- **Your Domain** - CORS & redirects

### Optional Services
- **Redis Cloud** - Sessions & caching (falls back to memory)
- **OpenAI API** - AI features (fallback: disabled)
- **Sentry** - Error tracking (fallback: console logs)
- **Microsoft Graph** - Office integration (fallback: disabled)

### Service Health Checks
```python
# Database: SELECT 1
# Redis: ping()
# Google OAuth: token validation
# OpenAI: API key check
```
