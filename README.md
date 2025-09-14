# Fikiri Solutions - Gmail Lead Responder

A modular AI automation platform focused on helping small businesses streamline workflows using Gmail API, email processing, and automated responses.

## 🚀 Features

- **Gmail API Integration**: Secure OAuth2 authentication and full Gmail API access
- **Email Processing**: Comprehensive email parsing with MIME support
- **Automated Responses**: Template-based automatic reply system
- **Email Management**: Mark as read/unread, archive, delete, star, and label operations
- **CLI Interface**: Easy-to-use command-line interface
- **Configuration Management**: Flexible configuration with environment variable support
- **Type Safety**: Full type hints throughout the codebase
- **Modular Design**: Clean, extensible architecture for future integrations

## 📁 Project Structure

```
fikiri_gmail_assistant/
├── core/
│   ├── auth.py          # Gmail API authentication
│   ├── gmail_utils.py   # Gmail service operations
│   ├── email_parser.py  # Email parsing and MIME handling
│   ├── actions.py       # Email management operations
│   └── config.py        # Configuration management
├── auth/
│   ├── credentials.json # Google OAuth2 credentials (you provide)
│   └── token.pkl        # Authentication token (auto-generated)
├── main.py              # CLI entry point
├── requirements.txt     # Python dependencies
├── config.json          # Configuration file (auto-generated)
└── README.md            # This file
```

## 🛠 Installation

### Prerequisites

- Python 3.10 or higher
- Google Cloud Platform account
- Gmail API enabled

### Setup

1. **Clone or download the project**:
   ```bash
   # If you have the files locally, navigate to the directory
   cd /path/to/fikiri_gmail_assistant
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up Google OAuth2 credentials**:
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Create a new project or select existing one
   - Enable the Gmail API
   - Create OAuth2 credentials (Desktop application)
   - Download the credentials JSON file
   - Place it in the `auth/` directory as `credentials.json`

4. **Create auth directory**:
   ```bash
   mkdir -p auth
   # Place your credentials.json file in the auth/ directory
   ```

## 🔐 Authentication

### First-time Setup

1. **Authenticate with Gmail**:
   ```bash
   python main.py auth
   ```

2. **Follow the prompts**:
   - The script will open a browser window
   - Sign in to your Google account
   - Grant permissions to Fikiri Solutions
   - Copy the authorization code
   - Paste it in the terminal

3. **Verify authentication**:
   ```bash
   python main.py status
   ```

## 📧 Usage

### Command Line Interface

#### List Emails
```bash
# List unread emails
python main.py list --query "is:unread" --max 10

# List emails from specific sender
python main.py list --query "from:example@gmail.com"

# List emails with specific subject
python main.py list --query "subject:urgent"
```

#### Process Emails
```bash
# Process unread emails (dry run)
python main.py process --query "is:unread" --dry-run

# Process emails with auto-reply
python main.py process --query "is:unread" --auto-reply

# Process specific message
python main.py process --msg-id "MESSAGE_ID_HERE"
```

#### Email Management
```python
from core.auth import authenticate_gmail
from core.actions import EmailActions

# Authenticate
service = authenticate_gmail('auth/credentials.json', 'auth/token.pkl')
actions = EmailActions(service)

# Mark as read
actions.mark_as_read('MESSAGE_ID')

# Archive message
actions.archive_message('MESSAGE_ID')

# Star message
actions.star_message('MESSAGE_ID')

# Add custom labels
actions.add_labels('MESSAGE_ID', ['LABEL_ID_1', 'LABEL_ID_2'])
```

### Programmatic Usage

```python
from core.auth import GmailAuthenticator
from core.gmail_utils import GmailService
from core.email_parser import EmailParser
from core.actions import EmailActions

# Initialize services
authenticator = GmailAuthenticator('auth/credentials.json', 'auth/token.pkl')
service = authenticator.authenticate()

gmail_service = GmailService(service)
email_parser = EmailParser()
email_actions = EmailActions(service)

# List and process emails
messages = gmail_service.list_messages("is:unread", max_results=5)

for message in messages:
    msg_id = message['id']
    
    # Get full message
    full_message = gmail_service.get_message(msg_id)
    
    # Parse email
    parsed_data = email_parser.parse_message(full_message)
    
    # Process based on content
    sender = parsed_data['headers']['from']
    subject = parsed_data['headers']['subject']
    body = parsed_data['body']['text']
    
    print(f"From: {sender}")
    print(f"Subject: {subject}")
    print(f"Body: {body[:100]}...")
    
    # Mark as read
    email_actions.mark_as_read(msg_id)
```

## ⚙️ Configuration

### Environment Variables

Create a `.env` file or set environment variables:

```bash
# Gmail API settings
GMAIL_CREDENTIALS_PATH=auth/credentials.json
GMAIL_TOKEN_PATH=auth/token.pkl
GMAIL_MAX_RESULTS=10

# Email settings
AUTO_REPLY_ENABLED=true
REPLY_TEMPLATE="Hi {sender_name},\n\nThank you for your email regarding \"{subject}\".\n\nI have received your message and will get back to you as soon as possible.\n\nBest regards,\nYour Name"
EMAIL_SIGNATURE="\n\n---\nFikiri Solutions\nAutomated Response System"

# General settings
DEBUG=false
DRY_RUN=false
```

### Configuration File

The system automatically creates a `config.json` file with default settings:

```json
{
  "gmail": {
    "credentials_path": "auth/credentials.json",
    "token_path": "auth/token.pkl",
    "scopes": ["https://www.googleapis.com/auth/gmail.modify"],
    "user_id": "me",
    "max_results": 10,
    "batch_size": 100
  },
  "email": {
    "auto_reply_enabled": false,
    "reply_template": "",
    "signature": "",
    "max_attachments": 5,
    "supported_mime_types": [
      "text/plain",
      "text/html",
      "multipart/alternative",
      "multipart/mixed",
      "multipart/related"
    ]
  },
  "logging": {
    "level": "INFO",
    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    "file_path": null,
    "max_file_size": 10485760,
    "backup_count": 5
  },
  "debug": false,
  "dry_run": false
}
```

## 🔍 Gmail Search Queries

Use Gmail's powerful search syntax:

```bash
# Basic queries
is:unread                    # Unread emails
is:read                      # Read emails
is:starred                   # Starred emails
is:important                 # Important emails

# Sender queries
from:example@gmail.com       # From specific sender
from:example                 # From any email containing "example"

# Subject queries
subject:urgent               # Subject contains "urgent"
subject:"meeting tomorrow"   # Exact phrase

# Date queries
newer_than:1d                # Last 24 hours
older_than:1w                # Older than 1 week
after:2024/01/01             # After specific date

# Combined queries
is:unread from:client        # Unread emails from clients
subject:invoice is:unread    # Unread invoices
```

## 🧪 Testing

### Dry Run Mode

Test your configuration without sending actual emails:

```bash
python main.py process --query "is:unread" --dry-run
```

### CRM Testing

Test CRM functionality:

```bash
# Test CRM ingestion
python3 main.py crm ingest --json '[{"name":"Test Lead","email":"test@example.com"}]'

# Test follow-up generation (dry-run)
python3 main.py crm followup --stage new

# Test webhook endpoints
uvicorn core.crm_sources:app --port 8000
# POST to http://localhost:8000/webhook/tally
```

### Manual Testing

```python
# Test email parsing
from core.email_parser import EmailParser

parser = EmailParser()
# Use with mock data or real message IDs

# Test CRM service
from core.crm_service import CRMService
crm = CRMService()
leads = crm.list()
```

## 📊 CRM Features

### Intelligent CRM Automations

The platform includes a comprehensive CRM system for lead management:

#### Lead Ingestion
- **CSV Import**: `
python3 main.py crm ingest --from-csv data/leads.csv`
- **JSON Import**: `python3 main.py crm ingest --json '[{"name":"Lead","email":"lead@example.com"}]'`
- **Webhook Endpoints**: `/webhook/tally`, `/webhook/typeform`, `/webhook/calendly`

#### Storage Options
- **Local JSON**: Default storage in `data/leads.json`
- **Google Sheets**: Set `ENABLE_GOOGLE_SHEETS=1` and `GOOGLE_SHEET_ID`
- **Notion**: Set `ENABLE_NOTION=1`, `NOTION_API_KEY`, and `NOTION_DB_ID`

#### Lead Management
- **Deduplication**: Automatic deduplication by email address
- **Scoring**: Keyword-based lead scoring (1-10 scale)
- **Stage Tracking**: `new`, `contacted`, `replied`, `won`, `lost`
- **Follow-ups**: AI-generated follow-up emails with Gmail integration

#### CRM Commands
```bash
# List all leads
python3 main.py crm list

# Generate follow-ups (dry-run)
python3 main.py crm followup --stage new

# Send follow-ups
python3 main.py crm followup --stage contacted --send

# Update lead stage
python3 main.py crm stage --id <lead_id> --to replied

# Daily follow-up trigger
curl -X POST http://localhost:8000/trigger/followups
```

## 🚀 Future Enhancements

### Planned Features

- **AI Integration**: Enhanced OpenAI/Claude integration for intelligent lead classification
- **Outlook Support**: Microsoft Graph API integration
- **Web Dashboard**: Streamlit or Flask-based web interface
- **Advanced Analytics**: Email metrics and CRM reporting
- **Multi-account Support**: Handle multiple Gmail accounts
- **Advanced Scheduling**: APScheduler integration for automated workflows

### Integration Examples

```python
# Future AI integration
from core.ai_classifier import EmailClassifier

classifier = EmailClassifier()
email_type = classifier.classify_email(parsed_data)
# Returns: 'lead', 'support', 'spam', 'urgent', etc.

# Future webhook integration
from core.webhooks import WebhookManager

webhook = WebhookManager()
webhook.trigger_lead_notification(parsed_data)
```

## 🛡️ Security

- **OAuth2 Authentication**: Secure Google API authentication
- **Token Management**: Automatic token refresh
- **Environment Variables**: Sensitive data via environment variables
- **Dry Run Mode**: Test without making changes
- **Error Handling**: Comprehensive error handling and logging

## 📝 Logging

The system provides comprehensive logging:

```bash
# Enable debug logging
python main.py --debug process --query "is:unread"

# Log to file
# Set LOG_FILE_PATH environment variable
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

### Common Issues

1. **Authentication Errors**:
   - Ensure credentials.json is in the correct location
   - Check that Gmail API is enabled in Google Cloud Console
   - Verify OAuth2 credentials are for "Desktop application"

2. **Permission Errors**:
   - Make sure the auth/ directory is writable
   - Check file permissions on credentials.json

3. **Import Errors**:
   - Ensure all dependencies are installed: `pip install -r requirements.txt`
   - Check Python version (3.10+ required)

### Getting Help

- Check the logs for detailed error messages
- Use `--debug` flag for verbose output
- Enable dry run mode to test without making changes

## 🎯 Use Cases

### Small Business Automation

- **Lawn Care Services**: Auto-respond to service requests
- **Appliance Repair**: Handle emergency calls and scheduling
- **Consulting**: Manage client inquiries and follow-ups
- **Real Estate**: Process lead inquiries and property requests

### Email Management

- **Lead Qualification**: Automatically categorize incoming leads
- **Response Templates**: Consistent, professional responses
- **Follow-up Automation**: Track and manage email conversations
- **Archive Management**: Organize processed emails

---

**Fikiri Solutions** - Streamlining business workflows with intelligent automation.
