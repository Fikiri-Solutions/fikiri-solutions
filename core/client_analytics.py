"""
Fikiri Solutions - Client Analytics & Reporting System
Generates ROI reports and business insights for each industry vertical
"""

import os
import json
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from openai import OpenAI

@dataclass
class ClientMetric:
    """Individual metric for client reporting"""
    metric_name: str
    value: float
    unit: str
    improvement: float  # Percentage improvement
    industry_benchmark: float
    description: str

@dataclass
class ClientReport:
    """Comprehensive client report"""
    client_id: str
    industry: str
    report_period: str
    generated_at: datetime
    
    # Key Metrics
    total_emails_handled: int
    total_appointments_scheduled: int
    total_leads_generated: int
    total_revenue_impact: float
    
    # Time Savings
    hours_saved: float
    staff_efficiency_gain: float
    
    # Business Impact
    customer_satisfaction_score: float
    retention_rate: float
    conversion_rate: float
    
    # ROI Metrics
    monthly_cost: float
    roi_percentage: float
    payback_period_days: int
    
    # Industry-Specific Metrics
    industry_metrics: List[ClientMetric]
    
    # Recommendations
    recommendations: List[str]
    next_quarter_goals: List[str]

class ClientAnalyticsEngine:
    """Generates comprehensive client reports and ROI analysis"""
    
    def __init__(self):
        # Initialize OpenAI client only if API key is available
        api_key = os.getenv('OPENAI_API_KEY')
        if api_key:
            self.client = OpenAI(api_key=api_key)
        else:
            self.client = None
            print("⚠️  OpenAI API key not found - Analytics features will be limited")
        
        self.industry_benchmarks = self._load_industry_benchmarks()
        
    def _load_industry_benchmarks(self) -> Dict[str, Dict[str, float]]:
        """Load industry-specific benchmarks for comparison"""
        return {
            'landscaping': {
                'avg_emails_per_month': 150,
                'avg_appointments_per_month': 45,
                'avg_lead_conversion': 0.25,
                'avg_hours_saved_per_month': 20,
                'avg_revenue_per_client': 2500
            },
            'restaurant': {
                'avg_emails_per_month': 300,
                'avg_reservations_per_month': 200,
                'avg_upsell_rate': 0.15,
                'avg_hours_saved_per_month': 25,
                'avg_revenue_per_client': 8000
            },
            'medical_practice': {
                'avg_emails_per_month': 200,
                'avg_appointments_per_month': 120,
                'avg_no_show_rate': 0.20,
                'avg_hours_saved_per_month': 30,
                'avg_revenue_per_client': 15000
            },
            'real_estate': {
                'avg_emails_per_month': 400,
                'avg_leads_per_month': 25,
                'avg_conversion_rate': 0.08,
                'avg_hours_saved_per_month': 35,
                'avg_revenue_per_client': 20000
            },
            'tax_services': {
                'avg_emails_per_month': 250,
                'avg_clients_per_month': 50,
                'avg_compliance_rate': 0.95,
                'avg_hours_saved_per_month': 40,
                'avg_revenue_per_client': 12000
            }
        }
    
    def generate_client_report(self, client_id: str, industry: str, usage_data: Dict[str, Any]) -> ClientReport:
        """Generate comprehensive client report with ROI analysis"""
        
        # Calculate key metrics
        total_emails = usage_data.get('emails_handled', 0)
        total_appointments = usage_data.get('appointments_scheduled', 0)
        total_leads = usage_data.get('leads_generated', 0)
        total_tool_calls = usage_data.get('tool_calls', 0)
        
        # Calculate time savings (based on industry benchmarks)
        hours_saved = self._calculate_hours_saved(industry, total_emails, total_appointments, total_tool_calls)
        
        # Calculate revenue impact
        revenue_impact = self._calculate_revenue_impact(industry, total_leads, total_appointments)
        
        # Calculate ROI
        monthly_cost = self._get_monthly_cost(industry)
        roi_percentage = (revenue_impact / monthly_cost) * 100 if monthly_cost > 0 else 0
        payback_period = (monthly_cost / (revenue_impact / 30)) if revenue_impact > 0 else 0
        
        # Generate industry-specific metrics
        industry_metrics = self._generate_industry_metrics(industry, usage_data)
        
        # Generate AI-powered recommendations
        recommendations = self._generate_recommendations(industry, usage_data, industry_metrics)
        next_quarter_goals = self._generate_next_quarter_goals(industry, usage_data)
        
        return ClientReport(
            client_id=client_id,
            industry=industry,
            report_period=f"{datetime.now().strftime('%B %Y')}",
            generated_at=datetime.now(),
            
            total_emails_handled=total_emails,
            total_appointments_scheduled=total_appointments,
            total_leads_generated=total_leads,
            total_revenue_impact=revenue_impact,
            
            hours_saved=hours_saved,
            staff_efficiency_gain=(hours_saved / 160) * 100,  # Assuming 160 working hours/month
            
            customer_satisfaction_score=self._calculate_satisfaction_score(industry, usage_data),
            retention_rate=self._calculate_retention_rate(industry, usage_data),
            conversion_rate=self._calculate_conversion_rate(industry, usage_data),
            
            monthly_cost=monthly_cost,
            roi_percentage=roi_percentage,
            payback_period_days=int(payback_period),
            
            industry_metrics=industry_metrics,
            recommendations=recommendations,
            next_quarter_goals=next_quarter_goals
        )
    
    def _calculate_hours_saved(self, industry: str, emails: int, appointments: int, tool_calls: int) -> float:
        """Calculate hours saved based on industry-specific benchmarks"""
        industry_rates = {
            'landscaping': {'email_time': 0.1, 'appointment_time': 0.5, 'tool_time': 0.2},
            'restaurant': {'email_time': 0.15, 'appointment_time': 0.3, 'tool_time': 0.25},
            'medical_practice': {'email_time': 0.2, 'appointment_time': 0.4, 'tool_time': 0.3},
            'real_estate': {'email_time': 0.12, 'appointment_time': 0.6, 'tool_time': 0.35},
            'tax_services': {'email_time': 0.18, 'appointment_time': 0.8, 'tool_time': 0.4}
        }
        
        rates = industry_rates.get(industry, industry_rates['landscaping'])
        return (emails * rates['email_time'] + 
                appointments * rates['appointment_time'] + 
                tool_calls * rates['tool_time'])
    
    def _calculate_revenue_impact(self, industry: str, leads: int, appointments: int) -> float:
        """Calculate revenue impact based on industry conversion rates"""
        industry_conversion = {
            'landscaping': {'lead_value': 500, 'appointment_value': 200},
            'restaurant': {'lead_value': 100, 'appointment_value': 150},
            'medical_practice': {'lead_value': 300, 'appointment_value': 250},
            'real_estate': {'lead_value': 2000, 'appointment_value': 500},
            'tax_services': {'lead_value': 400, 'appointment_value': 300}
        }
        
        conversion = industry_conversion.get(industry, industry_conversion['landscaping'])
        return (leads * conversion['lead_value'] + 
                appointments * conversion['appointment_value'])
    
    def _get_monthly_cost(self, industry: str) -> float:
        """Get monthly cost based on industry tier"""
        tier_costs = {
            'landscaping': 99,  # Professional
            'restaurant': 249,  # Premium
            'medical_practice': 499,  # Enterprise
            'real_estate': 499,  # Enterprise
            'tax_services': 499  # Enterprise
        }
        return tier_costs.get(industry, 99)
    
    def _generate_industry_metrics(self, industry: str, usage_data: Dict[str, Any]) -> List[ClientMetric]:
        """Generate industry-specific metrics"""
        benchmarks = self.industry_benchmarks.get(industry, {})
        
        metrics = []
        
        if industry == 'landscaping':
            metrics.extend([
                ClientMetric(
                    metric_name="Weather-Based Reschedules",
                    value=usage_data.get('weather_reschedules', 0),
                    unit="times",
                    improvement=15.0,
                    industry_benchmark=benchmarks.get('avg_weather_reschedules', 5),
                    description="Automatic rescheduling based on weather conditions"
                ),
                ClientMetric(
                    metric_name="Estimate Conversion Rate",
                    value=usage_data.get('estimate_conversion', 0.75),
                    unit="percentage",
                    improvement=25.0,
                    industry_benchmark=benchmarks.get('avg_conversion', 0.50),
                    description="Percentage of estimates that convert to projects"
                )
            ])
        
        elif industry == 'restaurant':
            metrics.extend([
                ClientMetric(
                    metric_name="Upselling Success Rate",
                    value=usage_data.get('upsell_rate', 0.20),
                    unit="percentage",
                    improvement=30.0,
                    industry_benchmark=benchmarks.get('avg_upsell_rate', 0.15),
                    description="Percentage of orders with successful upsells"
                ),
                ClientMetric(
                    metric_name="Loyalty Program Engagement",
                    value=usage_data.get('loyalty_engagement', 0.60),
                    unit="percentage",
                    improvement=20.0,
                    industry_benchmark=benchmarks.get('avg_loyalty', 0.40),
                    description="Percentage of customers actively using loyalty program"
                )
            ])
        
        elif industry == 'medical_practice':
            metrics.extend([
                ClientMetric(
                    metric_name="No-Show Reduction",
                    value=usage_data.get('no_show_rate', 0.08),
                    unit="percentage",
                    improvement=-40.0,  # Negative because lower is better
                    industry_benchmark=benchmarks.get('avg_no_show_rate', 0.20),
                    description="Reduction in patient no-show rates"
                ),
                ClientMetric(
                    metric_name="HIPAA Compliance Score",
                    value=usage_data.get('compliance_score', 0.98),
                    unit="percentage",
                    improvement=5.0,
                    industry_benchmark=benchmarks.get('avg_compliance', 0.93),
                    description="HIPAA compliance rating for patient communications"
                )
            ])
        
        return metrics
    
    def _calculate_satisfaction_score(self, industry: str, usage_data: Dict[str, Any]) -> float:
        """Calculate customer satisfaction score"""
        base_score = 4.2
        efficiency_bonus = min(usage_data.get('efficiency_gain', 0) / 100, 0.5)
        return min(base_score + efficiency_bonus, 5.0)
    
    def _calculate_retention_rate(self, industry: str, usage_data: Dict[str, Any]) -> float:
        """Calculate customer retention rate"""
        base_rate = 0.75
        automation_bonus = min(usage_data.get('automation_level', 0) / 100, 0.15)
        return min(base_rate + automation_bonus, 0.95)
    
    def _calculate_conversion_rate(self, industry: str, usage_data: Dict[str, Any]) -> float:
        """Calculate conversion rate"""
        benchmarks = self.industry_benchmarks.get(industry, {})
        base_rate = benchmarks.get('avg_lead_conversion', 0.25)
        ai_bonus = min(usage_data.get('ai_interactions', 0) / 1000, 0.10)
        return min(base_rate + ai_bonus, 0.80)
    
    def _generate_recommendations(self, industry: str, usage_data: Dict[str, Any], metrics: List[ClientMetric]) -> List[str]:
        """Generate AI-powered recommendations"""
        try:
            # Check if OpenAI client is available
            if not self.client:
                return [
                    "Increase automation usage to save more time",
                    "Focus on high-value customer interactions", 
                    "Implement additional industry-specific workflows"
                ]
            
            prompt = f"""Based on the following {industry} business data, provide 3 specific, actionable recommendations to improve performance:

Usage Data: {json.dumps(usage_data)}
Metrics: {json.dumps([asdict(m) for m in metrics])}

Provide recommendations that are:
1. Specific and actionable
2. Industry-relevant
3. Focused on growth and efficiency
4. Realistic to implement

Format as a JSON array of strings."""

            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=300,
                temperature=0.7
            )
            
            recommendations = json.loads(response.choices[0].message.content)
            return recommendations if isinstance(recommendations, list) else []
            
        except Exception as e:
            print(f"Error generating recommendations: {e}")
            return [
                "Increase automation usage to save more time",
                "Focus on high-value customer interactions",
                "Implement additional industry-specific workflows"
            ]
    
    def _generate_next_quarter_goals(self, industry: str, usage_data: Dict[str, Any]) -> List[str]:
        """Generate next quarter goals"""
        try:
            # Check if OpenAI client is available
            if not self.client:
                return [
                    "Increase automation usage to save more time",
                    "Focus on high-value customer interactions",
                    "Implement additional industry-specific workflows"
                ]
            
            prompt = f"""Based on current {industry} business performance, suggest 3 specific goals for next quarter:

Current Performance: {json.dumps(usage_data)}

Goals should be:
1. Specific and measurable
2. Industry-appropriate
3. Achievable in 3 months
4. Focused on growth

Format as a JSON array of strings."""

            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=300,
                temperature=0.7
            )
            
            goals = json.loads(response.choices[0].message.content)
            return goals if isinstance(goals, list) else []
            
        except Exception as e:
            print(f"Error generating goals: {e}")
            return [
                "Increase monthly automation usage by 25%",
                "Improve customer satisfaction scores",
                "Expand to additional business processes"
            ]
    
    def format_report_for_client(self, report: ClientReport) -> Dict[str, Any]:
        """Format report for client presentation"""
        return {
            "report_summary": {
                "client_id": report.client_id,
                "industry": report.industry,
                "report_period": report.report_period,
                "generated_at": report.generated_at.isoformat()
            },
            "key_metrics": {
                "emails_handled": report.total_emails_handled,
                "appointments_scheduled": report.total_appointments_scheduled,
                "leads_generated": report.total_leads_generated,
                "revenue_impact": f"${report.total_revenue_impact:,.2f}"
            },
            "efficiency_gains": {
                "hours_saved": f"{report.hours_saved:.1f} hours",
                "staff_efficiency_gain": f"{report.staff_efficiency_gain:.1f}%",
                "customer_satisfaction": f"{report.customer_satisfaction_score:.1f}/5.0",
                "retention_rate": f"{report.retention_rate:.1%}"
            },
            "roi_analysis": {
                "monthly_cost": f"${report.monthly_cost:,.2f}",
                "roi_percentage": f"{report.roi_percentage:.1f}%",
                "payback_period": f"{report.payback_period_days} days"
            },
            "industry_metrics": [asdict(metric) for metric in report.industry_metrics],
            "recommendations": report.recommendations,
            "next_quarter_goals": report.next_quarter_goals
        }

# Global instance
analytics_engine = ClientAnalyticsEngine()
