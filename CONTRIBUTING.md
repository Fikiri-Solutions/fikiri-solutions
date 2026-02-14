# 🚀 Fikiri Solutions - Developer Onboarding Guide

Welcome to Fikiri Solutions! This guide will get you up and running locally in under 30 minutes.

## 📋 Prerequisites

Before you begin, ensure you have the following installed:

- **Node.js** 18+ ([Download](https://nodejs.org/))
- **Python** 3.11+ ([Download](https://python.org/))
- **Git** ([Download](https://git-scm.com/))
- **Redis** ([Download](https://redis.io/download))
- **VS Code** (recommended) ([Download](https://code.visualstudio.com/))

## 🏗️ Project Structure

```
Fikiri/
├── frontend/                 # React + Vite + TypeScript
│   ├── src/
│   │   ├── components/      # UI components (radiant, layout, etc.)
│   │   ├── pages/           # Page components
│   │   ├── hooks/           # Custom hooks
│   │   ├── contexts/        # Auth, theme
│   │   └── services/        # API client (single backend entry)
│   └── dist/                # Build output
├── routes/                   # API routes (auth, business, user)
├── core/                     # Shared backend (ai, jwt, redis, webhooks)
├── crm/                      # CRM service (crm/service.py canonical)
├── email_automation/         # Email pipeline, jobs
├── integrations/            # Gmail, Outlook, iCloud connectors
├── analytics/                # Dashboard API
├── tests/                    # Backend tests (pytest)
├── scripts/                  # Automation readiness, DB tools
└── docs/                     # Documentation
```

## ⚡ Quick Start

### 1. Clone the Repository

```bash
git clone https://github.com/Fikiri-Solutions/fikiri-solutions.git
cd fikiri-solutions
```

### 2. Environment Setup

```bash
# Copy environment template
cp env.template .env

# Edit .env with your local settings (see env.template section comments)
```

### 3. Backend Setup

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On macOS/Linux:
source venv/bin/activate
# On Windows:
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Start Redis (in a separate terminal) if using Redis for cache/queues
redis-server

# Start backend server (database initializes on first run)
python app.py
```

### 4. Frontend Setup

```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

### 5. Verify Installation

- **Frontend**: http://localhost:5173 (Vite default)
- **Backend**: http://localhost:8081
- **API**: http://localhost:8081/api

## 🛠️ Development Workflow

### Branch Strategy

- `main` - Production-ready code
- `develop` - Integration branch for features
- `feature/*` - Feature branches
- `hotfix/*` - Critical bug fixes

### Making Changes

1. **Create a feature branch**:
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes**:
   - Follow the coding standards (see below)
   - Write tests for new functionality
   - Update documentation if needed

3. **Test your changes**:
   ```bash
   # Backend tests
   pytest tests/ -v
   
   # Frontend tests
   cd frontend
   npm run test
   ```

4. **Commit your changes**:
   ```bash
   git add .
   git commit -m "feat: add your feature description"
   ```

5. **Push and create PR**:
   ```bash
   git push origin feature/your-feature-name
   ```

## 📝 Coding Standards

### Python (Backend)

- **Style**: Follow PEP 8
- **Formatting**: Use Black for code formatting
- **Imports**: Use isort for import sorting
- **Type Hints**: Use type hints for all functions
- **Docstrings**: Use Google-style docstrings

```python
def process_email(email_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process email data and extract relevant information.
    
    Args:
        email_data: Raw email data dictionary
        
    Returns:
        Processed email data dictionary
        
    Raises:
        ValidationError: If email data is invalid
    """
    # Implementation here
    pass
```

### TypeScript/React (Frontend)

- **Style**: Follow ESLint configuration
- **Formatting**: Use Prettier
- **Components**: Use functional components with hooks
- **Props**: Define interfaces for all props
- **Error Handling**: Use error boundaries

```typescript
interface EmailCardProps {
  email: Email;
  onSelect: (email: Email) => void;
  isSelected: boolean;
}

export const EmailCard: React.FC<EmailCardProps> = ({
  email,
  onSelect,
  isSelected
}) => {
  // Implementation here
};
```

## 🧪 Testing

### Backend Testing

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=core --cov-report=html

# Run specific test file
pytest tests/test_email_service.py -v

# Run integration tests
pytest tests/integration/ -v
```

### Frontend Testing

```bash
cd frontend

# Run unit tests
npm run test

# Run E2E tests
npm run test:e2e

# Run tests in watch mode
npm run test:watch

# Run tests with coverage
npm run test:coverage
```

## 🔧 Development Tools

### VS Code Extensions (Recommended)

- **Python**: Python extension pack
- **TypeScript**: TypeScript Importer
- **React**: ES7+ React/Redux/React-Native snippets
- **Git**: GitLens
- **Testing**: Jest Runner
- **Formatting**: Prettier, Black Formatter

### VS Code Settings

Create `.vscode/settings.json`:

```json
{
  "python.defaultInterpreterPath": "./venv/bin/python",
  "python.formatting.provider": "black",
  "python.linting.enabled": true,
  "python.linting.pylintEnabled": true,
  "editor.formatOnSave": true,
  "editor.codeActionsOnSave": {
    "source.organizeImports": true
  },
  "typescript.preferences.importModuleSpecifier": "relative",
  "emmet.includeLanguages": {
    "typescript": "html"
  }
}
```

## 🐛 Debugging

### Backend Debugging

```bash
# Run with debugger
python -m pdb app.py

# Use VS Code debugger
# Set breakpoints and use F5 to start debugging
```

### Frontend Debugging

```bash
# Start with debug mode
npm run dev:debug

# Use React DevTools browser extension
# Use VS Code debugger for TypeScript
```

## 📊 Monitoring and Logging

### Local Logging

- **Backend logs**: `logs/fikiri.log`
- **Frontend logs**: Browser console
- **Redis logs**: Check Redis server output

### Production Monitoring

- **Sentry**: Error tracking and performance monitoring
- **Logs**: Structured JSON logging
- **Metrics**: Application performance metrics

## 🔐 Security

### Local Development

- Never commit `.env` files
- Use test API keys for development
- Keep dependencies updated

### Security Checklist

- [ ] Environment variables secured
- [ ] API keys rotated regularly
- [ ] Dependencies scanned for vulnerabilities
- [ ] Input validation implemented
- [ ] Rate limiting configured

## 🚀 Deployment

### Staging Deployment

```bash
# Deploy to staging
git push origin develop

# This triggers automatic deployment to staging environment
```

### Production Deployment

```bash
# Deploy to production
git push origin main

# This triggers automatic deployment to production
```

## 📚 Additional Resources

### Documentation

- [API Documentation](http://localhost:8081/api/docs)
- [Component Library](http://localhost:3000/storybook)
- [Architecture Overview](./docs/SYSTEM_ARCHITECTURE.md)

### External Services

- **Stripe**: Payment processing
- **Gmail API**: Email integration
- **OpenAI**: AI services
- **Redis**: Caching and sessions

### Troubleshooting

#### Common Issues

1. **Port already in use**:
   ```bash
   # Kill process on port 3000
   lsof -ti:3000 | xargs kill -9
   
   # Kill process on port 8081
   lsof -ti:8081 | xargs kill -9
   ```

2. **Redis connection failed**:
   ```bash
   # Start Redis server
   redis-server
   
   # Check Redis status
   redis-cli ping
   ```

3. **Python dependencies issues**:
   ```bash
   # Recreate virtual environment
   rm -rf venv
   python -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

4. **Node modules issues**:
   ```bash
   # Clear npm cache and reinstall
   npm cache clean --force
   rm -rf node_modules package-lock.json
   npm install
   ```

### Getting Help

- **Slack**: #dev-support channel
- **Email**: dev-support@fikirisolutions.com
- **Issues**: GitHub Issues
- **Wiki**: Internal documentation wiki

## 🎯 Next Steps

After completing this setup:

1. **Explore the codebase**: Start with the main components
2. **Run the test suite**: Ensure everything works
3. **Make a small change**: Try adding a new feature
4. **Join the team**: Introduce yourself in Slack
5. **Read the architecture docs**: Understand the system design

## 📞 Support

If you run into any issues:

1. Check this guide first
2. Search existing GitHub issues
3. Ask in the #dev-support Slack channel
4. Create a new issue if needed

Welcome to the team! 🎉
