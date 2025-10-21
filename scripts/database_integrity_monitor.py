#!/usr/bin/env python3
"""
Database Integrity Monitor for Fikiri Solutions
Monitors onboarding completion rates and sends alerts for anomalies
"""

import os
import sys
import sqlite3
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Tuple

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.database_optimization import db_optimizer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class DatabaseIntegrityMonitor:
    """Monitor database integrity and onboarding completion rates"""
    
    def __init__(self):
        self.db_optimizer = db_optimizer
        
    def check_onboarding_integrity(self) -> Dict[str, any]:
        """Check onboarding data integrity"""
        try:
            # Get total users
            total_users = self.db_optimizer.execute_query(
                "SELECT COUNT(*) as count FROM users WHERE is_active = 1"
            )[0]['count']
            
            # Get users with incomplete onboarding
            incomplete_onboarding = self.db_optimizer.execute_query(
                "SELECT COUNT(*) as count FROM users WHERE onboarding_completed = 0 AND is_active = 1"
            )[0]['count']
            
            # Get users with onboarding data but incomplete status
            inconsistent_data = self.db_optimizer.execute_query("""
                SELECT COUNT(*) as count 
                FROM users u 
                LEFT JOIN onboarding_info oi ON u.id = oi.user_id 
                WHERE u.is_active = 1 
                AND u.onboarding_completed = 0 
                AND oi.user_id IS NOT NULL
            """)[0]['count']
            
            # Get users with completed status but no onboarding data
            missing_data = self.db_optimizer.execute_query("""
                SELECT COUNT(*) as count 
                FROM users u 
                LEFT JOIN onboarding_info oi ON u.id = oi.user_id 
                WHERE u.is_active = 1 
                AND u.onboarding_completed = 1 
                AND oi.user_id IS NULL
            """)[0]['count']
            
            # Calculate completion rate
            completion_rate = ((total_users - incomplete_onboarding) / total_users * 100) if total_users > 0 else 0
            
            return {
                'total_users': total_users,
                'incomplete_onboarding': incomplete_onboarding,
                'inconsistent_data': inconsistent_data,
                'missing_data': missing_data,
                'completion_rate': round(completion_rate, 2),
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error checking onboarding integrity: {e}")
            return {'error': str(e)}
    
    def check_recent_onboarding_trends(self, days: int = 7) -> Dict[str, any]:
        """Check onboarding trends over the last N days"""
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            
            # Get daily onboarding completions
            daily_completions = self.db_optimizer.execute_query("""
                SELECT 
                    DATE(updated_at) as date,
                    COUNT(*) as completions
                FROM users 
                WHERE onboarding_completed = 1 
                AND updated_at >= ?
                GROUP BY DATE(updated_at)
                ORDER BY date DESC
            """, (cutoff_date.isoformat(),))
            
            # Get daily signups
            daily_signups = self.db_optimizer.execute_query("""
                SELECT 
                    DATE(created_at) as date,
                    COUNT(*) as signups
                FROM users 
                WHERE created_at >= ?
                GROUP BY DATE(created_at)
                ORDER BY date DESC
            """, (cutoff_date.isoformat(),))
            
            return {
                'daily_completions': daily_completions,
                'daily_signups': daily_signups,
                'period_days': days,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error checking onboarding trends: {e}")
            return {'error': str(e)}
    
    def check_data_consistency(self) -> List[Dict[str, any]]:
        """Check for data consistency issues"""
        issues = []
        
        try:
            # Check for orphaned onboarding data
            orphaned_data = self.db_optimizer.execute_query("""
                SELECT oi.user_id, oi.name, oi.company
                FROM onboarding_info oi
                LEFT JOIN users u ON oi.user_id = u.id
                WHERE u.id IS NULL
            """)
            
            if orphaned_data:
                issues.append({
                    'type': 'orphaned_onboarding_data',
                    'count': len(orphaned_data),
                    'description': 'Onboarding data exists for non-existent users'
                })
            
            # Check for users with invalid onboarding steps
            invalid_steps = self.db_optimizer.execute_query("""
                SELECT id, email, onboarding_step, onboarding_completed
                FROM users 
                WHERE onboarding_step < 1 AND onboarding_step != -1
                AND is_active = 1
            """)
            
            if invalid_steps:
                issues.append({
                    'type': 'invalid_onboarding_steps',
                    'count': len(invalid_steps),
                    'description': 'Users with invalid onboarding step values'
                })
            
            # Check for users stuck in onboarding
            stuck_users = self.db_optimizer.execute_query("""
                SELECT id, email, onboarding_step, created_at
                FROM users 
                WHERE onboarding_completed = 0 
                AND created_at < ?
                AND is_active = 1
            """, ((datetime.now() - timedelta(days=7)).isoformat(),))
            
            if stuck_users:
                issues.append({
                    'type': 'stuck_in_onboarding',
                    'count': len(stuck_users),
                    'description': 'Users stuck in onboarding for more than 7 days'
                })
            
            return issues
            
        except Exception as e:
            logger.error(f"Error checking data consistency: {e}")
            return [{'type': 'error', 'description': str(e)}]
    
    def generate_report(self) -> Dict[str, any]:
        """Generate a comprehensive integrity report"""
        logger.info("Generating database integrity report...")
        
        integrity_check = self.check_onboarding_integrity()
        trends = self.check_recent_onboarding_trends()
        consistency_issues = self.check_data_consistency()
        
        report = {
            'integrity': integrity_check,
            'trends': trends,
            'consistency_issues': consistency_issues,
            'generated_at': datetime.now().isoformat()
        }
        
        # Log critical issues
        if integrity_check.get('completion_rate', 0) < 50:
            logger.warning(f"Low onboarding completion rate: {integrity_check.get('completion_rate')}%")
        
        if consistency_issues:
            logger.warning(f"Found {len(consistency_issues)} consistency issues")
            for issue in consistency_issues:
                logger.warning(f"  - {issue['type']}: {issue['description']}")
        
        return report

def main():
    """Main function for running the integrity monitor"""
    monitor = DatabaseIntegrityMonitor()
    
    # Generate and print report
    report = monitor.generate_report()
    
    print("=" * 60)
    print("FIKIRI SOLUTIONS - DATABASE INTEGRITY REPORT")
    print("=" * 60)
    print(f"Generated at: {report['generated_at']}")
    print()
    
    # Integrity summary
    integrity = report['integrity']
    if 'error' not in integrity:
        print("ONBOARDING INTEGRITY SUMMARY:")
        print(f"  Total active users: {integrity['total_users']}")
        print(f"  Incomplete onboarding: {integrity['incomplete_onboarding']}")
        print(f"  Completion rate: {integrity['completion_rate']}%")
        print(f"  Inconsistent data: {integrity['inconsistent_data']}")
        print(f"  Missing data: {integrity['missing_data']}")
        print()
    
    # Consistency issues
    issues = report['consistency_issues']
    if issues:
        print("CONSISTENCY ISSUES:")
        for issue in issues:
            print(f"  - {issue['type']}: {issue['count']} ({issue['description']})")
        print()
    else:
        print("✅ No consistency issues found")
        print()
    
    # Trends
    trends = report['trends']
    if 'error' not in trends:
        print(f"RECENT TRENDS ({trends['period_days']} days):")
        print(f"  Daily completions: {len(trends['daily_completions'])} days with data")
        print(f"  Daily signups: {len(trends['daily_signups'])} days with data")
        print()
    
    print("=" * 60)
    
    # Return exit code based on issues found
    if issues:
        return 1  # Issues found
    else:
        return 0  # No issues

if __name__ == "__main__":
    sys.exit(main())
