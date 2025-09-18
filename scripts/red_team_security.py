#!/usr/bin/env python3
"""
Fikiri Solutions - Red Team Security Testing
Penetration testing beyond Bandit/npm audit (XSS, OAuth misconfigs, phishing)
"""

import asyncio
import requests
import json
import re
import time
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import subprocess
import os
from urllib.parse import urljoin, urlparse
import hashlib
import base64

logger = logging.getLogger(__name__)

class SecurityTestType(Enum):
    """Types of security tests to perform."""
    XSS_INJECTION = "xss_injection"
    SQL_INJECTION = "sql_injection"
    CSRF_ATTACK = "csrf_attack"
    OAUTH_MISCONFIG = "oauth_misconfig"
    PHISHING_SIMULATION = "phishing_simulation"
    BRUTE_FORCE = "brute_force"
    SESSION_HIJACKING = "session_hijacking"
    FILE_UPLOAD_VULN = "file_upload_vuln"
    DIRECTORY_TRAVERSAL = "directory_traversal"
    API_ENDPOINT_EXPOSURE = "api_endpoint_exposure"
    HEADER_INJECTION = "header_injection"
    JWT_VULNERABILITIES = "jwt_vulnerabilities"

@dataclass
class SecurityTestResult:
    """Represents a security test result."""
    test_type: SecurityTestType
    severity: str  # low, medium, high, critical
    vulnerable: bool
    description: str
    payload_used: Optional[str] = None
    response_code: Optional[int] = None
    response_body: Optional[str] = None
    recommendation: Optional[str] = None

class RedTeamSecurityTester:
    """Red team security testing engine."""
    
    def __init__(self, base_url: str = "https://fikirisolutions.onrender.com"):
        self.base_url = base_url
        self.session = requests.Session()
        self.test_results: List[SecurityTestResult] = []
        self.vulnerable_endpoints: List[str] = []
        
        # Common payloads for different attack types
        self.xss_payloads = [
            "<script>alert('XSS')</script>",
            "<img src=x onerror=alert('XSS')>",
            "javascript:alert('XSS')",
            "<svg onload=alert('XSS')>",
            "<iframe src=javascript:alert('XSS')>",
            "<body onload=alert('XSS')>",
            "<input onfocus=alert('XSS') autofocus>",
            "<select onfocus=alert('XSS') autofocus>",
            "<textarea onfocus=alert('XSS') autofocus>",
            "<keygen onfocus=alert('XSS') autofocus>",
            "<video><source onerror=alert('XSS')>",
            "<audio src=x onerror=alert('XSS')>",
            "<details open ontoggle=alert('XSS')>",
            "<marquee onstart=alert('XSS')>",
            "<math><mi//xlink:href=data:x,<script>alert('XSS')</script>"
        ]
        
        self.sql_payloads = [
            "' OR '1'='1",
            "' OR 1=1--",
            "' UNION SELECT * FROM users--",
            "'; DROP TABLE users; --",
            "' OR '1'='1' /*",
            "admin'--",
            "admin'/*",
            "' OR 1=1#",
            "' OR 'x'='x",
            "') OR ('1'='1",
            "' OR 1=1 LIMIT 1--",
            "' OR 1=1 ORDER BY 1--",
            "' OR 1=1 GROUP BY 1--",
            "' OR 1=1 HAVING 1=1--",
            "' OR 1=1 UNION SELECT 1,2,3--"
        ]
        
        self.csrf_payloads = [
            "<form action='{url}' method='POST'><input name='test' value='csrf'><input type='submit'></form>",
            "<img src='{url}?test=csrf'>",
            "<iframe src='{url}'></iframe>",
            "<script>fetch('{url}', {method: 'POST', body: 'test=csrf'})</script>"
        ]
    
    async def test_xss_injection(self) -> List[SecurityTestResult]:
        """Test for Cross-Site Scripting (XSS) vulnerabilities."""
        logger.info("🔍 Testing for XSS vulnerabilities...")
        results = []
        
        # Test endpoints that might be vulnerable to XSS
        test_endpoints = [
            "/api/crm/leads",
            "/api/auth/login",
            "/api/ai/chat",
            "/contact",
            "/search"
        ]
        
        for endpoint in test_endpoints:
            url = urljoin(self.base_url, endpoint)
            
            for payload in self.xss_payloads:
                try:
                    # Test GET parameters
                    response = self.session.get(url, params={"test": payload}, timeout=10)
                    
                    if self._is_xss_vulnerable(response.text, payload):
                        result = SecurityTestResult(
                            test_type=SecurityTestType.XSS_INJECTION,
                            severity="high",
                            vulnerable=True,
                            description=f"XSS vulnerability found in {endpoint}",
                            payload_used=payload,
                            response_code=response.status_code,
                            response_body=response.text[:500],
                            recommendation="Implement proper input sanitization and output encoding"
                        )
                        results.append(result)
                        logger.warning(f"⚠️ XSS vulnerability found: {endpoint}")
                    
                    # Test POST data
                    response = self.session.post(url, data={"test": payload}, timeout=10)
                    
                    if self._is_xss_vulnerable(response.text, payload):
                        result = SecurityTestResult(
                            test_type=SecurityTestType.XSS_INJECTION,
                            severity="high",
                            vulnerable=True,
                            description=f"XSS vulnerability found in {endpoint} (POST)",
                            payload_used=payload,
                            response_code=response.status_code,
                            response_body=response.text[:500],
                            recommendation="Implement proper input sanitization and output encoding"
                        )
                        results.append(result)
                        logger.warning(f"⚠️ XSS vulnerability found: {endpoint} (POST)")
                
                except Exception as e:
                    logger.error(f"❌ XSS test failed for {endpoint}: {e}")
        
        return results
    
    async def test_sql_injection(self) -> List[SecurityTestResult]:
        """Test for SQL injection vulnerabilities."""
        logger.info("🔍 Testing for SQL injection vulnerabilities...")
        results = []
        
        test_endpoints = [
            "/api/crm/leads",
            "/api/auth/login",
            "/api/search",
            "/api/users"
        ]
        
        for endpoint in test_endpoints:
            url = urljoin(self.base_url, endpoint)
            
            for payload in self.sql_payloads:
                try:
                    # Test GET parameters
                    response = self.session.get(url, params={"id": payload}, timeout=10)
                    
                    if self._is_sql_injection_vulnerable(response.text, response.status_code):
                        result = SecurityTestResult(
                            test_type=SecurityTestType.SQL_INJECTION,
                            severity="critical",
                            vulnerable=True,
                            description=f"SQL injection vulnerability found in {endpoint}",
                            payload_used=payload,
                            response_code=response.status_code,
                            response_body=response.text[:500],
                            recommendation="Use parameterized queries and input validation"
                        )
                        results.append(result)
                        logger.warning(f"⚠️ SQL injection vulnerability found: {endpoint}")
                    
                    # Test POST data
                    response = self.session.post(url, data={"id": payload}, timeout=10)
                    
                    if self._is_sql_injection_vulnerable(response.text, response.status_code):
                        result = SecurityTestResult(
                            test_type=SecurityTestType.SQL_INJECTION,
                            severity="critical",
                            vulnerable=True,
                            description=f"SQL injection vulnerability found in {endpoint} (POST)",
                            payload_used=payload,
                            response_code=response.status_code,
                            response_body=response.text[:500],
                            recommendation="Use parameterized queries and input validation"
                        )
                        results.append(result)
                        logger.warning(f"⚠️ SQL injection vulnerability found: {endpoint} (POST)")
                
                except Exception as e:
                    logger.error(f"❌ SQL injection test failed for {endpoint}: {e}")
        
        return results
    
    async def test_csrf_attack(self) -> List[SecurityTestResult]:
        """Test for Cross-Site Request Forgery (CSRF) vulnerabilities."""
        logger.info("🔍 Testing for CSRF vulnerabilities...")
        results = []
        
        # Test endpoints that modify data
        test_endpoints = [
            "/api/crm/leads",
            "/api/auth/logout",
            "/api/settings"
        ]
        
        for endpoint in test_endpoints:
            url = urljoin(self.base_url, endpoint)
            
            try:
                # Test if CSRF protection is missing
                response = self.session.post(url, data={"test": "csrf"}, timeout=10)
                
                if response.status_code == 200 and "csrf" in response.text.lower():
                    result = SecurityTestResult(
                        test_type=SecurityTestType.CSRF_ATTACK,
                        severity="medium",
                        vulnerable=True,
                        description=f"Potential CSRF vulnerability in {endpoint}",
                        payload_used="CSRF test payload",
                        response_code=response.status_code,
                        response_body=response.text[:500],
                        recommendation="Implement CSRF tokens and SameSite cookies"
                    )
                    results.append(result)
                    logger.warning(f"⚠️ Potential CSRF vulnerability found: {endpoint}")
            
            except Exception as e:
                logger.error(f"❌ CSRF test failed for {endpoint}: {e}")
        
        return results
    
    async def test_oauth_misconfig(self) -> List[SecurityTestResult]:
        """Test for OAuth misconfigurations."""
        logger.info("🔍 Testing for OAuth misconfigurations...")
        results = []
        
        # Test OAuth endpoints
        oauth_endpoints = [
            "/oauth/authorize",
            "/oauth/token",
            "/oauth/callback",
            "/auth/google",
            "/auth/github"
        ]
        
        for endpoint in oauth_endpoints:
            url = urljoin(self.base_url, endpoint)
            
            try:
                response = self.session.get(url, timeout=10)
                
                # Check for common OAuth misconfigurations
                vulnerabilities = []
                
                if response.status_code == 200:
                    # Check for missing state parameter
                    if "state" not in response.text.lower():
                        vulnerabilities.append("Missing state parameter")
                    
                    # Check for insecure redirects
                    if "redirect_uri" in response.text and "http://" in response.text:
                        vulnerabilities.append("Insecure redirect URI")
                    
                    # Check for missing PKCE
                    if "code_challenge" not in response.text.lower():
                        vulnerabilities.append("Missing PKCE protection")
                
                if vulnerabilities:
                    result = SecurityTestResult(
                        test_type=SecurityTestType.OAUTH_MISCONFIG,
                        severity="high",
                        vulnerable=True,
                        description=f"OAuth misconfigurations found in {endpoint}",
                        payload_used="OAuth configuration test",
                        response_code=response.status_code,
                        response_body=response.text[:500],
                        recommendation=f"Fix OAuth misconfigurations: {', '.join(vulnerabilities)}"
                    )
                    results.append(result)
                    logger.warning(f"⚠️ OAuth misconfigurations found: {endpoint}")
            
            except Exception as e:
                logger.error(f"❌ OAuth test failed for {endpoint}: {e}")
        
        return results
    
    async def test_api_endpoint_exposure(self) -> List[SecurityTestResult]:
        """Test for exposed API endpoints."""
        logger.info("🔍 Testing for exposed API endpoints...")
        results = []
        
        # Common API endpoints to test
        api_endpoints = [
            "/api/admin",
            "/api/users",
            "/api/config",
            "/api/secrets",
            "/api/keys",
            "/api/tokens",
            "/api/database",
            "/api/logs",
            "/api/debug",
            "/api/test",
            "/api/dev",
            "/api/staging",
            "/api/internal",
            "/api/private",
            "/api/backup",
            "/api/restore",
            "/api/migrate",
            "/api/seed",
            "/api/reset",
            "/api/clear"
        ]
        
        for endpoint in api_endpoints:
            url = urljoin(self.base_url, endpoint)
            
            try:
                response = self.session.get(url, timeout=5)
                
                if response.status_code == 200:
                    result = SecurityTestResult(
                        test_type=SecurityTestType.API_ENDPOINT_EXPOSURE,
                        severity="medium",
                        vulnerable=True,
                        description=f"Exposed API endpoint: {endpoint}",
                        payload_used="GET request",
                        response_code=response.status_code,
                        response_body=response.text[:500],
                        recommendation="Restrict access to sensitive API endpoints"
                    )
                    results.append(result)
                    logger.warning(f"⚠️ Exposed API endpoint found: {endpoint}")
            
            except Exception as e:
                logger.error(f"❌ API endpoint test failed for {endpoint}: {e}")
        
        return results
    
    async def test_jwt_vulnerabilities(self) -> List[SecurityTestResult]:
        """Test for JWT vulnerabilities."""
        logger.info("🔍 Testing for JWT vulnerabilities...")
        results = []
        
        # Test JWT endpoints
        jwt_endpoints = [
            "/api/auth/login",
            "/api/auth/token",
            "/api/auth/refresh"
        ]
        
        for endpoint in jwt_endpoints:
            url = urljoin(self.base_url, endpoint)
            
            try:
                # Test with malformed JWT
                malformed_jwt = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.invalid"
                response = self.session.get(url, headers={"Authorization": f"Bearer {malformed_jwt}"}, timeout=10)
                
                if response.status_code == 200:
                    result = SecurityTestResult(
                        test_type=SecurityTestType.JWT_VULNERABILITIES,
                        severity="high",
                        vulnerable=True,
                        description=f"JWT vulnerability found in {endpoint}",
                        payload_used=malformed_jwt,
                        response_code=response.status_code,
                        response_body=response.text[:500],
                        recommendation="Implement proper JWT validation and signature verification"
                    )
                    results.append(result)
                    logger.warning(f"⚠️ JWT vulnerability found: {endpoint}")
            
            except Exception as e:
                logger.error(f"❌ JWT test failed for {endpoint}: {e}")
        
        return results
    
    def _is_xss_vulnerable(self, response_text: str, payload: str) -> bool:
        """Check if response is vulnerable to XSS."""
        # Check if payload is reflected in response without proper encoding
        if payload in response_text:
            return True
        
        # Check for common XSS patterns
        xss_patterns = [
            r"<script[^>]*>.*</script>",
            r"javascript:",
            r"on\w+\s*=",
            r"<iframe[^>]*>",
            r"<img[^>]*onerror",
            r"<svg[^>]*onload"
        ]
        
        for pattern in xss_patterns:
            if re.search(pattern, response_text, re.IGNORECASE):
                return True
        
        return False
    
    def _is_sql_injection_vulnerable(self, response_text: str, status_code: int) -> bool:
        """Check if response indicates SQL injection vulnerability."""
        # Check for SQL error messages
        sql_errors = [
            "sql syntax",
            "mysql error",
            "postgresql error",
            "sqlite error",
            "database error",
            "syntax error",
            "query failed",
            "invalid query"
        ]
        
        for error in sql_errors:
            if error in response_text.lower():
                return True
        
        # Check for successful injection indicators
        if status_code == 200 and any(word in response_text.lower() for word in ["admin", "user", "password", "login"]):
            return True
        
        return False
    
    async def run_comprehensive_security_test(self) -> Dict[str, Any]:
        """Run comprehensive security testing."""
        logger.info("🚀 Starting comprehensive red team security testing...")
        
        start_time = time.time()
        
        # Run all security tests
        test_results = {
            "start_time": datetime.now().isoformat(),
            "base_url": self.base_url,
            "tests": {},
            "summary": {
                "total_tests": 0,
                "vulnerabilities_found": 0,
                "critical_vulnerabilities": 0,
                "high_vulnerabilities": 0,
                "medium_vulnerabilities": 0,
                "low_vulnerabilities": 0
            }
        }
        
        # XSS Testing
        logger.info("🔍 Running XSS injection tests...")
        xss_results = await self.test_xss_injection()
        test_results["tests"]["xss_injection"] = [result.__dict__ for result in xss_results]
        
        # SQL Injection Testing
        logger.info("🔍 Running SQL injection tests...")
        sql_results = await self.test_sql_injection()
        test_results["tests"]["sql_injection"] = [result.__dict__ for result in sql_results]
        
        # CSRF Testing
        logger.info("🔍 Running CSRF tests...")
        csrf_results = await self.test_csrf_attack()
        test_results["tests"]["csrf_attack"] = [result.__dict__ for result in csrf_results]
        
        # OAuth Misconfiguration Testing
        logger.info("🔍 Running OAuth misconfiguration tests...")
        oauth_results = await self.test_oauth_misconfig()
        test_results["tests"]["oauth_misconfig"] = [result.__dict__ for result in oauth_results]
        
        # API Endpoint Exposure Testing
        logger.info("🔍 Running API endpoint exposure tests...")
        api_results = await self.test_api_endpoint_exposure()
        test_results["tests"]["api_endpoint_exposure"] = [result.__dict__ for result in api_results]
        
        # JWT Vulnerability Testing
        logger.info("🔍 Running JWT vulnerability tests...")
        jwt_results = await self.test_jwt_vulnerabilities()
        test_results["tests"]["jwt_vulnerabilities"] = [result.__dict__ for result in jwt_results]
        
        # Compile all results
        all_results = xss_results + sql_results + csrf_results + oauth_results + api_results + jwt_results
        
        # Generate summary
        test_results["summary"]["total_tests"] = len(all_results)
        test_results["summary"]["vulnerabilities_found"] = sum(1 for r in all_results if r.vulnerable)
        
        for result in all_results:
            if result.vulnerable:
                if result.severity == "critical":
                    test_results["summary"]["critical_vulnerabilities"] += 1
                elif result.severity == "high":
                    test_results["summary"]["high_vulnerabilities"] += 1
                elif result.severity == "medium":
                    test_results["summary"]["medium_vulnerabilities"] += 1
                elif result.severity == "low":
                    test_results["summary"]["low_vulnerabilities"] += 1
        
        test_results["end_time"] = datetime.now().isoformat()
        test_results["duration_seconds"] = time.time() - start_time
        
        # Generate recommendations
        test_results["recommendations"] = self._generate_security_recommendations(all_results)
        
        logger.info(f"🎯 Security testing complete: {test_results['summary']['vulnerabilities_found']} vulnerabilities found")
        
        return test_results
    
    def _generate_security_recommendations(self, results: List[SecurityTestResult]) -> List[str]:
        """Generate security recommendations based on test results."""
        recommendations = []
        
        # Count vulnerabilities by type
        vulnerability_counts = {}
        for result in results:
            if result.vulnerable:
                test_type = result.test_type.value
                vulnerability_counts[test_type] = vulnerability_counts.get(test_type, 0) + 1
        
        # Generate specific recommendations
        if vulnerability_counts.get("xss_injection", 0) > 0:
            recommendations.append("Implement comprehensive input sanitization and output encoding")
        
        if vulnerability_counts.get("sql_injection", 0) > 0:
            recommendations.append("Use parameterized queries and input validation")
        
        if vulnerability_counts.get("csrf_attack", 0) > 0:
            recommendations.append("Implement CSRF tokens and SameSite cookies")
        
        if vulnerability_counts.get("oauth_misconfig", 0) > 0:
            recommendations.append("Review and fix OAuth configuration")
        
        if vulnerability_counts.get("api_endpoint_exposure", 0) > 0:
            recommendations.append("Restrict access to sensitive API endpoints")
        
        if vulnerability_counts.get("jwt_vulnerabilities", 0) > 0:
            recommendations.append("Implement proper JWT validation and signature verification")
        
        # General recommendations
        if len(results) > 0:
            recommendations.extend([
                "Implement Web Application Firewall (WAF)",
                "Enable security headers (CSP, HSTS, X-Frame-Options)",
                "Regular security audits and penetration testing",
                "Implement rate limiting and DDoS protection",
                "Monitor and log security events"
            ])
        
        return recommendations

# Global security tester instance
security_tester = RedTeamSecurityTester()

async def run_red_team_security_test():
    """Run comprehensive red team security testing."""
    logger.info("🚀 Starting red team security testing...")
    
    results = await security_tester.run_comprehensive_security_test()
    
    logger.info(f"🎯 Security testing complete:")
    logger.info(f"   Total tests: {results['summary']['total_tests']}")
    logger.info(f"   Vulnerabilities found: {results['summary']['vulnerabilities_found']}")
    logger.info(f"   Critical: {results['summary']['critical_vulnerabilities']}")
    logger.info(f"   High: {results['summary']['high_vulnerabilities']}")
    logger.info(f"   Medium: {results['summary']['medium_vulnerabilities']}")
    logger.info(f"   Low: {results['summary']['low_vulnerabilities']}")
    
    return results

if __name__ == "__main__":
    # Run red team security testing
    asyncio.run(run_red_team_security_test())
