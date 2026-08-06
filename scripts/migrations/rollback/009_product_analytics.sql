-- Rollback for 009_product_analytics.sql
-- Safe only when no production dependency on these tables remains.

DROP TABLE IF EXISTS tenant_daily_metrics;
DROP TABLE IF EXISTS product_events;
