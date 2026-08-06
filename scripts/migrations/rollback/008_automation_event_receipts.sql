-- Rollback for 008_automation_event_receipts.sql
-- Safe only when no production dependency on this table remains.

DROP TABLE IF EXISTS automation_event_receipts;
