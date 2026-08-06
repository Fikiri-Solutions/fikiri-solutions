-- Additive: immediate access-token invalidation via session version.
-- Prefer runtime: core.auth_session_version.ensure_auth_session_version_column()
-- (handles SQLite + PostgreSQL; ignores duplicate-column).
--
-- PostgreSQL / SQLite ops reference (run once; ignore "already exists"):

ALTER TABLE users ADD COLUMN auth_session_version INTEGER NOT NULL DEFAULT 1;
