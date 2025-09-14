# Fikiri Solutions - Gmail Lead Responder & AI Automation Suite

A lightweight, AI-powered business automation platform focused on Gmail integration, email processing, and intelligent lead management. Built with simplicity and extensibility in mind.

## 🚀 Features

- **Gmail API Integration**: Secure OAuth2 authentication and full Gmail API access
- **Email Processing**: Comprehensive email parsing with MIME support
- **Automated Responses**: Template-based automatic reply system
- **Email Management**: Mark as read/unread, archive, delete, star, and label operations
- **CLI Interface**: Easy-to-use command-line interface with comprehensive commands
- **Configuration Management**: Flexible configuration with environment variable support
- **Docker Support**: Containerized deployment with Docker Compose
- **Monitoring**: Prometheus and Grafana integration for system monitoring
- **Type Safety**: Full type hints throughout the codebase
- **Modular Design**: Clean, extensible architecture for future integrations

## 📁 Project Structure

```
fikiri-solutions/
├── core/                    # Core business logic (simplified)
├── auth/                    # Authentication files
│   ├── credentials.json.template
│   └── token.pkl
├── data/                    # Data storage
│   ├── business_profile.json
│   ├── faq_knowledge.json
│   ├── leads.csv
│   └── leads.json
├── templates/               # Email response templates
│   ├── general_response.txt
│   ├── lead_response.txt
│   ├── support_response.txt
│   └── urgent_response.txt
├── monitoring/              # Monitoring configuration
│   ├── prometheus.yml
│   └── grafana/
├── tests/                   # Test files
├── main.py                  # CLI entry point
├── requirements.txt         # Python dependencies
├── Dockerfile              # Docker configuration
├── docker-compose.yml      # Docker Compose setup
└── README.md               # This file
```

## 🛠 Installation

### Prerequisites

- Python 3.10 or higher
- Google Cloud Platform account
- Gmail API enabled

### Quick Start

1. **Clone the repository**:
   ```bash
   git clone https://github.com/Fikiri-Solutions/fikiri-solutions.git
   cd fikiri-solutions
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

4. **Authenticate with Gmail**:
   ```bash
   python main.py auth
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

The CLI supports multiple commands for different operations:

#### Authentication
```bash
# Authenticate with Gmail
python main.py auth

# Check authentication status
python main.py status
```

#### Email Operations
```bash
# List unread emails
python main.py list --query "is:unread" --max 10

# Fetch emails with details
python main.py fetch --query "is:unread" --detailed

# Process emails (dry run)
python main.py process --query "is:unread" --dry-run

# Process emails with auto-reply
python main.py process --query "is:unread" --auto-reply
```

#### Email Management
```bash
# Send test reply
python main.py reply --msg-id "MESSAGE_ID" --text "Test reply"

# Email actions
python main.py actions --msg-id "MESSAGE_ID" --action read
python main.py actions --msg-id "MESSAGE_ID" --action archive
python main.py actions --msg-id "MESSAGE_ID" --action star
```

#### CRM Operations
```bash
# Ingest leads from JSON
python main.py crm ingest --json '[{"name":"Test Lead","email":"test@example.com"}]'

# Ingest leads from CSV
python main.py crm ingest --from-csv data/leads.csv

# List all leads
python main.py crm list

# Generate follow-ups (preview)
python main.py crm followup --stage new

# Send follow-ups
python main.py crm followup --stage contacted --send

# Update lead stage
python main.py crm stage --id <lead_id> --to replied
```

#### Workflow Automation
```bash
# Schedule email processing
python main.py workflow schedule-email --query "is:unread" --interval 30 --auto-reply

# Schedule CRM follow-ups
python main.py workflow schedule-crm --interval-hours 24 --send

# List active workflows
python main.py workflow list

# Stop workflows
python main.py workflow stop --all
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
REPLY_TEMPLATE="Hi {sender_name},\n\nThank you for your email regarding \"{subject}\".\n\nI have received your message and will get back to you as soon as possible.\n\nBest regards,\nFikiri Solutions Team"
EMAIL_SIGNATURE="\n\n---\nFikiri Solutions\nAutomated Response System"

# General settings
DEBUG=false
DRY_RUN=false
```

### Dry Run Mode

Test your configuration without sending actual emails:

```bash
# Set environment variable
export DRY_RUN=true

# Or use command flag
python main.py process --query "is:unread" --dry-run
```

## 🐳 Docker Deployment

### Using Docker Compose

1. **Start the services**:
   ```bash
   docker-compose up -d
   ```

2. **View logs**:
   ```bash
   docker-compose logs -f
   ```

3. **Stop services**:
   ```bash
   docker-compose down
   ```

### Manual Docker Build

```bash
# Build the image
docker build -t fikiri-solutions .

# Run the container
docker run -it --rm fikiri-solutions python main.py --help
```

## 📊 Monitoring

The project includes monitoring setup with Prometheus and Grafana:

### Start Monitoring Stack

```bash
# Start monitoring services
docker-compose -f monitoring/docker-compose.yml up -d

# Access Grafana dashboard
open http://localhost:3000
# Default credentials: admin/admin
```

### Available Dashboards

- **System Metrics**: CPU, memory, disk usage
- **Email Processing**: Email counts, processing times
- **CRM Metrics**: Lead counts, conversion rates
- **Error Tracking**: Error rates and types

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

### Test in Google Colab

1. **Open Google Colab**: https://colab.research.google.com/
2. **Clone the repository**:
   ```python
   !git clone https://github.com/Fikiri-Solutions/fikiri-solutions.git
   !cd fikiri-solutions && pip install -r requirements.txt
   ```
3. **Test the CLI**:
   ```python
   !python main.py --help
   ```

### Local Testing

```bash
# Test authentication
python main.py auth

# Test email listing
python main.py list --query "is:unread" --max 5

# Test CRM functionality
python main.py crm list
```

## 🚀 Future Enhancements

### Planned Features

- **AI Integration**: Enhanced OpenAI/Claude integration for intelligent lead classification
- **Outlook Support**: Microsoft Graph API integration
- **Web Dashboard**: Streamlit or Flask-based web interface
- **Advanced Analytics**: Email metrics and CRM reporting
- **Multi-account Support**: Handle multiple Gmail accounts
- **Advanced Scheduling**: APScheduler integration for automated workflows

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

## 🔗 Links

- **GitHub Repository**: https://github.com/Fikiri-Solutions/fikiri-solutions
- **Documentation**: See `API_DOCUMENTATION.md` for detailed API reference
- **Authentication Setup**: See `AUTHENTICATION_SETUP.md` for detailed setup instructions
- **Performance Optimization**: See `PERFORMANCE_OPTIMIZATION.md` for optimization tips