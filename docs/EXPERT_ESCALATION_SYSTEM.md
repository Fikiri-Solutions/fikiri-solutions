# Expert Escalation & Human-in-the-Loop System

## Overview

This document describes the expert escalation system that brings human experts into the loop when the chatbot cannot confidently answer user questions. Inspired by Microsoft Teams FAQ Plus, this system enables seamless handoff from bot to human experts.

## Architecture

### Components

1. **Escalation Engine** (`core/expert_escalation.py`)
   - Detects low-confidence answers
   - Routes questions to expert teams
   - Manages assignment and handoff

2. **Expert Management** (`core/expert_manager.py`)
   - Manages expert users and teams
   - Handles expert availability and routing
   - Tracks expert performance

3. **Conversation Context** (Enhanced `core/context_aware_responses.py`)
   - Multi-turn conversation tracking
   - Context preservation across escalations
   - Conversation state management

4. **Feedback Loop** (`core/chatbot_feedback.py`)
   - Collects user feedback on answers
   - Allows experts to add Q&A pairs
   - Improves knowledge base over time

5. **Expert API** (`routes/expert_api.py`)
   - Expert dashboard endpoints
   - Q&A management interface
   - Assignment and response endpoints

## Database Schema

### expert_teams
```sql
CREATE TABLE IF NOT EXISTS expert_teams (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id TEXT NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(tenant_id, name)
);
```

### expert_team_members
```sql
CREATE TABLE IF NOT EXISTS expert_team_members (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    team_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    role TEXT DEFAULT 'expert',  -- 'expert', 'admin'
    is_active BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (team_id) REFERENCES expert_teams (id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
    UNIQUE(team_id, user_id)
);
```

### escalated_questions
```sql
CREATE TABLE IF NOT EXISTS escalated_questions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation_id TEXT NOT NULL,
    tenant_id TEXT NOT NULL,
    user_id TEXT,  -- End user who asked
    question TEXT NOT NULL,
    original_answer TEXT,
    confidence REAL,
    assigned_to INTEGER,  -- Expert user_id
    team_id INTEGER,
    status TEXT DEFAULT 'pending',  -- 'pending', 'assigned', 'in_progress', 'resolved', 'closed'
    resolution TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    assigned_at TIMESTAMP,
    resolved_at TIMESTAMP,
    FOREIGN KEY (assigned_to) REFERENCES users (id),
    FOREIGN KEY (team_id) REFERENCES expert_teams (id)
);
```

### expert_responses
```sql
CREATE TABLE IF NOT EXISTS expert_responses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    escalated_question_id INTEGER NOT NULL,
    expert_user_id INTEGER NOT NULL,
    response_text TEXT NOT NULL,
    added_to_kb BOOLEAN DEFAULT 0,
    faq_id INTEGER,  -- If added as FAQ
    kb_document_id TEXT,  -- If added as KB doc
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (escalated_question_id) REFERENCES escalated_questions (id) ON DELETE CASCADE,
    FOREIGN KEY (expert_user_id) REFERENCES users (id)
);
```

### conversation_feedback
```sql
CREATE TABLE IF NOT EXISTS conversation_feedback (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation_id TEXT NOT NULL,
    message_id TEXT,
    helpful BOOLEAN,
    feedback_text TEXT,
    user_id TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## Escalation Flow

1. **User asks question** → Chatbot processes query
2. **Confidence check** → If confidence < threshold (default 0.7), escalate
3. **Route to team** → Assign to appropriate expert team (by tenant, category, etc.)
4. **Expert notification** → Notify available experts
5. **Expert responds** → Expert provides answer via API/UI
6. **Add to KB** → Expert can add Q&A pair to knowledge base
7. **User receives answer** → Answer sent back to user
8. **Feedback loop** → User can rate answer, improving future responses

## Configuration

### Escalation Thresholds
- Default confidence threshold: 0.7
- Configurable per tenant
- Can be adjusted based on FAQ category

### Expert Routing Rules
- Round-robin assignment
- Load balancing by active assignments
- Category-based routing (if FAQ category matches expert specialty)
- Availability-based routing

## API Endpoints

### Public Chatbot (Enhanced)
- `POST /api/public/chatbot/query` - Returns escalation options when confidence low

### Expert API
- `GET /api/expert/questions` - List assigned questions
- `POST /api/expert/questions/<id>/assign` - Assign question to self
- `POST /api/expert/questions/<id>/respond` - Provide expert answer
- `POST /api/expert/questions/<id>/add-to-kb` - Add Q&A to knowledge base
- `GET /api/expert/teams` - List expert teams
- `POST /api/expert/teams` - Create expert team
- `GET /api/expert/stats` - Expert performance stats

### Feedback API
- `POST /api/chatbot/feedback` - Submit feedback on answer
- `GET /api/chatbot/feedback/<conversation_id>` - Get feedback for conversation

## Multi-Turn Conversations

Conversations maintain context across:
- Bot responses
- Escalations
- Expert interactions
- Follow-up questions

Context includes:
- Previous messages
- Escalation history
- User intent
- Resolved issues
- Pending questions

## Feedback Loop

1. **User rates answer** → Helpful/Not helpful
2. **System tracks** → Confidence vs actual helpfulness
3. **Expert reviews** → Low-rated answers reviewed by experts
4. **KB updates** → Experts add/update Q&A pairs
5. **Model improvement** → Feedback used to improve confidence scoring
