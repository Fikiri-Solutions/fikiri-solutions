"""
Fikiri Solutions - Usage Tracking System
Tracks usage for overage billing and feature gating
"""

import os
import stripe
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import sqlite3
import json

logger = logging.getLogger(__name__)

class UsageType(Enum):
    """Types of usage to track"""
    EMAIL_PROCESSING = "email_processing"
    LEAD_STORAGE = "lead_storage"
    AI_RESPONSES = "ai_responses"

@dataclass
class UsageRecord:
    """Individual usage record"""
    user_id: str
    usage_type: UsageType
    quantity: int
    timestamp: datetime
    metadata: Dict[str, Any] = None

@dataclass
class MonthlyUsage:
    """Monthly usage summary"""
    user_id: str
    month_year: str
    email_processing: int
    lead_storage: int
    ai_responses: int
    total_cost: float

class UsageTracker:
    """Tracks usage for overage billing and feature gating"""
    
    def __init__(self, db_path: str = "data/fikiri.db"):
        self.db_path = db_path
        self.overage_pricing = {
            UsageType.EMAIL_PROCESSING: 0.02,  # $0.02 per email
            UsageType.LEAD_STORAGE: 0.10,     # $0.10 per lead
            UsageType.AI_RESPONSES: 0.05      # $0.05 per AI response
        }
        self._init_database()
    
    def _init_database(self):
        """Initialize database tables for usage tracking"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Create usage_records table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS usage_records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    usage_type TEXT NOT NULL,
                    quantity INTEGER NOT NULL,
                    timestamp DATETIME NOT NULL,
                    metadata TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Create monthly_usage table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS monthly_usage (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    month_year TEXT NOT NULL,
                    email_processing INTEGER DEFAULT 0,
                    lead_storage INTEGER DEFAULT 0,
                    ai_responses INTEGER DEFAULT 0,
                    total_cost REAL DEFAULT 0.0,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(user_id, month_year)
                )
            ''')
            
            # Create indexes
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_usage_user_id ON usage_records(user_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_usage_type ON usage_records(usage_type)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_usage_timestamp ON usage_records(timestamp)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_monthly_user_month ON monthly_usage(user_id, month_year)')
            
            conn.commit()
            conn.close()
            logger.info("Usage tracking database initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize usage tracking database: {e}")
            raise
    
    def track_usage(self, user_id: str, usage_type: UsageType, quantity: int = 1, metadata: Dict[str, Any] = None) -> bool:
        """Track usage for a user"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Insert usage record
            cursor.execute('''
                INSERT INTO usage_records (user_id, usage_type, quantity, timestamp, metadata)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                user_id,
                usage_type.value,
                quantity,
                datetime.now().isoformat(),
                json.dumps(metadata) if metadata else None
            ))
            
            # Update monthly usage
            month_year = datetime.now().strftime('%Y-%m')
            self._update_monthly_usage(cursor, user_id, month_year, usage_type, quantity)
            
            conn.commit()
            conn.close()
            
            logger.info(f"Tracked {quantity} {usage_type.value} usage for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to track usage: {e}")
            return False
    
    def _update_monthly_usage(self, cursor, user_id: str, month_year: str, usage_type: UsageType, quantity: int):
        """Update monthly usage totals"""
        try:
            # Check if monthly record exists
            cursor.execute('''
                SELECT email_processing, lead_storage, ai_responses 
                FROM monthly_usage 
                WHERE user_id = ? AND month_year = ?
            ''', (user_id, month_year))
            
            result = cursor.fetchone()
            
            if result:
                # Update existing record
                email_processing, lead_storage, ai_responses = result
                
                if usage_type == UsageType.EMAIL_PROCESSING:
                    email_processing += quantity
                elif usage_type == UsageType.LEAD_STORAGE:
                    lead_storage += quantity
                elif usage_type == UsageType.AI_RESPONSES:
                    ai_responses += quantity
                
                # Calculate total cost
                total_cost = (
                    email_processing * self.overage_pricing[UsageType.EMAIL_PROCESSING] +
                    lead_storage * self.overage_pricing[UsageType.LEAD_STORAGE] +
                    ai_responses * self.overage_pricing[UsageType.AI_RESPONSES]
                )
                
                cursor.execute('''
                    UPDATE monthly_usage 
                    SET email_processing = ?, lead_storage = ?, ai_responses = ?, 
                        total_cost = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE user_id = ? AND month_year = ?
                ''', (email_processing, lead_storage, ai_responses, total_cost, user_id, month_year))
                
            else:
                # Create new record
                email_processing = quantity if usage_type == UsageType.EMAIL_PROCESSING else 0
                lead_storage = quantity if usage_type == UsageType.LEAD_STORAGE else 0
                ai_responses = quantity if usage_type == UsageType.AI_RESPONSES else 0
                
                total_cost = (
                    email_processing * self.overage_pricing[UsageType.EMAIL_PROCESSING] +
                    lead_storage * self.overage_pricing[UsageType.LEAD_STORAGE] +
                    ai_responses * self.overage_pricing[UsageType.AI_RESPONSES]
                )
                
                cursor.execute('''
                    INSERT INTO monthly_usage 
                    (user_id, month_year, email_processing, lead_storage, ai_responses, total_cost)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (user_id, month_year, email_processing, lead_storage, ai_responses, total_cost))
                
        except Exception as e:
            logger.error(f"Failed to update monthly usage: {e}")
            raise
    
    def get_monthly_usage(self, user_id: str, month_year: str = None) -> Optional[MonthlyUsage]:
        """Get monthly usage for a user"""
        try:
            if not month_year:
                month_year = datetime.now().strftime('%Y-%m')
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT email_processing, lead_storage, ai_responses, total_cost
                FROM monthly_usage 
                WHERE user_id = ? AND month_year = ?
            ''', (user_id, month_year))
            
            result = cursor.fetchone()
            conn.close()
            
            if result:
                email_processing, lead_storage, ai_responses, total_cost = result
                return MonthlyUsage(
                    user_id=user_id,
                    month_year=month_year,
                    email_processing=email_processing,
                    lead_storage=lead_storage,
                    ai_responses=ai_responses,
                    total_cost=total_cost
                )
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get monthly usage: {e}")
            return None
    
    def get_usage_history(self, user_id: str, days: int = 30) -> List[UsageRecord]:
        """Get usage history for a user"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            start_date = (datetime.now() - timedelta(days=days)).isoformat()
            
            cursor.execute('''
                SELECT usage_type, quantity, timestamp, metadata
                FROM usage_records 
                WHERE user_id = ? AND timestamp >= ?
                ORDER BY timestamp DESC
            ''', (user_id, start_date))
            
            results = cursor.fetchall()
            conn.close()
            
            usage_records = []
            for row in results:
                usage_type, quantity, timestamp, metadata = row
                usage_records.append(UsageRecord(
                    user_id=user_id,
                    usage_type=UsageType(usage_type),
                    quantity=quantity,
                    timestamp=datetime.fromisoformat(timestamp),
                    metadata=json.loads(metadata) if metadata else None
                ))
            
            return usage_records
            
        except Exception as e:
            logger.error(f"Failed to get usage history: {e}")
            return []
    
    def check_usage_limits(self, user_id: str, tier_limits: Dict[str, int]) -> Dict[str, Any]:
        """Check if user has exceeded usage limits"""
        try:
            current_usage = self.get_monthly_usage(user_id)
            
            if not current_usage:
                return {
                    'within_limits': True,
                    'overages': {},
                    'total_overage_cost': 0.0
                }
            
            overages = {}
            total_overage_cost = 0.0
            
            # Check email processing limit
            email_limit = tier_limits.get('emails_per_month', 0)
            if email_limit > 0 and current_usage.email_processing > email_limit:
                email_overage = current_usage.email_processing - email_limit
                overages['email_processing'] = email_overage
                total_overage_cost += email_overage * self.overage_pricing[UsageType.EMAIL_PROCESSING]
            
            # Check lead storage limit
            lead_limit = tier_limits.get('leads_storage', 0)
            if lead_limit > 0 and current_usage.lead_storage > lead_limit:
                lead_overage = current_usage.lead_storage - lead_limit
                overages['lead_storage'] = lead_overage
                total_overage_cost += lead_overage * self.overage_pricing[UsageType.LEAD_STORAGE]
            
            # Check AI responses limit
            ai_limit = tier_limits.get('ai_responses_per_month', 0)
            if ai_limit > 0 and current_usage.ai_responses > ai_limit:
                ai_overage = current_usage.ai_responses - ai_limit
                overages['ai_responses'] = ai_overage
                total_overage_cost += ai_overage * self.overage_pricing[UsageType.AI_RESPONSES]
            
            return {
                'within_limits': len(overages) == 0,
                'overages': overages,
                'total_overage_cost': total_overage_cost,
                'current_usage': {
                    'email_processing': current_usage.email_processing,
                    'lead_storage': current_usage.lead_storage,
                    'ai_responses': current_usage.ai_responses
                },
                'limits': tier_limits
            }
            
        except Exception as e:
            logger.error(f"Failed to check usage limits: {e}")
            return {
                'within_limits': True,
                'overages': {},
                'total_overage_cost': 0.0,
                'error': str(e)
            }
    
    def create_usage_invoice_items(self, user_id: str, subscription_item_id: str, overages: Dict[str, int]) -> List[Dict[str, Any]]:
        """Create Stripe invoice items for overage charges"""
        try:
            invoice_items = []
            
            for usage_type, quantity in overages.items():
                if quantity > 0:
                    # Create invoice item for overage
                    invoice_item = stripe.InvoiceItem.create(
                        customer=user_id,  # This should be the Stripe customer ID
                        amount=int(quantity * self.overage_pricing[UsageType(usage_type)] * 100),  # Convert to cents
                        currency='usd',
                        description=f'Overage: {usage_type} ({quantity} units)',
                        metadata={
                            'usage_type': usage_type,
                            'quantity': quantity,
                            'user_id': user_id
                        }
                    )
                    
                    invoice_items.append({
                        'id': invoice_item.id,
                        'usage_type': usage_type,
                        'quantity': quantity,
                        'amount': invoice_item.amount
                    })
            
            return invoice_items
            
        except Exception as e:
            logger.error(f"Failed to create usage invoice items: {e}")
            return []
    
    def get_usage_analytics(self, user_id: str, days: int = 30) -> Dict[str, Any]:
        """Get usage analytics for a user"""
        try:
            usage_history = self.get_usage_history(user_id, days)
            current_usage = self.get_monthly_usage(user_id)
            
            # Calculate daily averages
            daily_averages = {}
            for usage_type in UsageType:
                daily_total = sum(
                    record.quantity for record in usage_history 
                    if record.usage_type == usage_type
                )
                daily_averages[usage_type.value] = daily_total / days if days > 0 else 0
            
            # Calculate trends (simplified)
            trends = {}
            for usage_type in UsageType:
                recent_usage = [
                    record.quantity for record in usage_history 
                    if record.usage_type == usage_type and 
                    record.timestamp >= datetime.now() - timedelta(days=7)
                ]
                older_usage = [
                    record.quantity for record in usage_history 
                    if record.usage_type == usage_type and 
                    datetime.now() - timedelta(days=14) <= record.timestamp < datetime.now() - timedelta(days=7)
                ]
                
                recent_avg = sum(recent_usage) / len(recent_usage) if recent_usage else 0
                older_avg = sum(older_usage) / len(older_usage) if older_usage else 0
                
                if older_avg > 0:
                    trends[usage_type.value] = ((recent_avg - older_avg) / older_avg) * 100
                else:
                    trends[usage_type.value] = 0
            
            return {
                'current_usage': {
                    'email_processing': current_usage.email_processing if current_usage else 0,
                    'lead_storage': current_usage.lead_storage if current_usage else 0,
                    'ai_responses': current_usage.ai_responses if current_usage else 0,
                    'total_cost': current_usage.total_cost if current_usage else 0.0
                },
                'daily_averages': daily_averages,
                'trends': trends,
                'total_records': len(usage_history)
            }
            
        except Exception as e:
            logger.error(f"Failed to get usage analytics: {e}")
            return {
                'error': str(e)
            }
