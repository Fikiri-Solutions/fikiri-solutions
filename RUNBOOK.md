# 🚦 Pre-Launch Runbook

## First-Hour Post-Deploy Checklist

### 1. Smoke Tests (Manual or Script)

#### Frontend Health Checks
```bash
# Test all critical pages return 200
curl -I https://your-domain.com/
curl -I https://your-domain.com/ai
curl -I https://your-domain.com/crm
curl -I https://your-domain.com/services
curl -I https://your-domain.com/login
curl -I https://your-domain.com/onboarding
```

#### Backend Health Checks
```bash
# Test API endpoints
curl -X GET https://your-domain.com/api/health
curl -X POST https://your-domain.com/api/auth/signup \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"testpass123"}'
```

#### User Flow Test
1. **Sign up** → **Login** → **Connect Gmail** (test account)
2. **Onboarding job** moves through: Sync → Extract → Automations → Seed
3. **CRM shows imported leads**
4. **AI answers** "Who emailed me last?"

### 2. Automation Safety Test

```bash
# Enable test auto-reply for test inbox
curl -X POST https://your-domain.com/api/automations \
  -H "Content-Type: application/json" \
  -d '{"user_id":1,"name":"Test Auto-Reply","action_type":"auto_reply","status":"active"}'

# Send 1 email → verify exactly one reply, correct label applied, no loop
```

### 3. Metrics Sanity Check

```bash
# Check dashboard tiles populate
curl -X GET https://your-domain.com/api/dashboard/metrics?user_id=1

# Verify metrics_daily has increments
sqlite3 data/fikiri.db "SELECT * FROM metrics_daily WHERE user_id = 1 ORDER BY day DESC LIMIT 5;"
```

### 4. Logs & Errors Check

```bash
# Check last 15 minutes for errors
tail -n 100 logs/fikiri_$(date +%Y%m%d).log | grep -E "(ERROR|CRITICAL|Exception)"

# Check for token refresh errors
grep "OAuth refresh failed" logs/fikiri_$(date +%Y%m%d).log | tail -10
```

### 5. Emergency Procedures

#### If Any Step Fails:

1. **Toggle Global Kill-Switch** (pauses outbound actions):
   ```bash
   curl -X POST https://your-domain.com/api/automation/kill-switch \
     -H "Content-Type: application/json" \
     -d '{"enabled":true}'
   ```

2. **Revert to Previous Release**:
   ```bash
   git tag -l | tail -2  # List last 2 tags
   git checkout v0.9.0  # Revert to previous version
   git push origin main --force
   ```

3. **Investigate with Logs**:
   ```bash
   # Check specific error patterns
   grep -A 5 -B 5 "ERROR" logs/fikiri_$(date +%Y%m%d).log
   
   # Check database integrity
   sqlite3 data/fikiri.db ".schema" | grep -E "(leads|onboarding_jobs|metrics_daily)"
   ```

## Rollback Steps

### Database Rollback
```bash
# If migration issues, rollback database
python scripts/migrations/001_add_user_id_to_leads.py down

# Restore from backup
cp data/fikiri_backup_$(date +%Y%m%d).db data/fikiri.db
```

### Frontend Rollback
```bash
# Clear Vercel build cache
vercel --prod --force

# Or revert to previous deployment
vercel rollback
```

### Environment Rollback
```bash
# Restore environment variables
cp .env.backup .env

# Restart services
pm2 restart all  # or your process manager
```

## Monitoring Commands

### Health Check Script
```bash
#!/bin/bash
# health-check.sh

echo "🔍 Running health checks..."

# Frontend
echo "Testing frontend..."
curl -s -o /dev/null -w "%{http_code}" https://your-domain.com/ | grep -q "200" && echo "✅ Frontend OK" || echo "❌ Frontend FAILED"

# Backend
echo "Testing backend..."
curl -s -o /dev/null -w "%{http_code}" https://your-domain.com/api/health | grep -q "200" && echo "✅ Backend OK" || echo "❌ Backend FAILED"

# Database
echo "Testing database..."
sqlite3 data/fikiri.db "SELECT 1;" > /dev/null 2>&1 && echo "✅ Database OK" || echo "❌ Database FAILED"

# OAuth
echo "Testing OAuth..."
curl -s https://your-domain.com/api/oauth/token-status?user_id=1 | grep -q "success" && echo "✅ OAuth OK" || echo "❌ OAuth FAILED"

echo "🎉 Health check complete!"
```

### Performance Monitoring
```bash
# Check response times
curl -w "@curl-format.txt" -o /dev/null -s https://your-domain.com/api/leads?user_id=1

# Check rate limits
curl -X GET https://your-domain.com/api/rate-limits/status?user_id=1
```

## Alert Thresholds

- **Uptime**: < 99.9% for 5 minutes
- **Error Rate**: > 1% 5xx responses for 5 minutes  
- **Automation Failures**: > 5 failures in 10 minutes
- **OAuth Refresh Failures**: > 3 per user within 15 minutes
- **Response Time**: p95 > 300ms for 5 minutes

## Emergency Contacts

- **Primary**: DevOps Team
- **Secondary**: Development Team
- **Escalation**: CTO

## Post-Deploy Validation

### 24-Hour Checklist
- [ ] All smoke tests passing
- [ ] No critical errors in logs
- [ ] User registrations working
- [ ] Gmail OAuth flow working
- [ ] Onboarding completing successfully
- [ ] CRM data populating
- [ ] AI Assistant responding
- [ ] Rate limits functioning
- [ ] Automation safety controls active

### 7-Day Checklist
- [ ] Performance metrics stable
- [ ] User feedback positive
- [ ] No security incidents
- [ ] Database growth normal
- [ ] OAuth tokens refreshing properly
- [ ] Automation rules executing safely
- [ ] Error rates within acceptable limits

---

**Remember**: When in doubt, enable the kill-switch and investigate. It's better to pause automations than to have runaway actions.
