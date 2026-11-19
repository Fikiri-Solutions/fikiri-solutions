-- Rollback 011_site_marketing_events (destructive).
DROP INDEX IF EXISTS idx_site_marketing_events_occurred;
DROP INDEX IF EXISTS idx_site_marketing_events_name_occurred;
DROP INDEX IF EXISTS idx_site_marketing_events_dedupe;
DROP TABLE IF EXISTS site_marketing_events;
