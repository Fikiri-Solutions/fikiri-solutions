# Fikiri Solutions Monitoring Configuration
# Add these metrics to your monitoring system (Prometheus/Grafana)

# Authentication Metrics
auth_login_success_total{endpoint="/api/auth/login",method="POST"} 0
auth_login_failed_total{endpoint="/api/auth/login",method="POST",error_type="invalid_credentials"} 0
auth_login_failed_total{endpoint="/api/auth/login",method="POST",error_type="rate_limit"} 0
auth_refresh_total{endpoint="/api/auth/refresh",method="POST"} 0
auth_refresh_failed_total{endpoint="/api/auth/refresh",method="POST",error_type="invalid_token"} 0
auth_refresh_failed_total{endpoint="/api/auth/refresh",method="POST",error_type="expired_token"} 0

# System Health Metrics
redis_connection_errors_total{service="cache"} 0
redis_connection_errors_total{service="sessions"} 0
redis_connection_errors_total{service="rate_limiter"} 0
database_query_duration_seconds{query_type="select",table="users"} 0
database_query_duration_seconds{query_type="insert",table="query_performance_log"} 0

# Performance Metrics
jwt_token_generation_duration_seconds 0
jwt_token_verification_duration_seconds 0
cookie_set_duration_seconds 0
cors_preflight_duration_seconds 0

# Error Tracking
authentication_errors_total{error_type="jwt_decode_error"} 0
authentication_errors_total{error_type="fernet_decrypt_error"} 0
authentication_errors_total{error_type="session_not_found"} 0

# Usage Metrics
active_sessions_total 0
concurrent_users_total 0
api_requests_per_minute{endpoint="/api/auth/login"} 0
api_requests_per_minute{endpoint="/api/auth/whoami"} 0

# Security Metrics
failed_login_attempts_total{ip_address="unknown"} 0
suspicious_activity_total{type="multiple_failed_logins"} 0
suspicious_activity_total{type="unusual_user_agent"} 0

# Business Metrics
user_registrations_total{source="email"} 0
user_registrations_total{source="oauth"} 0
onboarding_completion_rate 0
user_retention_rate{days="7"} 0
user_retention_rate{days="30"} 0
