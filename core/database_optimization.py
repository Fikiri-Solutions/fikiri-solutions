"""
Database Optimization System
Query performance, indexing, and migrations for Fikiri Solutions
"""

import sqlite3
import json
import time
import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import threading
from contextlib import contextmanager

logger = logging.getLogger(__name__)

@dataclass
class QueryMetrics:
    """Database query performance metrics"""
    query: str
    execution_time: float
    rows_affected: int
    timestamp: datetime
    success: bool
    error: Optional[str] = None

@dataclass
class IndexInfo:
    """Database index information"""
    table_name: str
    index_name: str
    columns: List[str]
    unique: bool
    size_bytes: int

class DatabaseOptimizer:
    """Database optimization and performance monitoring"""
    
    def __init__(self, db_path: str = "data/fikiri.db"):
        self.db_path = db_path
        self.query_metrics: List[QueryMetrics] = []
        self.max_metrics = 10000
        self.lock = threading.Lock()
        self._initialize_database()
    
    def _initialize_database(self):
        """Initialize database with optimized schema"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Create optimized tables with proper indexes
            self._create_optimized_tables(cursor)
            self._create_indexes(cursor)
            self._create_views(cursor)
            
            conn.commit()
            logger.info("Database initialized with optimized schema")
    
    def _create_optimized_tables(self, cursor):
        """Create tables with optimized structure"""
        
        # Users table for authentication and profiles
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT NOT NULL UNIQUE,
                name TEXT NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT DEFAULT 'user',
                business_name TEXT,
                business_email TEXT,
                industry TEXT,
                team_size TEXT,
                is_active BOOLEAN DEFAULT 1,
                email_verified BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP,
                onboarding_completed BOOLEAN DEFAULT 0,
                onboarding_step INTEGER DEFAULT 0,
                metadata TEXT  -- JSON object for additional user data
            )
        """)
        
        # Gmail OAuth tokens table (supporting both encrypted and plain storage)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS gmail_tokens (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                access_token TEXT NOT NULL,
                refresh_token TEXT,
                access_token_enc TEXT,  -- Encrypted version
                refresh_token_enc TEXT, -- Encrypted version
                token_type TEXT DEFAULT 'Bearer',
                expires_at TIMESTAMP,
                expiry_timestamp INTEGER,  -- Unix timestamp version
                scope TEXT,  -- OAuth scopes granted (JSON string)
                scopes_json TEXT,  -- OAuth scopes granted (JSON string) for encrypted tokens
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT 1,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
            )
        """)
        
        # Email sync tracking table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS email_sync (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                sync_type TEXT NOT NULL,  -- 'initial', 'incremental', 'manual'
                status TEXT DEFAULT 'pending',  -- 'pending', 'running', 'completed', 'failed'
                emails_processed INTEGER DEFAULT 0,
                emails_total INTEGER DEFAULT 0,
                started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP,
                error_message TEXT,
                metadata TEXT,  -- JSON object for sync details
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
            )
        """)
        
        # Onboarding info table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS onboarding_info (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                name TEXT,
                company TEXT,
                industry TEXT,
                team_size TEXT,
                goals TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
            )
        """)
        
        # OAuth states table for CSRF protection
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS oauth_states (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                state TEXT UNIQUE NOT NULL,
                user_id INTEGER,
                provider TEXT DEFAULT 'gmail',
                redirect_url TEXT,
                expires_at INTEGER,
                metadata TEXT,  -- JSON object for additional state data
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
            )
        """)
        
        # User sessions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                session_id TEXT NOT NULL UNIQUE,
                ip_address TEXT,
                user_agent TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP NOT NULL,
                is_valid BOOLEAN DEFAULT 1,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
            )
        """)
        
        # Leads table with proper data types and constraints
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS leads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                email TEXT NOT NULL,
                name TEXT NOT NULL,
                phone TEXT,
                company TEXT,
                source TEXT DEFAULT 'web',
                stage TEXT DEFAULT 'new',
                score INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_contact TIMESTAMP,
                notes TEXT,
                tags TEXT,  -- JSON array of tags
                metadata TEXT,  -- JSON object for additional data
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
                UNIQUE(user_id, email)  -- Unique email per user
            )
        """)
        
        # Activities table for lead interactions
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS lead_activities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                lead_id INTEGER NOT NULL,
                activity_type TEXT NOT NULL,
                description TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                metadata TEXT,  -- JSON object
                FOREIGN KEY (lead_id) REFERENCES leads (id) ON DELETE CASCADE
            )
        """)
        
        # Email templates table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS email_templates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                subject TEXT NOT NULL,
                body TEXT NOT NULL,
                template_type TEXT DEFAULT 'general',
                industry TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT 1
            )
        """)
        
        # Performance metrics table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS performance_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                endpoint TEXT NOT NULL,
                method TEXT NOT NULL,
                response_time REAL NOT NULL,
                status_code INTEGER NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                user_agent TEXT,
                ip_address TEXT
            )
        """)
        
        # User privacy settings table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_privacy_settings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                data_retention_days INTEGER DEFAULT 90,
                email_scanning_enabled BOOLEAN DEFAULT 1,
                personal_email_exclusion BOOLEAN DEFAULT 1,
                auto_labeling_enabled BOOLEAN DEFAULT 1,
                lead_detection_enabled BOOLEAN DEFAULT 1,
                analytics_tracking_enabled BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
                UNIQUE(user_id)
            )
        """)
        
        # Data retention logs table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS data_retention_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                data_type TEXT NOT NULL,  -- 'emails', 'leads', 'activities'
                records_deleted INTEGER DEFAULT 0,
                retention_policy_days INTEGER NOT NULL,
                deleted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                metadata TEXT,  -- JSON object with deletion details
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
            )
        """)
        
        # Privacy consent tracking table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS privacy_consents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                consent_type TEXT NOT NULL,  -- 'gmail_access', 'data_processing', 'analytics'
                granted BOOLEAN NOT NULL,
                consent_text TEXT NOT NULL,
                ip_address TEXT,
                user_agent TEXT,
                granted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                revoked_at TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
            )
        """)
        
        # System configuration table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS system_config (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                description TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Automation rules table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS automation_rules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                description TEXT,
                trigger_type TEXT NOT NULL,
                trigger_conditions TEXT NOT NULL,  -- JSON object
                action_type TEXT NOT NULL,
                action_parameters TEXT NOT NULL,  -- JSON object
                status TEXT DEFAULT 'active',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_executed TIMESTAMP,
                execution_count INTEGER DEFAULT 0,
                success_count INTEGER DEFAULT 0,
                error_count INTEGER DEFAULT 0,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
            )
        """)
        
        # Automation executions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS automation_executions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                rule_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                trigger_data TEXT NOT NULL,  -- JSON object
                action_result TEXT NOT NULL,  -- JSON object
                status TEXT NOT NULL,  -- 'success', 'error'
                executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                error_message TEXT,
                FOREIGN KEY (rule_id) REFERENCES automation_rules (id) ON DELETE CASCADE,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
            )
        """)
        
        # Parsed emails table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS parsed_emails (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                email_id TEXT NOT NULL,
                thread_id TEXT,
                sender_email TEXT NOT NULL,
                sender_name TEXT,
                recipient_email TEXT,
                subject TEXT,
                body_text TEXT,
                body_html TEXT,
                email_date TIMESTAMP,
                labels TEXT,  -- JSON array
                attachments TEXT,  -- JSON array
                extracted_data TEXT,  -- JSON object
                lead_potential INTEGER DEFAULT 0,
                action_required BOOLEAN DEFAULT 0,
                parsed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
            )
        """)
        
        # Email insights table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS email_insights (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                email_id TEXT NOT NULL,
                insight_type TEXT NOT NULL,
                confidence REAL NOT NULL,
                data TEXT NOT NULL,  -- JSON object
                suggested_action TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
            )
        """)
        
        # Feature flags table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS feature_flags (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                feature_name TEXT NOT NULL UNIQUE,
                enabled BOOLEAN DEFAULT 0,
                description TEXT,
                rollout_percentage INTEGER DEFAULT 0,
                target_users TEXT,  -- JSON array of user IDs or conditions
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # User feature access table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_feature_access (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                feature_name TEXT NOT NULL,
                has_access BOOLEAN DEFAULT 0,
                granted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                granted_by TEXT,  -- 'system', 'admin', etc.
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
                UNIQUE(user_id, feature_name)
            )
        """)
        
        # Analytics events table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS analytics_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                event_type TEXT NOT NULL,
                event_data TEXT,  -- JSON object
                ip_address TEXT,
                user_agent TEXT,
                session_id TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE SET NULL
            )
        """)
        
        # Onboarding jobs table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS onboarding_jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                status TEXT DEFAULT 'pending',  -- 'pending', 'running', 'completed', 'failed'
                current_step TEXT DEFAULT 'initializing',
                progress INTEGER DEFAULT 0,  -- 0-100
                started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP,
                error_message TEXT,
                metadata TEXT,  -- JSON object with job details
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
            )
        """)
        
        # Metrics daily table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS metrics_daily (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                day DATE NOT NULL,  -- YYYY-MM-DD format
                emails_processed INTEGER DEFAULT 0,
                leads_created INTEGER DEFAULT 0,
                automations_run INTEGER DEFAULT 0,
                automation_errors INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
                UNIQUE(user_id, day)
            )
        """)
    
    def _create_indexes(self, cursor):
        """Create optimized indexes for better query performance"""
        
        indexes = [
            # Users table indexes
            ("idx_users_email", "users", ["email"]),
            ("idx_users_role", "users", ["role"]),
            ("idx_users_active", "users", ["is_active"]),
            ("idx_users_onboarding", "users", ["onboarding_completed"]),
            ("idx_users_created_at", "users", ["created_at"]),
            
            # Gmail tokens indexes
            ("idx_gmail_tokens_user_id", "gmail_tokens", ["user_id"]),
            ("idx_gmail_tokens_active", "gmail_tokens", ["is_active"]),
            ("idx_gmail_tokens_expires", "gmail_tokens", ["expires_at"]),
            
            # Email sync indexes
            ("idx_email_sync_user_id", "email_sync", ["user_id"]),
            ("idx_email_sync_status", "email_sync", ["status"]),
            ("idx_email_sync_type", "email_sync", ["sync_type"]),
            ("idx_email_sync_started", "email_sync", ["started_at"]),
            
            # User sessions indexes
            ("idx_sessions_user_id", "user_sessions", ["user_id"]),
            ("idx_sessions_session_id", "user_sessions", ["session_id"]),
            ("idx_sessions_expires", "user_sessions", ["expires_at"]),
            ("idx_sessions_valid", "user_sessions", ["is_valid"]),
            
            # Privacy settings indexes
            ("idx_privacy_user_id", "user_privacy_settings", ["user_id"]),
            ("idx_privacy_retention", "user_privacy_settings", ["data_retention_days"]),
            
            # Data retention logs indexes
            ("idx_retention_user_id", "data_retention_logs", ["user_id"]),
            ("idx_retention_data_type", "data_retention_logs", ["data_type"]),
            ("idx_retention_deleted_at", "data_retention_logs", ["deleted_at"]),
            
            # Privacy consents indexes
            ("idx_consents_user_id", "privacy_consents", ["user_id"]),
            ("idx_consents_type", "privacy_consents", ["consent_type"]),
            ("idx_consents_granted", "privacy_consents", ["granted"]),
            ("idx_consents_granted_at", "privacy_consents", ["granted_at"]),
            
            # Automation rules indexes
            ("idx_automation_user_id", "automation_rules", ["user_id"]),
            ("idx_automation_trigger_type", "automation_rules", ["trigger_type"]),
            ("idx_automation_status", "automation_rules", ["status"]),
            ("idx_automation_last_executed", "automation_rules", ["last_executed"]),
            
            # Automation executions indexes
            ("idx_executions_rule_id", "automation_executions", ["rule_id"]),
            ("idx_executions_user_id", "automation_executions", ["user_id"]),
            ("idx_executions_status", "automation_executions", ["status"]),
            ("idx_executions_executed_at", "automation_executions", ["executed_at"]),
            
            # Parsed emails indexes
            ("idx_parsed_emails_user_id", "parsed_emails", ["user_id"]),
            ("idx_parsed_emails_email_id", "parsed_emails", ["email_id"]),
            ("idx_parsed_emails_sender", "parsed_emails", ["sender_email"]),
            ("idx_parsed_emails_date", "parsed_emails", ["email_date"]),
            ("idx_parsed_emails_lead_potential", "parsed_emails", ["lead_potential"]),
            
            # Email insights indexes
            ("idx_insights_user_id", "email_insights", ["user_id"]),
            ("idx_insights_email_id", "email_insights", ["email_id"]),
            ("idx_insights_type", "email_insights", ["insight_type"]),
            ("idx_insights_created_at", "email_insights", ["created_at"]),
            
            # Feature flags indexes
            ("idx_feature_flags_name", "feature_flags", ["feature_name"]),
            ("idx_feature_flags_enabled", "feature_flags", ["enabled"]),
            
            # User feature access indexes
            ("idx_user_features_user_id", "user_feature_access", ["user_id"]),
            ("idx_user_features_feature", "user_feature_access", ["feature_name"]),
            ("idx_user_features_access", "user_feature_access", ["has_access"]),
            
            # Analytics events indexes
            ("idx_analytics_user_id", "analytics_events", ["user_id"]),
            ("idx_analytics_event_type", "analytics_events", ["event_type"]),
            ("idx_analytics_created_at", "analytics_events", ["created_at"]),
            ("idx_analytics_session", "analytics_events", ["session_id"]),
            
            # Onboarding jobs indexes
            ("idx_onboarding_user_id", "onboarding_jobs", ["user_id"]),
            ("idx_onboarding_status", "onboarding_jobs", ["status"]),
            ("idx_onboarding_started_at", "onboarding_jobs", ["started_at"]),
            
            # Metrics daily indexes
            ("idx_metrics_user_id", "metrics_daily", ["user_id"]),
            ("idx_metrics_day", "metrics_daily", ["day"]),
            ("idx_metrics_user_day", "metrics_daily", ["user_id", "day"]),
            
            # Leads table indexes
            ("idx_leads_user_id", "leads", ["user_id"]),
            ("idx_leads_email", "leads", ["email"]),
            ("idx_leads_stage", "leads", ["stage"]),
            ("idx_leads_source", "leads", ["source"]),
            ("idx_leads_created_at", "leads", ["created_at"]),
            ("idx_leads_score", "leads", ["score"]),
            ("idx_leads_company", "leads", ["company"]),
            
            # Composite indexes for common queries
            ("idx_leads_user_stage", "leads", ["user_id", "stage"]),
            ("idx_leads_user_source", "leads", ["user_id", "source"]),
            ("idx_leads_stage_source", "leads", ["stage", "source"]),
            ("idx_leads_created_stage", "leads", ["created_at", "stage"]),
            
            # Activities table indexes
            ("idx_activities_lead_id", "lead_activities", ["lead_id"]),
            ("idx_activities_type", "lead_activities", ["activity_type"]),
            ("idx_activities_timestamp", "lead_activities", ["timestamp"]),
            ("idx_activities_lead_timestamp", "lead_activities", ["lead_id", "timestamp"]),
            
            # Email templates indexes
            ("idx_templates_type", "email_templates", ["template_type"]),
            ("idx_templates_industry", "email_templates", ["industry"]),
            ("idx_templates_active", "email_templates", ["is_active"]),
            
            # Performance metrics indexes
            ("idx_perf_endpoint", "performance_metrics", ["endpoint"]),
            ("idx_perf_timestamp", "performance_metrics", ["timestamp"]),
            ("idx_perf_status", "performance_metrics", ["status_code"]),
            ("idx_perf_endpoint_timestamp", "performance_metrics", ["endpoint", "timestamp"]),
        ]
        
        for index_name, table_name, columns in indexes:
            try:
                cursor.execute(f"""
                    CREATE INDEX IF NOT EXISTS {index_name} 
                    ON {table_name} ({', '.join(columns)})
                """)
            except Exception as e:
                logger.warning(f"Failed to create index {index_name}: {e}")
    
    def _create_views(self, cursor):
        """Create optimized views for common queries"""
        
        # Lead summary view
        cursor.execute("""
            CREATE VIEW IF NOT EXISTS lead_summary AS
            SELECT 
                l.id,
                l.email,
                l.name,
                l.company,
                l.stage,
                l.source,
                l.score,
                l.created_at,
                l.last_contact,
                COUNT(a.id) as activity_count,
                MAX(a.timestamp) as last_activity
            FROM leads l
            LEFT JOIN lead_activities a ON l.id = a.lead_id
            GROUP BY l.id, l.email, l.name, l.company, l.stage, l.source, l.score, l.created_at, l.last_contact
        """)
        
        # Performance summary view
        cursor.execute("""
            CREATE VIEW IF NOT EXISTS performance_summary AS
            SELECT 
                endpoint,
                method,
                COUNT(*) as request_count,
                AVG(response_time) as avg_response_time,
                MIN(response_time) as min_response_time,
                MAX(response_time) as max_response_time,
                COUNT(CASE WHEN status_code >= 400 THEN 1 END) as error_count
            FROM performance_metrics
            WHERE timestamp >= datetime('now', '-24 hours')
            GROUP BY endpoint, method
        """)
    
    @contextmanager
    def get_connection(self):
        """Get database connection with proper error handling"""
        conn = None
        try:
            conn = sqlite3.connect(self.db_path, timeout=30.0)
            conn.row_factory = sqlite3.Row  # Enable dict-like access
            conn.execute("PRAGMA journal_mode=WAL")  # Enable WAL mode for better concurrency
            conn.execute("PRAGMA synchronous=NORMAL")  # Balance safety and performance
            conn.execute("PRAGMA cache_size=10000")  # Increase cache size
            conn.execute("PRAGMA temp_store=MEMORY")  # Store temp tables in memory
            yield conn
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Database connection error: {e}")
            raise
        finally:
            if conn:
                conn.close()
    
    def execute_query(self, query: str, params: Tuple = None, fetch: bool = True) -> Any:
        """Execute a query with performance monitoring"""
        start_time = time.time()
        
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                if params:
                    cursor.execute(query, params)
                else:
                    cursor.execute(query)
                
                if fetch:
                    if query.strip().upper().startswith(('SELECT', 'PRAGMA')):
                        result = cursor.fetchall()
                    else:
                        result = cursor.rowcount
                else:
                    result = cursor.rowcount
                
                conn.commit()
                
                execution_time = time.time() - start_time
                
                # Record metrics
                self._record_query_metrics(query, execution_time, result, True)
                
                return result
                
        except Exception as e:
            execution_time = time.time() - start_time
            self._record_query_metrics(query, execution_time, 0, False, str(e))
            logger.error(f"Query execution error: {e}")
            raise
    
    def _record_query_metrics(self, query: str, execution_time: float, 
                            rows_affected: int, success: bool, error: str = None):
        """Record query performance metrics"""
        with self.lock:
            metric = QueryMetrics(
                query=query[:100],  # Truncate long queries
                execution_time=execution_time,
                rows_affected=rows_affected,
                timestamp=datetime.now(),
                success=success,
                error=error
            )
            
            self.query_metrics.append(metric)
            
            # Keep only recent metrics
            if len(self.query_metrics) > self.max_metrics:
                self.query_metrics = self.query_metrics[-self.max_metrics:]
    
    def get_query_performance(self, hours: int = 24) -> Dict[str, Any]:
        """Get query performance analysis"""
        cutoff_time = datetime.now().timestamp() - (hours * 3600)
        
        recent_metrics = [
            m for m in self.query_metrics 
            if m.timestamp.timestamp() > cutoff_time
        ]
        
        if not recent_metrics:
            return {'message': 'No recent query metrics available'}
        
        # Calculate statistics
        execution_times = [m.execution_time for m in recent_metrics]
        successful_queries = [m for m in recent_metrics if m.success]
        failed_queries = [m for m in recent_metrics if not m.success]
        
        # Find slow queries
        slow_queries = [m for m in recent_metrics if m.execution_time > 1.0]
        
        # Most frequent queries
        query_counts = {}
        for m in recent_metrics:
            query_counts[m.query] = query_counts.get(m.query, 0) + 1
        
        most_frequent = sorted(query_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        
        return {
            'total_queries': len(recent_metrics),
            'successful_queries': len(successful_queries),
            'failed_queries': len(failed_queries),
            'success_rate': len(successful_queries) / len(recent_metrics) * 100,
            'avg_execution_time': sum(execution_times) / len(execution_times),
            'max_execution_time': max(execution_times),
            'min_execution_time': min(execution_times),
            'slow_queries_count': len(slow_queries),
            'most_frequent_queries': most_frequent,
            'slow_queries': [
                {
                    'query': m.query,
                    'execution_time': m.execution_time,
                    'timestamp': m.timestamp.isoformat()
                }
                for m in slow_queries[:10]
            ]
        }
    
    def optimize_database(self) -> Dict[str, Any]:
        """Run database optimization tasks"""
        optimization_results = {}
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Analyze tables
            cursor.execute("ANALYZE")
            optimization_results['analyze'] = 'Completed'
            
            # Vacuum database
            cursor.execute("VACUUM")
            optimization_results['vacuum'] = 'Completed'
            
            # Get database size
            cursor.execute("SELECT page_count * page_size as size FROM pragma_page_count(), pragma_page_size()")
            size_result = cursor.fetchone()
            optimization_results['database_size_bytes'] = size_result[0] if size_result else 0
            
            # Get index information
            cursor.execute("""
                SELECT name, tbl_name, sql 
                FROM sqlite_master 
                WHERE type='index' AND name NOT LIKE 'sqlite_%'
            """)
            indexes = cursor.fetchall()
            optimization_results['indexes'] = [
                {
                    'name': idx[0],
                    'table': idx[1],
                    'sql': idx[2]
                }
                for idx in indexes
            ]
            
            conn.commit()
        
        return optimization_results
    
    def get_database_stats(self) -> Dict[str, Any]:
        """Get comprehensive database statistics"""
        stats = {}
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Table sizes
            cursor.execute("""
                SELECT name, 
                       (SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name=m.name) as table_count,
                       (SELECT COUNT(*) FROM sqlite_master WHERE type='index' AND tbl_name=m.name) as index_count
                FROM sqlite_master m
                WHERE type='table' AND name NOT LIKE 'sqlite_%'
            """)
            
            tables = cursor.fetchall()
            stats['tables'] = [
                {
                    'name': table[0],
                    'index_count': table[2]
                }
                for table in tables
            ]
            
            # Row counts
            for table in tables:
                table_name = table[0]
                try:
                    cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                    count = cursor.fetchone()[0]
                    stats[f'{table_name}_count'] = count
                except Exception as e:
                    logger.warning(f"Could not get count for table {table_name}: {e}")
            
            # Database file size
            cursor.execute("SELECT page_count * page_size as size FROM pragma_page_count(), pragma_page_size()")
            size_result = cursor.fetchone()
            stats['database_size_bytes'] = size_result[0] if size_result else 0
        
        return stats
    
    def create_migration(self, version: str, description: str, up_sql: str, down_sql: str = None):
        """Create a database migration"""
        migration = {
            'version': version,
            'description': description,
            'up_sql': up_sql,
            'down_sql': down_sql,
            'created_at': datetime.now().isoformat()
        }
        
        # Store migration in system config
        self.execute_query(
            "INSERT OR REPLACE INTO system_config (key, value) VALUES (?, ?)",
            (f"migration_{version}", json.dumps(migration))
        )
        
        logger.info(f"Migration {version} created: {description}")
        return migration
    
    def run_migration(self, version: str) -> bool:
        """Run a specific migration"""
        try:
            migration_data = self.execute_query(
                "SELECT value FROM system_config WHERE key = ?",
                (f"migration_{version}",)
            )
            
            if not migration_data:
                logger.error(f"Migration {version} not found")
                return False
            
            migration = json.loads(migration_data[0]['value'])
            
            # Execute migration SQL
            self.execute_query(migration['up_sql'], fetch=False)
            
            # Mark as applied
            self.execute_query(
                "INSERT OR REPLACE INTO system_config (key, value) VALUES (?, ?)",
                (f"migration_{version}_applied", datetime.now().isoformat())
            )
            
            logger.info(f"Migration {version} applied successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to run migration {version}: {e}")
            return False

# Global database optimizer instance
db_optimizer = DatabaseOptimizer()

# ============================================================================
# MIGRATION SYSTEM
# ============================================================================

class MigrationManager:
    """Manage database migrations"""
    
    def __init__(self, db_optimizer: DatabaseOptimizer):
        self.db_optimizer = db_optimizer
        self.migrations: List[Dict[str, Any]] = []
        self._load_migrations()
    
    def _load_migrations(self):
        """Load all available migrations"""
        try:
            migrations_data = self.db_optimizer.execute_query(
                "SELECT key, value FROM system_config WHERE key LIKE 'migration_%' AND key NOT LIKE '%_applied'"
            )
            
            for migration_row in migrations_data:
                migration = json.loads(migration_row['value'])
                self.migrations.append(migration)
            
            # Sort by version
            self.migrations.sort(key=lambda x: x['version'])
            
        except Exception as e:
            logger.error(f"Failed to load migrations: {e}")
    
    def create_migration(self, version: str, description: str, up_sql: str, down_sql: str = None):
        """Create a new migration"""
        return self.db_optimizer.create_migration(version, description, up_sql, down_sql)
    
    def run_all_pending_migrations(self) -> List[str]:
        """Run all pending migrations"""
        applied_migrations = []
        
        for migration in self.migrations:
            version = migration['version']
            
            # Check if already applied
            applied_check = self.db_optimizer.execute_query(
                "SELECT value FROM system_config WHERE key = ?",
                (f"migration_{version}_applied",)
            )
            
            if not applied_check:
                if self.db_optimizer.run_migration(version):
                    applied_migrations.append(version)
        
        return applied_migrations
    
    def get_migration_status(self) -> Dict[str, Any]:
        """Get status of all migrations"""
        status = {
            'total_migrations': len(self.migrations),
            'applied_migrations': [],
            'pending_migrations': []
        }
        
        for migration in self.migrations:
            version = migration['version']
            
            applied_check = self.db_optimizer.execute_query(
                "SELECT value FROM system_config WHERE key = ?",
                (f"migration_{version}_applied",)
            )
            
            if applied_check:
                status['applied_migrations'].append({
                    'version': version,
                    'description': migration['description'],
                    'applied_at': applied_check[0]['value']
                })
            else:
                status['pending_migrations'].append({
                    'version': version,
                    'description': migration['description']
                })
        
        return status

# Global migration manager
migration_manager = MigrationManager(db_optimizer)

# Export the database optimization system
__all__ = [
    'DatabaseOptimizer', 'db_optimizer', 'MigrationManager', 'migration_manager',
    'QueryMetrics', 'IndexInfo'
]

