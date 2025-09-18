# 🚀 Release Management Guide

## Version Tagging and Deployment

### Creating a Release

1. **Tag the Release**:
   ```bash
   git tag -a v1.0.0 -m "Release v1.0.0: Complete Onboarding Orchestration"
   git push origin v1.0.0
   ```

2. **Generate Release Notes**:
   ```bash
   # Create release notes with features, migrations, rollback steps
   cat > RELEASE_NOTES_v1.0.0.md << EOF
   # Release v1.0.0 - Complete Onboarding Orchestration
   
   ## Features
   - Complete 5-step onboarding flow with real-time progress
   - Backend orchestration for Gmail sync and data seeding
   - Starter automations (auto-reply, invoice labeling) - OFF by default
   - Multi-user CRM with proper database schema
   - Visual trust cues and privacy explanations
   - Real-time progress tracking with WebSocket polling
   - Comprehensive error handling and retry mechanisms
   
   ## Migrations
   - Added user_id column to leads table for multi-user support
   - Created onboarding_jobs table for progress tracking
   - Created metrics_daily table for dashboard data
   - Added proper indexes and foreign key constraints
   
   ## Rollback Steps
   - Revert to previous commit: git reset --hard HEAD~1
   - Drop new tables: DROP TABLE onboarding_jobs, metrics_daily
   - Remove user_id column from leads table
   - Clear frontend build cache in Vercel
   
   ## Breaking Changes
   None
   
   ## Dependencies
   - flask-cors, aiohttp added to requirements.txt
   EOF
   ```

### Deployment Process

1. **Pre-Deploy Checklist**:
   - [ ] All tests passing
   - [ ] Database backup created
   - [ ] Environment variables configured
   - [ ] Kill-switch tested
   - [ ] Rollback plan ready

2. **Deploy Backend**:
   ```bash
   # Deploy to production server
   git checkout v1.0.0
   pip install -r requirements.txt
   python scripts/migrations/001_add_user_id_to_leads.py up
   pm2 restart fikiri-backend
   ```

3. **Deploy Frontend**:
   ```bash
   # Deploy to Vercel
   vercel --prod
   
   # Clear build cache for CSS/JS changes
   vercel --prod --force
   ```

4. **Post-Deploy Validation**:
   ```bash
   # Run smoke tests
   ./scripts/health-check.sh
   
   # Check logs
   tail -f logs/fikiri_$(date +%Y%m%d).log
   ```

## Rollback Procedures

### Quick Rollback (< 5 minutes)

1. **Enable Kill-Switch**:
   ```bash
   curl -X POST https://your-domain.com/api/automation/kill-switch \
     -H "Content-Type: application/json" \
     -d '{"enabled":true}'
   ```

2. **Revert Code**:
   ```bash
   git checkout v0.9.0  # Previous stable version
   git push origin main --force
   ```

3. **Restart Services**:
   ```bash
   pm2 restart all
   vercel --prod --force
   ```

### Full Rollback (< 15 minutes)

1. **Database Rollback**:
   ```bash
   # Rollback migration
   python scripts/migrations/001_add_user_id_to_leads.py down
   
   # Or restore from backup
   cp data/fikiri_backup_$(date +%Y%m%d).db data/fikiri.db
   ```

2. **Environment Rollback**:
   ```bash
   # Restore environment
   cp .env.backup .env
   
   # Restart with old config
   pm2 restart all
   ```

3. **Frontend Rollback**:
   ```bash
   # Rollback Vercel deployment
   vercel rollback
   ```

## Cache Management

### Vercel Build Cache

```bash
# Clear build cache for CSS/JS changes
vercel --prod --force

# Or clear specific cache
vercel --prod --clear-cache
```

### API Response Caching

```bash
# Clear API cache
curl -X POST https://your-domain.com/api/cache/clear

# Check cache status
curl -X GET https://your-domain.com/api/cache/status
```

### Database Cache

```bash
# Clear database query cache
sqlite3 data/fikiri.db "PRAGMA cache_size = 0; PRAGMA cache_size = 2000;"
```

## Environment Management

### Production Environment

```bash
# Required environment variables
export OPENAI_API_KEY="sk-your-openai-key-here"
export SECRET_KEY="your-super-secret-key-here-minimum-32-chars"
export GMAIL_CLIENT_ID="your-gmail-client-id"
export GMAIL_CLIENT_SECRET="your-gmail-client-secret"
export OAUTH_ENCRYPTION_KEY="your-oauth-encryption-key"

# Optional but recommended
export OUTLOOK_CLIENT_ID="your-outlook-client-id"
export OUTLOOK_CLIENT_SECRET="your-outlook-client-secret"
export STRIPE_SECRET_KEY="sk_live_your-stripe-key"
export STRIPE_PUBLISHABLE_KEY="pk_live_your-stripe-key"
export LOG_LEVEL="INFO"
export SENTRY_DSN="https://your-sentry-dsn@sentry.io/project"
```

### Staging Environment

```bash
# Use test/staging values
export OPENAI_API_KEY="sk-test-your-openai-key"
export SECRET_KEY="staging-secret-key-32-chars-minimum"
export GMAIL_CLIENT_ID="staging-gmail-client-id"
export GMAIL_CLIENT_SECRET="staging-gmail-client-secret"
export LOG_LEVEL="DEBUG"
```

## Monitoring and Alerts

### Health Check Endpoints

```bash
# Basic health check
curl https://your-domain.com/api/health

# Detailed system status
curl https://your-domain.com/api/system/status

# Rate limit status
curl https://your-domain.com/api/rate-limits/status?user_id=1

# OAuth token status
curl https://your-domain.com/api/oauth/token-status?user_id=1&service=gmail
```

### Alert Configuration

```bash
# Set up monitoring alerts
# Uptime: < 99.9% for 5 minutes
# Error Rate: > 1% 5xx responses for 5 minutes
# Automation Failures: > 5 failures in 10 minutes
# OAuth Refresh Failures: > 3 per user within 15 minutes
# Response Time: p95 > 300ms for 5 minutes
```

## Database Management

### Backup Strategy

```bash
# Daily automated backup
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
cp data/fikiri.db "backups/fikiri_backup_$DATE.db"
echo "Backup created: fikiri_backup_$DATE.db"
```

### Migration Management

```bash
# Run migration
python scripts/migrations/001_add_user_id_to_leads.py up

# Dry run migration
python scripts/migrations/001_add_user_id_to_leads.py dry-run

# Rollback migration
python scripts/migrations/001_add_user_id_to_leads.py down
```

### Database Maintenance

```bash
# Optimize database
sqlite3 data/fikiri.db "VACUUM;"

# Check database integrity
sqlite3 data/fikiri.db "PRAGMA integrity_check;"

# Analyze query performance
sqlite3 data/fikiri.db "ANALYZE;"
```

## Security Considerations

### Pre-Deploy Security Check

```bash
# Check for secrets in code
grep -r "sk-" . --exclude-dir=node_modules --exclude-dir=.venv
grep -r "password.*=" . --exclude-dir=node_modules --exclude-dir=.venv

# Check file permissions
find . -type f -name "*.py" -exec chmod 644 {} \;
find . -type f -name "*.sh" -exec chmod 755 {} \;
```

### Post-Deploy Security Check

```bash
# Test security headers
curl -I https://your-domain.com/ | grep -E "(HSTS|CSP|X-Content-Type-Options)"

# Test rate limiting
for i in {1..100}; do curl -s https://your-domain.com/api/health; done

# Test authentication
curl -X POST https://your-domain.com/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"wrongpassword"}'
```

## Performance Optimization

### Frontend Performance

```bash
# Check bundle size
npm run build
ls -la dist/assets/

# Check Core Web Vitals
# Use Lighthouse or PageSpeed Insights
```

### Backend Performance

```bash
# Check response times
curl -w "@curl-format.txt" -o /dev/null -s https://your-domain.com/api/leads?user_id=1

# Monitor database performance
sqlite3 data/fikiri.db "EXPLAIN QUERY PLAN SELECT * FROM leads WHERE user_id = 1;"
```

## Troubleshooting

### Common Issues

1. **Database Connection Issues**:
   ```bash
   # Check database file permissions
   ls -la data/fikiri.db
   
   # Check database integrity
   sqlite3 data/fikiri.db "PRAGMA integrity_check;"
   ```

2. **OAuth Token Issues**:
   ```bash
   # Check token status
   curl https://your-domain.com/api/oauth/token-status?user_id=1&service=gmail
   
   # Refresh token
   curl -X POST https://your-domain.com/api/oauth/refresh-token \
     -H "Content-Type: application/json" \
     -d '{"user_id":1,"service":"gmail"}'
   ```

3. **Rate Limiting Issues**:
   ```bash
   # Check rate limit status
   curl https://your-domain.com/api/rate-limits/status?user_id=1
   
   # Reset rate limits (admin only)
   curl -X POST https://your-domain.com/api/rate-limits/reset \
     -H "Content-Type: application/json" \
     -d '{"user_id":1}'
   ```

### Emergency Procedures

1. **System Down**:
   - Enable kill-switch
   - Check logs for errors
   - Restart services
   - Check database connectivity

2. **Data Corruption**:
   - Stop all services
   - Restore from backup
   - Verify data integrity
   - Restart services

3. **Security Incident**:
   - Enable kill-switch
   - Revoke all OAuth tokens
   - Check logs for suspicious activity
   - Notify security team

---

**Remember**: Always test rollback procedures in staging before deploying to production!
