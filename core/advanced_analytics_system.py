"""
Advanced Analytics System for Fikiri Solutions
Comprehensive email and communication analytics with AI insights
"""

import json
import logging
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
import statistics
from core.minimal_config import get_config

logger = logging.getLogger(__name__)

@dataclass
class AnalyticsMetric:
    """Analytics metric data structure"""
    metric_name: str
    value: float
    unit: str
    timestamp: datetime
    category: str
    metadata: Dict[str, Any]

@dataclass
class PerformanceInsight:
    """Performance insight data structure"""
    insight_type: str
    title: str
    description: str
    impact: str  # low, medium, high
    recommendation: str
    confidence: float
    category: str

class AdvancedAnalyticsSystem:
    """Advanced analytics with AI-powered insights"""
    
    def __init__(self):
        self.metrics_history = []
        self.insights_cache = {}
        
        # Analytics categories
        self.categories = {
            "email_performance": ["response_time", "open_rate", "click_rate", "reply_rate"],
            "customer_satisfaction": ["sentiment_score", "complaint_rate", "praise_rate", "nps_score"],
            "business_metrics": ["lead_conversion", "revenue_impact", "cost_per_lead", "roi"],
            "operational": ["email_volume", "automation_rate", "error_rate", "uptime"]
        }
        
        # Performance benchmarks
        self.benchmarks = {
            "email_performance": {
                "response_time": {"excellent": 2, "good": 4, "average": 8, "poor": 12},
                "open_rate": {"excellent": 0.25, "good": 0.20, "average": 0.15, "poor": 0.10},
                "click_rate": {"excellent": 0.05, "good": 0.03, "average": 0.02, "poor": 0.01},
                "reply_rate": {"excellent": 0.10, "good": 0.07, "average": 0.05, "poor": 0.03}
            },
            "customer_satisfaction": {
                "sentiment_score": {"excellent": 0.8, "good": 0.6, "average": 0.4, "poor": 0.2},
                "complaint_rate": {"excellent": 0.02, "good": 0.05, "average": 0.10, "poor": 0.20},
                "nps_score": {"excellent": 50, "good": 30, "average": 10, "poor": -10}
            }
        }
    
    def track_metric(self, metric_name: str, value: float, unit: str, 
                    category: str, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """Track a new metric"""
        try:
            metric = AnalyticsMetric(
                metric_name=metric_name,
                value=value,
                unit=unit,
                timestamp=datetime.now(),
                category=category,
                metadata=metadata or {}
            )
            
            self.metrics_history.append(metric)
            
            logger.info(f"✅ Metric tracked: {metric_name} = {value} {unit}")
            
            return {
                "success": True,
                "metric_id": f"{metric_name}_{int(metric.timestamp.timestamp())}",
                "timestamp": metric.timestamp.isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to track metric: {e}")
            return {"success": False, "error": str(e)}
    
    def get_metrics_summary(self, category: str = None, days: int = 30) -> Dict[str, Any]:
        """Get metrics summary for specified period"""
        try:
            # Filter metrics by category and time
            cutoff_date = datetime.now() - timedelta(days=days)
            filtered_metrics = [
                m for m in self.metrics_history
                if m.timestamp >= cutoff_date and (category is None or m.category == category)
            ]
            
            if not filtered_metrics:
                return {"error": "No metrics found for the specified period"}
            
            # Group by metric name
            metrics_by_name = {}
            for metric in filtered_metrics:
                if metric.metric_name not in metrics_by_name:
                    metrics_by_name[metric.metric_name] = []
                metrics_by_name[metric.metric_name].append(metric)
            
            # Calculate summary statistics
            summary = {}
            for metric_name, metrics in metrics_by_name.items():
                values = [m.value for m in metrics]
                
                summary[metric_name] = {
                    "count": len(values),
                    "average": statistics.mean(values),
                    "median": statistics.median(values),
                    "min": min(values),
                    "max": max(values),
                    "std_dev": statistics.stdev(values) if len(values) > 1 else 0,
                    "latest_value": values[-1],
                    "trend": self._calculate_trend(values),
                    "unit": metrics[0].unit,
                    "category": metrics[0].category
                }
            
            return {
                "period_days": days,
                "total_metrics": len(filtered_metrics),
                "metrics_summary": summary,
                "generated_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to get metrics summary: {e}")
            return {"error": "Summary generation failed"}
    
    def _calculate_trend(self, values: List[float]) -> str:
        """Calculate trend direction"""
        if len(values) < 2:
            return "stable"
        
        # Simple linear trend calculation
        recent_avg = statistics.mean(values[-3:]) if len(values) >= 3 else values[-1]
        older_avg = statistics.mean(values[:-3]) if len(values) >= 6 else values[0]
        
        if recent_avg > older_avg * 1.05:
            return "increasing"
        elif recent_avg < older_avg * 0.95:
            return "decreasing"
        else:
            return "stable"
    
    def generate_performance_insights(self, user_id: int, days: int = 30) -> List[PerformanceInsight]:
        """Generate AI-powered performance insights"""
        try:
            insights = []
            
            # Get recent metrics
            metrics_summary = self.get_metrics_summary(days=days)
            
            if "error" in metrics_summary:
                return insights
            
            # Analyze email performance
            email_insights = self._analyze_email_performance(metrics_summary)
            insights.extend(email_insights)
            
            # Analyze customer satisfaction
            satisfaction_insights = self._analyze_customer_satisfaction(metrics_summary)
            insights.extend(satisfaction_insights)
            
            # Analyze business metrics
            business_insights = self._analyze_business_metrics(metrics_summary)
            insights.extend(business_insights)
            
            # Analyze operational metrics
            operational_insights = self._analyze_operational_metrics(metrics_summary)
            insights.extend(operational_insights)
            
            # Cache insights
            self.insights_cache[user_id] = {
                "insights": insights,
                "generated_at": datetime.now(),
                "period_days": days
            }
            
            return insights
            
        except Exception as e:
            logger.error(f"❌ Failed to generate insights: {e}")
            return []
    
    def _analyze_email_performance(self, metrics_summary: Dict[str, Any]) -> List[PerformanceInsight]:
        """Analyze email performance metrics"""
        insights = []
        metrics = metrics_summary.get("metrics_summary", {})
        
        # Response time analysis
        if "response_time" in metrics:
            response_time = metrics["response_time"]["average"]
            benchmark = self.benchmarks["email_performance"]["response_time"]
            
            if response_time <= benchmark["excellent"]:
                insights.append(PerformanceInsight(
                    insight_type="performance",
                    title="Excellent Response Time",
                    description=f"Your average response time of {response_time:.1f} hours is excellent.",
                    impact="high",
                    recommendation="Maintain this level of responsiveness to keep customers satisfied.",
                    confidence=0.9,
                    category="email_performance"
                ))
            elif response_time > benchmark["poor"]:
                insights.append(PerformanceInsight(
                    insight_type="performance",
                    title="Slow Response Time",
                    description=f"Your average response time of {response_time:.1f} hours is above industry standards.",
                    impact="high",
                    recommendation="Consider implementing automated responses and faster response protocols.",
                    confidence=0.8,
                    category="email_performance"
                ))
        
        # Open rate analysis
        if "open_rate" in metrics:
            open_rate = metrics["open_rate"]["average"]
            benchmark = self.benchmarks["email_performance"]["open_rate"]
            
            if open_rate < benchmark["average"]:
                insights.append(PerformanceInsight(
                    insight_type="engagement",
                    title="Low Email Open Rate",
                    description=f"Your open rate of {open_rate:.1%} is below average.",
                    impact="medium",
                    recommendation="Improve subject lines and send times to increase open rates.",
                    confidence=0.7,
                    category="email_performance"
                ))
        
        return insights
    
    def _analyze_customer_satisfaction(self, metrics_summary: Dict[str, Any]) -> List[PerformanceInsight]:
        """Analyze customer satisfaction metrics"""
        insights = []
        metrics = metrics_summary.get("metrics_summary", {})
        
        # Sentiment analysis
        if "sentiment_score" in metrics:
            sentiment_score = metrics["sentiment_score"]["average"]
            benchmark = self.benchmarks["customer_satisfaction"]["sentiment_score"]
            
            if sentiment_score < benchmark["average"]:
                insights.append(PerformanceInsight(
                    insight_type="satisfaction",
                    title="Customer Sentiment Concerns",
                    description=f"Customer sentiment score of {sentiment_score:.2f} indicates room for improvement.",
                    impact="high",
                    recommendation="Review communication tone and response quality to improve customer satisfaction.",
                    confidence=0.8,
                    category="customer_satisfaction"
                ))
        
        # Complaint rate analysis
        if "complaint_rate" in metrics:
            complaint_rate = metrics["complaint_rate"]["average"]
            benchmark = self.benchmarks["customer_satisfaction"]["complaint_rate"]
            
            if complaint_rate > benchmark["average"]:
                insights.append(PerformanceInsight(
                    insight_type="satisfaction",
                    title="High Complaint Rate",
                    description=f"Complaint rate of {complaint_rate:.1%} is above industry average.",
                    impact="high",
                    recommendation="Implement proactive customer service measures and quality control processes.",
                    confidence=0.9,
                    category="customer_satisfaction"
                ))
        
        return insights
    
    def _analyze_business_metrics(self, metrics_summary: Dict[str, Any]) -> List[PerformanceInsight]:
        """Analyze business metrics"""
        insights = []
        metrics = metrics_summary.get("metrics_summary", {})
        
        # Lead conversion analysis
        if "lead_conversion" in metrics:
            conversion_rate = metrics["lead_conversion"]["average"]
            
            if conversion_rate < 0.05:  # 5% threshold
                insights.append(PerformanceInsight(
                    insight_type="business",
                    title="Low Lead Conversion",
                    description=f"Lead conversion rate of {conversion_rate:.1%} is below optimal levels.",
                    impact="high",
                    recommendation="Review lead qualification process and follow-up strategies.",
                    confidence=0.8,
                    category="business_metrics"
                ))
        
        # ROI analysis
        if "roi" in metrics:
            roi = metrics["roi"]["average"]
            
            if roi < 2.0:  # 2x ROI threshold
                insights.append(PerformanceInsight(
                    insight_type="business",
                    title="ROI Improvement Opportunity",
                    description=f"Current ROI of {roi:.1f}x could be improved.",
                    impact="medium",
                    recommendation="Optimize automation processes and reduce operational costs.",
                    confidence=0.7,
                    category="business_metrics"
                ))
        
        return insights
    
    def _analyze_operational_metrics(self, metrics_summary: Dict[str, Any]) -> List[PerformanceInsight]:
        """Analyze operational metrics"""
        insights = []
        metrics = metrics_summary.get("metrics_summary", {})
        
        # Automation rate analysis
        if "automation_rate" in metrics:
            automation_rate = metrics["automation_rate"]["average"]
            
            if automation_rate < 0.7:  # 70% threshold
                insights.append(PerformanceInsight(
                    insight_type="operational",
                    title="Automation Opportunity",
                    description=f"Automation rate of {automation_rate:.1%} could be increased.",
                    impact="medium",
                    recommendation="Implement more automated workflows to improve efficiency.",
                    confidence=0.8,
                    category="operational"
                ))
        
        # Error rate analysis
        if "error_rate" in metrics:
            error_rate = metrics["error_rate"]["average"]
            
            if error_rate > 0.05:  # 5% threshold
                insights.append(PerformanceInsight(
                    insight_type="operational",
                    title="High Error Rate",
                    description=f"Error rate of {error_rate:.1%} needs attention.",
                    impact="high",
                    recommendation="Review processes and implement quality control measures.",
                    confidence=0.9,
                    category="operational"
                ))
        
        return insights
    
    def get_performance_dashboard(self, user_id: int, days: int = 30) -> Dict[str, Any]:
        """Get comprehensive performance dashboard"""
        try:
            # Get metrics summary
            metrics_summary = self.get_metrics_summary(days=days)
            
            # Generate insights
            insights = self.generate_performance_insights(user_id, days)
            
            # Calculate overall performance score
            performance_score = self._calculate_performance_score(metrics_summary)
            
            # Get trend analysis
            trend_analysis = self._analyze_trends(metrics_summary)
            
            return {
                "user_id": user_id,
                "period_days": days,
                "performance_score": performance_score,
                "metrics_summary": metrics_summary,
                "insights": [
                    {
                        "type": insight.insight_type,
                        "title": insight.title,
                        "description": insight.description,
                        "impact": insight.impact,
                        "recommendation": insight.recommendation,
                        "confidence": insight.confidence,
                        "category": insight.category
                    }
                    for insight in insights
                ],
                "trend_analysis": trend_analysis,
                "generated_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to generate dashboard: {e}")
            return {"error": "Dashboard generation failed"}
    
    def _calculate_performance_score(self, metrics_summary: Dict[str, Any]) -> float:
        """Calculate overall performance score"""
        try:
            metrics = metrics_summary.get("metrics_summary", {})
            scores = []
            
            # Email performance score
            if "response_time" in metrics:
                response_time = metrics["response_time"]["average"]
                if response_time <= 2:
                    scores.append(100)
                elif response_time <= 4:
                    scores.append(80)
                elif response_time <= 8:
                    scores.append(60)
                else:
                    scores.append(40)
            
            # Customer satisfaction score
            if "sentiment_score" in metrics:
                sentiment_score = metrics["sentiment_score"]["average"]
                scores.append(sentiment_score * 100)
            
            # Business metrics score
            if "roi" in metrics:
                roi = metrics["roi"]["average"]
                if roi >= 3:
                    scores.append(100)
                elif roi >= 2:
                    scores.append(80)
                elif roi >= 1.5:
                    scores.append(60)
                else:
                    scores.append(40)
            
            return statistics.mean(scores) if scores else 0.0
            
        except Exception as e:
            logger.error(f"❌ Failed to calculate performance score: {e}")
            return 0.0
    
    def _analyze_trends(self, metrics_summary: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze trends across metrics"""
        try:
            metrics = metrics_summary.get("metrics_summary", {})
            trends = {}
            
            for metric_name, metric_data in metrics.items():
                trend = metric_data.get("trend", "stable")
                trends[metric_name] = {
                    "direction": trend,
                    "latest_value": metric_data.get("latest_value", 0),
                    "average": metric_data.get("average", 0)
                }
            
            return trends
            
        except Exception as e:
            logger.error(f"❌ Failed to analyze trends: {e}")
            return {}
    
    def export_analytics_data(self, user_id: int, format: str = "json", days: int = 30) -> Dict[str, Any]:
        """Export analytics data in specified format"""
        try:
            # Get dashboard data
            dashboard_data = self.get_performance_dashboard(user_id, days)
            
            if format == "json":
                return {
                    "success": True,
                    "format": "json",
                    "data": dashboard_data
                }
            elif format == "csv":
                # Convert to CSV format
                csv_data = self._convert_to_csv(dashboard_data)
                return {
                    "success": True,
                    "format": "csv",
                    "data": csv_data
                }
            else:
                return {"success": False, "error": "Unsupported format"}
                
        except Exception as e:
            logger.error(f"❌ Failed to export analytics: {e}")
            return {"success": False, "error": str(e)}
    
    def _convert_to_csv(self, dashboard_data: Dict[str, Any]) -> str:
        """Convert dashboard data to CSV format"""
        try:
            csv_lines = []
            
            # Add header
            csv_lines.append("Metric,Value,Category,Trend,Impact")
            
            # Add metrics data
            metrics_summary = dashboard_data.get("metrics_summary", {}).get("metrics_summary", {})
            for metric_name, metric_data in metrics_summary.items():
                csv_lines.append(f"{metric_name},{metric_data.get('average', 0)},{metric_data.get('category', '')},{metric_data.get('trend', 'stable')},medium")
            
            return "\n".join(csv_lines)
            
        except Exception as e:
            logger.error(f"❌ Failed to convert to CSV: {e}")
            return ""

# Global instance
analytics_system = None

def get_analytics_system() -> Optional[AdvancedAnalyticsSystem]:
    """Get the global analytics system instance"""
    global analytics_system
    
    if analytics_system is None:
        analytics_system = AdvancedAnalyticsSystem()
    
    return analytics_system
