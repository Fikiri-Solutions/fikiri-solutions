#!/usr/bin/env python3
"""
Fikiri Solutions - User Onboarding Dry Run Tests
Test as if you're a brand-new client connecting Gmail → CRM → automation in under 5 minutes
"""

import asyncio
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum
import requests
import json
import random
import string

logger = logging.getLogger(__name__)

class OnboardingStep(Enum):
    """Steps in the user onboarding process."""
    SIGNUP = "signup"
    EMAIL_VERIFICATION = "email_verification"
    GMAIL_CONNECTION = "gmail_connection"
    CRM_SETUP = "crm_setup"
    AUTOMATION_CONFIG = "automation_config"
    FIRST_EMAIL_PROCESSED = "first_email_processed"
    DASHBOARD_TOUR = "dashboard_tour"
    SUCCESS_METRICS = "success_metrics"

@dataclass
class OnboardingTestResult:
    """Result of an onboarding test step."""
    step: OnboardingStep
    success: bool
    duration_seconds: float
    error_message: Optional[str] = None
    data_collected: Optional[Dict[str, Any]] = None
    user_feedback: Optional[str] = None

class UserOnboardingTester:
    """User onboarding dry run testing system."""
    
    def __init__(self, base_url: str = "https://fikirisolutions.onrender.com"):
        self.base_url = base_url
        self.session = requests.Session()
        self.test_results: List[OnboardingTestResult] = []
        self.test_user_data = self._generate_test_user_data()
        self.target_duration = 300  # 5 minutes target
        
    def _generate_test_user_data(self) -> Dict[str, Any]:
        """Generate realistic test user data."""
        random_id = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
        return {
            "name": f"Test User {random_id}",
            "email": f"testuser{random_id}@example.com",
            "company": f"Test Company {random_id}",
            "phone": f"+1-555-{random.randint(100, 999)}-{random.randint(1000, 9999)}",
            "industry": random.choice(["landscaping", "restaurant", "medical", "retail", "consulting"]),
            "gmail_email": f"testgmail{random_id}@gmail.com",
            "expected_volume": random.choice(["low", "medium", "high"]),
            "automation_preferences": {
                "auto_reply": True,
                "lead_scoring": True,
                "follow_up_reminders": True,
                "reporting": True
            }
        }
    
    async def test_signup_process(self) -> OnboardingTestResult:
        """Test the user signup process."""
        logger.info("👤 Testing user signup process...")
        
        start_time = time.time()
        
        try:
            # Step 1: Visit signup page
            signup_url = f"{self.base_url}/signup"
            response = self.session.get(signup_url, timeout=10)
            
            if response.status_code != 200:
                return OnboardingTestResult(
                    step=OnboardingStep.SIGNUP,
                    success=False,
                    duration_seconds=time.time() - start_time,
                    error_message=f"Signup page not accessible: {response.status_code}"
                )
            
            # Step 2: Fill out signup form
            signup_data = {
                "name": self.test_user_data["name"],
                "email": self.test_user_data["email"],
                "company": self.test_user_data["company"],
                "phone": self.test_user_data["phone"],
                "industry": self.test_user_data["industry"],
                "password": "TestPassword123!",
                "confirm_password": "TestPassword123!"
            }
            
            response = self.session.post(signup_url, data=signup_data, timeout=10)
            
            if response.status_code in [200, 201, 302]:
                duration = time.time() - start_time
                return OnboardingTestResult(
                    step=OnboardingStep.SIGNUP,
                    success=True,
                    duration_seconds=duration,
                    data_collected=signup_data,
                    user_feedback="Signup process completed successfully"
                )
            else:
                return OnboardingTestResult(
                    step=OnboardingStep.SIGNUP,
                    success=False,
                    duration_seconds=time.time() - start_time,
                    error_message=f"Signup failed: {response.status_code}"
                )
        
        except Exception as e:
            return OnboardingTestResult(
                step=OnboardingStep.SIGNUP,
                success=False,
                duration_seconds=time.time() - start_time,
                error_message=f"Signup process error: {str(e)}"
            )
    
    async def test_email_verification(self) -> OnboardingTestResult:
        """Test email verification process."""
        logger.info("📧 Testing email verification process...")
        
        start_time = time.time()
        
        try:
            # Simulate email verification
            verification_url = f"{self.base_url}/verify-email"
            verification_data = {
                "email": self.test_user_data["email"],
                "token": "test_verification_token"
            }
            
            response = self.session.post(verification_url, data=verification_data, timeout=10)
            
            if response.status_code in [200, 201]:
                duration = time.time() - start_time
                return OnboardingTestResult(
                    step=OnboardingStep.EMAIL_VERIFICATION,
                    success=True,
                    duration_seconds=duration,
                    user_feedback="Email verification completed"
                )
            else:
                return OnboardingTestResult(
                    step=OnboardingStep.EMAIL_VERIFICATION,
                    success=False,
                    duration_seconds=time.time() - start_time,
                    error_message=f"Email verification failed: {response.status_code}"
                )
        
        except Exception as e:
            return OnboardingTestResult(
                step=OnboardingStep.EMAIL_VERIFICATION,
                success=False,
                duration_seconds=time.time() - start_time,
                error_message=f"Email verification error: {str(e)}"
            )
    
    async def test_gmail_connection(self) -> OnboardingTestResult:
        """Test Gmail connection process."""
        logger.info("📮 Testing Gmail connection process...")
        
        start_time = time.time()
        
        try:
            # Step 1: Initiate Gmail OAuth flow
            oauth_url = f"{self.base_url}/auth/google"
            response = self.session.get(oauth_url, timeout=10)
            
            if response.status_code != 200:
                return OnboardingTestResult(
                    step=OnboardingStep.GMAIL_CONNECTION,
                    success=False,
                    duration_seconds=time.time() - start_time,
                    error_message=f"Gmail OAuth initiation failed: {response.status_code}"
                )
            
            # Step 2: Simulate OAuth callback
            callback_url = f"{self.base_url}/auth/google/callback"
            callback_data = {
                "code": "test_oauth_code",
                "state": "test_state"
            }
            
            response = self.session.post(callback_url, data=callback_data, timeout=10)
            
            if response.status_code in [200, 201, 302]:
                duration = time.time() - start_time
                return OnboardingTestResult(
                    step=OnboardingStep.GMAIL_CONNECTION,
                    success=True,
                    duration_seconds=duration,
                    data_collected={"gmail_email": self.test_user_data["gmail_email"]},
                    user_feedback="Gmail connection established successfully"
                )
            else:
                return OnboardingTestResult(
                    step=OnboardingStep.GMAIL_CONNECTION,
                    success=False,
                    duration_seconds=time.time() - start_time,
                    error_message=f"Gmail connection failed: {response.status_code}"
                )
        
        except Exception as e:
            return OnboardingTestResult(
                step=OnboardingStep.GMAIL_CONNECTION,
                success=False,
                duration_seconds=time.time() - start_time,
                error_message=f"Gmail connection error: {str(e)}"
            )
    
    async def test_crm_setup(self) -> OnboardingTestResult:
        """Test CRM setup process."""
        logger.info("📊 Testing CRM setup process...")
        
        start_time = time.time()
        
        try:
            # Step 1: Access CRM setup page
            crm_setup_url = f"{self.base_url}/crm/setup"
            response = self.session.get(crm_setup_url, timeout=10)
            
            if response.status_code != 200:
                return OnboardingTestResult(
                    step=OnboardingStep.CRM_SETUP,
                    success=False,
                    duration_seconds=time.time() - start_time,
                    error_message=f"CRM setup page not accessible: {response.status_code}"
                )
            
            # Step 2: Configure CRM settings
            crm_config = {
                "lead_scoring_enabled": True,
                "auto_lead_creation": True,
                "follow_up_reminders": True,
                "email_templates": ["welcome", "follow_up", "thank_you"],
                "custom_fields": ["source", "priority", "notes"]
            }
            
            response = self.session.post(crm_setup_url, data=crm_config, timeout=10)
            
            if response.status_code in [200, 201]:
                duration = time.time() - start_time
                return OnboardingTestResult(
                    step=OnboardingStep.CRM_SETUP,
                    success=True,
                    duration_seconds=duration,
                    data_collected=crm_config,
                    user_feedback="CRM setup completed successfully"
                )
            else:
                return OnboardingTestResult(
                    step=OnboardingStep.CRM_SETUP,
                    success=False,
                    duration_seconds=time.time() - start_time,
                    error_message=f"CRM setup failed: {response.status_code}"
                )
        
        except Exception as e:
            return OnboardingTestResult(
                step=OnboardingStep.CRM_SETUP,
                success=False,
                duration_seconds=time.time() - start_time,
                error_message=f"CRM setup error: {str(e)}"
            )
    
    async def test_automation_config(self) -> OnboardingTestResult:
        """Test automation configuration process."""
        logger.info("🤖 Testing automation configuration process...")
        
        start_time = time.time()
        
        try:
            # Step 1: Access automation setup
            automation_url = f"{self.base_url}/automation/setup"
            response = self.session.get(automation_url, timeout=10)
            
            if response.status_code != 200:
                return OnboardingTestResult(
                    step=OnboardingStep.AUTOMATION_CONFIG,
                    success=False,
                    duration_seconds=time.time() - start_time,
                    error_message=f"Automation setup page not accessible: {response.status_code}"
                )
            
            # Step 2: Configure automation rules
            automation_config = {
                "auto_reply_enabled": True,
                "response_tone": "professional",
                "auto_reply_delay_minutes": 5,
                "max_responses_per_day": 50,
                "lead_scoring_rules": {
                    "high_priority_keywords": ["urgent", "asap", "immediately"],
                    "low_priority_keywords": ["maybe", "sometime", "later"]
                },
                "follow_up_rules": {
                    "enabled": True,
                    "delay_hours": 24,
                    "max_follow_ups": 3
                }
            }
            
            response = self.session.post(automation_url, data=automation_config, timeout=10)
            
            if response.status_code in [200, 201]:
                duration = time.time() - start_time
                return OnboardingTestResult(
                    step=OnboardingStep.AUTOMATION_CONFIG,
                    success=True,
                    duration_seconds=duration,
                    data_collected=automation_config,
                    user_feedback="Automation configuration completed successfully"
                )
            else:
                return OnboardingTestResult(
                    step=OnboardingStep.AUTOMATION_CONFIG,
                    success=False,
                    duration_seconds=time.time() - start_time,
                    error_message=f"Automation configuration failed: {response.status_code}"
                )
        
        except Exception as e:
            return OnboardingTestResult(
                step=OnboardingStep.AUTOMATION_CONFIG,
                success=False,
                duration_seconds=time.time() - start_time,
                error_message=f"Automation configuration error: {str(e)}"
            )
    
    async def test_first_email_processing(self) -> OnboardingTestResult:
        """Test first email processing."""
        logger.info("📨 Testing first email processing...")
        
        start_time = time.time()
        
        try:
            # Simulate receiving and processing an email
            test_email = {
                "from": "customer@example.com",
                "subject": "Interested in your services",
                "body": "Hi, I'm interested in learning more about your landscaping services. Can you provide a quote?",
                "received_at": datetime.now().isoformat()
            }
            
            # Send test email for processing
            process_url = f"{self.base_url}/api/email/process"
            response = self.session.post(process_url, json=test_email, timeout=10)
            
            if response.status_code in [200, 201]:
                # Check if lead was created
                leads_url = f"{self.base_url}/api/crm/leads"
                leads_response = self.session.get(leads_url, timeout=10)
                
                if leads_response.status_code == 200:
                    leads_data = leads_response.json()
                    if leads_data.get("leads") and len(leads_data["leads"]) > 0:
                        duration = time.time() - start_time
                        return OnboardingTestResult(
                            step=OnboardingStep.FIRST_EMAIL_PROCESSED,
                            success=True,
                            duration_seconds=duration,
                            data_collected={"email_processed": True, "lead_created": True},
                            user_feedback="First email processed and lead created successfully"
                        )
                
                return OnboardingTestResult(
                    step=OnboardingStep.FIRST_EMAIL_PROCESSED,
                    success=False,
                    duration_seconds=time.time() - start_time,
                    error_message="Email processed but lead not created"
                )
            else:
                return OnboardingTestResult(
                    step=OnboardingStep.FIRST_EMAIL_PROCESSED,
                    success=False,
                    duration_seconds=time.time() - start_time,
                    error_message=f"Email processing failed: {response.status_code}"
                )
        
        except Exception as e:
            return OnboardingTestResult(
                step=OnboardingStep.FIRST_EMAIL_PROCESSED,
                success=False,
                duration_seconds=time.time() - start_time,
                error_message=f"Email processing error: {str(e)}"
            )
    
    async def test_dashboard_tour(self) -> OnboardingTestResult:
        """Test dashboard tour and navigation."""
        logger.info("🎯 Testing dashboard tour...")
        
        start_time = time.time()
        
        try:
            # Test dashboard access
            dashboard_url = f"{self.base_url}/dashboard"
            response = self.session.get(dashboard_url, timeout=10)
            
            if response.status_code != 200:
                return OnboardingTestResult(
                    step=OnboardingStep.DASHBOARD_TOUR,
                    success=False,
                    duration_seconds=time.time() - start_time,
                    error_message=f"Dashboard not accessible: {response.status_code}"
                )
            
            # Test key dashboard features
            dashboard_features = [
                "/api/metrics",
                "/api/crm/leads",
                "/api/automation/status",
                "/api/email/stats"
            ]
            
            accessible_features = 0
            for feature in dashboard_features:
                feature_url = f"{self.base_url}{feature}"
                feature_response = self.session.get(feature_url, timeout=5)
                if feature_response.status_code == 200:
                    accessible_features += 1
            
            duration = time.time() - start_time
            success_rate = accessible_features / len(dashboard_features)
            
            return OnboardingTestResult(
                step=OnboardingStep.DASHBOARD_TOUR,
                success=success_rate >= 0.8,  # 80% of features accessible
                duration_seconds=duration,
                data_collected={"features_accessible": accessible_features, "total_features": len(dashboard_features)},
                user_feedback=f"Dashboard tour completed with {success_rate:.1%} feature accessibility"
            )
        
        except Exception as e:
            return OnboardingTestResult(
                step=OnboardingStep.DASHBOARD_TOUR,
                success=False,
                duration_seconds=time.time() - start_time,
                error_message=f"Dashboard tour error: {str(e)}"
            )
    
    async def test_success_metrics(self) -> OnboardingTestResult:
        """Test success metrics and reporting."""
        logger.info("📈 Testing success metrics...")
        
        start_time = time.time()
        
        try:
            # Test metrics collection
            metrics_url = f"{self.base_url}/api/metrics"
            response = self.session.get(metrics_url, timeout=10)
            
            if response.status_code == 200:
                metrics_data = response.json()
                
                # Check for key metrics
                required_metrics = ["total_emails", "active_leads", "ai_responses", "avg_response_time"]
                available_metrics = [metric for metric in required_metrics if metric in metrics_data.get("data", {})]
                
                duration = time.time() - start_time
                metrics_coverage = len(available_metrics) / len(required_metrics)
                
                return OnboardingTestResult(
                    step=OnboardingStep.SUCCESS_METRICS,
                    success=metrics_coverage >= 0.75,  # 75% of metrics available
                    duration_seconds=duration,
                    data_collected={"metrics_available": available_metrics, "coverage": metrics_coverage},
                    user_feedback=f"Success metrics collected with {metrics_coverage:.1%} coverage"
                )
            else:
                return OnboardingTestResult(
                    step=OnboardingStep.SUCCESS_METRICS,
                    success=False,
                    duration_seconds=time.time() - start_time,
                    error_message=f"Metrics collection failed: {response.status_code}"
                )
        
        except Exception as e:
            return OnboardingTestResult(
                step=OnboardingStep.SUCCESS_METRICS,
                success=False,
                duration_seconds=time.time() - start_time,
                error_message=f"Success metrics error: {str(e)}"
            )
    
    async def run_complete_onboarding_test(self) -> Dict[str, Any]:
        """Run complete user onboarding dry run test."""
        logger.info("🚀 Starting complete user onboarding dry run test...")
        
        start_time = time.time()
        
        test_results = {
            "start_time": datetime.now().isoformat(),
            "test_user": self.test_user_data,
            "target_duration_seconds": self.target_duration,
            "steps": {},
            "summary": {
                "total_steps": 0,
                "successful_steps": 0,
                "failed_steps": 0,
                "total_duration_seconds": 0,
                "success_rate": 0.0,
                "target_met": False
            },
            "recommendations": []
        }
        
        # Run all onboarding steps
        steps = [
            (OnboardingStep.SIGNUP, self.test_signup_process),
            (OnboardingStep.EMAIL_VERIFICATION, self.test_email_verification),
            (OnboardingStep.GMAIL_CONNECTION, self.test_gmail_connection),
            (OnboardingStep.CRM_SETUP, self.test_crm_setup),
            (OnboardingStep.AUTOMATION_CONFIG, self.test_automation_config),
            (OnboardingStep.FIRST_EMAIL_PROCESSED, self.test_first_email_processing),
            (OnboardingStep.DASHBOARD_TOUR, self.test_dashboard_tour),
            (OnboardingStep.SUCCESS_METRICS, self.test_success_metrics)
        ]
        
        for step, test_function in steps:
            logger.info(f"🔄 Running {step.value}...")
            result = await test_function()
            
            test_results["steps"][step.value] = {
                "success": result.success,
                "duration_seconds": result.duration_seconds,
                "error_message": result.error_message,
                "data_collected": result.data_collected,
                "user_feedback": result.user_feedback
            }
            
            test_results["summary"]["total_steps"] += 1
            if result.success:
                test_results["summary"]["successful_steps"] += 1
            else:
                test_results["summary"]["failed_steps"] += 1
            
            # Add delay between steps to simulate real user behavior
            await asyncio.sleep(2)
        
        # Calculate summary
        total_duration = time.time() - start_time
        test_results["summary"]["total_duration_seconds"] = total_duration
        test_results["summary"]["success_rate"] = (
            test_results["summary"]["successful_steps"] / test_results["summary"]["total_steps"] * 100
        )
        test_results["summary"]["target_met"] = total_duration <= self.target_duration
        
        test_results["end_time"] = datetime.now().isoformat()
        
        # Generate recommendations
        test_results["recommendations"] = self._generate_onboarding_recommendations(test_results)
        
        logger.info(f"🎯 Onboarding test complete:")
        logger.info(f"   Duration: {total_duration:.1f}s (target: {self.target_duration}s)")
        logger.info(f"   Success rate: {test_results['summary']['success_rate']:.1f}%")
        logger.info(f"   Target met: {test_results['summary']['target_met']}")
        
        return test_results
    
    def _generate_onboarding_recommendations(self, test_results: Dict[str, Any]) -> List[str]:
        """Generate recommendations based on onboarding test results."""
        recommendations = []
        
        # Check duration
        if not test_results["summary"]["target_met"]:
            recommendations.append("Reduce onboarding time - exceeds 5-minute target")
        
        # Check success rate
        if test_results["summary"]["success_rate"] < 90:
            recommendations.append("Improve onboarding success rate - below 90%")
        
        # Check individual steps
        failed_steps = []
        for step_name, step_result in test_results["steps"].items():
            if not step_result["success"]:
                failed_steps.append(step_name)
        
        if failed_steps:
            recommendations.append(f"Fix failed onboarding steps: {', '.join(failed_steps)}")
        
        # General recommendations
        recommendations.extend([
            "Implement onboarding progress indicators",
            "Add tooltips and help text for complex steps",
            "Provide video tutorials for key features",
            "Implement smart defaults for automation settings",
            "Add onboarding completion rewards/celebration"
        ])
        
        return recommendations

# Global onboarding tester instance
onboarding_tester = UserOnboardingTester()

async def run_user_onboarding_test():
    """Run comprehensive user onboarding dry run test."""
    logger.info("🚀 Starting user onboarding dry run test...")
    
    results = await onboarding_tester.run_complete_onboarding_test()
    
    logger.info(f"🎯 Onboarding test complete:")
    logger.info(f"   Duration: {results['summary']['total_duration_seconds']:.1f}s")
    logger.info(f"   Success rate: {results['summary']['success_rate']:.1f}%")
    logger.info(f"   Target met: {results['summary']['target_met']}")
    
    return results

if __name__ == "__main__":
    # Run user onboarding test
    asyncio.run(run_user_onboarding_test())
