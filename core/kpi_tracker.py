#!/usr/bin/env python3
"""
KPI Tracking System
Calculates and tracks key performance indicators for early-stage and mid-stage companies
"""

import json
import logging
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum

from core.database_optimization import db_optimizer
from core.trace_context import get_trace_id

logger = logging.getLogger(__name__)

class CompanyStage(Enum):
    """Company growth stage"""
    EARLY_STAGE = "early_stage"
    MID_STAGE = "mid_stage"

@dataclass
class EarlyStageKPIs:
    """Early-stage company KPIs"""
    cac: Optional[float]  # Customer Acquisition Cost (None if insufficient data)
    clv: Optional[float]  # Customer Lifetime Value (None if insufficient data)
    burn_rate: Optional[float]  # Monthly burn rate (None if insufficient data)
    gross_margin: Optional[float]  # Gross margin percentage (None if insufficient data)
    cac_payback_period: Optional[float]  # Months to recover CAC (None if insufficient data)
    clv_cac_ratio: Optional[float]  # CLV:CAC ratio (None if insufficient data)
    data_quality: Dict[str, str]  # Indicates which KPIs use real vs estimated data

@dataclass
class MidStageKPIs:
    """Mid-stage company KPIs"""
    retention_rate: Optional[float]  # Customer retention rate (None if insufficient data)
    arpu: Optional[float]  # Average Revenue Per User (None if insufficient data)
    sales_efficiency: Optional[float]  # Sales efficiency ratio (None if insufficient data)
    net_revenue_retention: Optional[float]  # Net Revenue Retention % (None if insufficient data)
    churn_rate: Optional[float]  # Customer churn rate (None if insufficient data)
    expansion_revenue: Optional[float]  # Revenue from upsells/expansion (None if insufficient data)
    data_quality: Dict[str, str]  # Indicates which KPIs use real vs estimated data

class KPITracker:
    """Tracks and calculates business KPIs"""
    
    def __init__(self):
        logger.info("📊 KPI tracker initialized")
    
    def calculate_cac(
        self,
        period_days: int = 30,
        include_marketing: bool = True,
        include_sales: bool = True,
        require_actual_costs: bool = True
    ) -> Optional[float]:
        """
        Calculate Customer Acquisition Cost (CAC)
        
        CAC = (Total Sales & Marketing Costs) / (New Customers Acquired)
        
        Args:
            period_days: Period to calculate CAC for
            include_marketing: Include marketing costs
            include_sales: Include sales costs
            require_actual_costs: If True, return None when only estimated costs available
        
        Returns:
            CAC value, or None if insufficient actual data and require_actual_costs=True
        """
        try:
            start_date = datetime.now() - timedelta(days=period_days)
            
            # Get new customers in period
            new_customers = db_optimizer.execute_query(
                """SELECT COUNT(*) as count FROM users 
                   WHERE created_at >= ? AND is_active = 1""",
                (start_date.isoformat(),)
            )
            customer_count = new_customers[0]['count'] if new_customers else 0
            
            if customer_count == 0:
                if require_actual_costs:
                    return None
                return 0.0
            
            # Get total marketing/sales costs (will use actual if available)
            total_costs = self._estimate_acquisition_costs(
                period_days, 
                include_marketing, 
                include_sales,
                require_actual_costs=require_actual_costs
            )
            
            if total_costs is None or total_costs == 0:
                if require_actual_costs:
                    return None
                return 0.0
            
            cac = total_costs / customer_count if customer_count > 0 else 0.0
            
            logger.info(f"📊 Calculated CAC: ${cac:.2f} (period: {period_days} days, customers: {customer_count})")
            
            return round(cac, 2)
            
        except Exception as e:
            logger.error(f"Failed to calculate CAC: {e}")
            return None
    
    def calculate_clv(
        self,
        average_revenue_per_customer: Optional[float] = None,
        average_customer_lifespan_months: Optional[float] = None,
        gross_margin_percent: Optional[float] = None,
        require_actual_data: bool = True
    ) -> Optional[float]:
        """
        Calculate Customer Lifetime Value (CLV)
        
        CLV = (Average Revenue Per Customer) × (Average Customer Lifespan) × (Gross Margin %)
        
        Args:
            average_revenue_per_customer: Average monthly revenue per customer (if None, calculated)
            average_customer_lifespan_months: Average customer lifespan in months (if None, estimated)
            gross_margin_percent: Gross margin percentage (if None, calculated)
            require_actual_data: If True, return None when revenue data is insufficient
        
        Returns:
            CLV value, or None if insufficient data and require_actual_data=True
        """
        try:
            # Check if we have revenue data
            if require_actual_data and not self._has_revenue_data():
                logger.warning("⚠️ Insufficient revenue data for CLV calculation. Returning None.")
                return None
            
            # Calculate average revenue per customer if not provided
            if average_revenue_per_customer is None:
                average_revenue_per_customer = self._calculate_average_revenue_per_customer()
                if average_revenue_per_customer == 0:
                    if require_actual_data:
                        return None
                    # Use default estimate
                    average_revenue_per_customer = 50.0  # Default estimate
            
            # Estimate customer lifespan if not provided (based on churn rate)
            if average_customer_lifespan_months is None:
                churn_rate = self.calculate_churn_rate()
                if churn_rate > 0:
                    average_customer_lifespan_months = 1 / (churn_rate / 100)  # Inverse of monthly churn rate
                else:
                    if require_actual_data and not self._has_subscription_data():
                        return None
                    average_customer_lifespan_months = 24  # Default 24 months
            
            # Calculate gross margin if not provided
            if gross_margin_percent is None:
                gross_margin_percent = self.calculate_gross_margin(require_actual_data=require_actual_data)
                if gross_margin_percent is None:
                    if require_actual_data:
                        return None
                    gross_margin_percent = 80.0  # Default estimate
            
            if average_revenue_per_customer == 0 or average_customer_lifespan_months == 0:
                return None
            
            clv = (
                average_revenue_per_customer *
                average_customer_lifespan_months *
                (gross_margin_percent / 100)
            )
            
            logger.info(f"📊 Calculated CLV: ${clv:.2f}")
            
            return round(clv, 2)
            
        except Exception as e:
            logger.error(f"Failed to calculate CLV: {e}")
            return None
    
    def calculate_burn_rate(
        self,
        period_days: int = 30,
        include_all_costs: bool = True,
        require_actual_data: bool = True
    ) -> Optional[float]:
        """
        Calculate Monthly Burn Rate
        
        Burn Rate = Total Monthly Operating Expenses
        
        Args:
            period_days: Period to calculate burn rate for
            include_all_costs: Include all operating costs
            require_actual_data: If True, return None when cost data is insufficient
        
        Returns:
            Monthly burn rate, or None if insufficient data and require_actual_data=True
        """
        try:
            if require_actual_data:
                # Check if we have actual cost data
                start_date = datetime.now() - timedelta(days=period_days)
                cost_check = db_optimizer.execute_query(
                    "SELECT COUNT(*) as count FROM acquisition_costs WHERE cost_date >= ?",
                    (start_date.isoformat(),)
                )
                has_costs = cost_check and cost_check[0].get('count', 0) > 0
                
                if not has_costs:
                    logger.warning("⚠️ No actual cost data recorded. Cannot calculate accurate burn rate. Returning None.")
                    return None
            
            # Calculate total expenses for the period
            # Note: In production, this would come from accounting system
            # For now, estimate based on infrastructure and operational costs
            
            # Get infrastructure costs (simplified)
            infrastructure_costs = self._estimate_infrastructure_costs(period_days)
            
            # Get personnel costs (simplified - would need payroll data)
            personnel_costs = self._estimate_personnel_costs(period_days)
            
            # Get marketing/sales costs (will use actual if available)
            marketing_costs = self._estimate_acquisition_costs(period_days, include_marketing=True, include_sales=False, require_actual_costs=False) or 0
            sales_costs = self._estimate_acquisition_costs(period_days, include_marketing=False, include_sales=True, require_actual_costs=False) or 0
            
            total_costs = infrastructure_costs + personnel_costs + marketing_costs + sales_costs
            
            if total_costs == 0:
                return None
            
            # Convert to monthly burn rate
            days_in_month = 30
            monthly_burn_rate = (total_costs / period_days) * days_in_month
            
            logger.info(f"📊 Calculated burn rate: ${monthly_burn_rate:.2f}/month")
            
            return round(monthly_burn_rate, 2)
            
        except Exception as e:
            logger.error(f"Failed to calculate burn rate: {e}")
            return None
    
    def calculate_gross_margin(
        self,
        period_days: int = 30,
        require_actual_data: bool = True
    ) -> Optional[float]:
        """
        Calculate Gross Margin
        
        Gross Margin % = ((Revenue - COGS) / Revenue) × 100
        
        Args:
            period_days: Period to calculate gross margin for
            require_actual_data: If True, return None when revenue data is insufficient
        
        Returns:
            Gross margin percentage, or None if insufficient data and require_actual_data=True
        """
        try:
            start_date = datetime.now() - timedelta(days=period_days)
            
            # Check if we have revenue data
            if require_actual_data and not self._has_revenue_data():
                logger.warning("⚠️ Insufficient revenue data for gross margin calculation. Returning None.")
                return None
            
            # Calculate total revenue
            revenue = self._calculate_total_revenue(start_date)
            
            if revenue == 0:
                if require_actual_data:
                    return None
                return 0.0
            
            # Calculate COGS (Cost of Goods Sold)
            # For SaaS: COGS typically includes hosting, support, payment processing
            # NOTE: Currently uses 20% estimate - in production, use actual COGS
            cogs = self._calculate_cogs(start_date)
            
            gross_margin = ((revenue - cogs) / revenue) * 100
            
            logger.info(f"📊 Calculated gross margin: {gross_margin:.2f}%")
            
            return round(gross_margin, 2)
            
        except Exception as e:
            logger.error(f"Failed to calculate gross margin: {e}")
            return None
    
    def calculate_retention_rate(
        self,
        period_days: int = 30,
        require_actual_data: bool = True
    ) -> Optional[float]:
        """
        Calculate Customer Retention Rate
        
        Retention Rate = ((Customers at End - New Customers) / Customers at Start) × 100
        
        Args:
            period_days: Period to calculate retention for
            require_actual_data: If True, return None when customer data is insufficient
        
        Returns:
            Retention rate percentage, or None if insufficient data and require_actual_data=True
        """
        try:
            # Check if we have customer data
            if require_actual_data and not self._has_customer_data():
                logger.warning("⚠️ Insufficient customer data for retention rate calculation. Returning None.")
                return None
            
            start_date = datetime.now() - timedelta(days=period_days)
            end_date = datetime.now()
            
            # Get customers at start of period
            customers_at_start = db_optimizer.execute_query(
                """SELECT COUNT(*) as count FROM users 
                   WHERE created_at < ? AND is_active = 1""",
                (start_date.isoformat(),)
            )
            start_count = customers_at_start[0]['count'] if customers_at_start else 0
            
            # Get new customers during period
            new_customers = db_optimizer.execute_query(
                """SELECT COUNT(*) as count FROM users 
                   WHERE created_at >= ? AND created_at < ? AND is_active = 1""",
                (start_date.isoformat(), end_date.isoformat())
            )
            new_count = new_customers[0]['count'] if new_customers else 0
            
            # Get active customers at end (who were customers at start)
            customers_at_end = db_optimizer.execute_query(
                """SELECT COUNT(*) as count FROM users 
                   WHERE created_at < ? AND is_active = 1""",
                (end_date.isoformat(),)
            )
            end_count = customers_at_end[0]['count'] if customers_at_end else 0
            
            if start_count == 0:
                if require_actual_data:
                    return None
                return 100.0  # No customers to retain
            
            retention_rate = ((end_count - new_count) / start_count) * 100
            
            logger.info(f"📊 Calculated retention rate: {retention_rate:.2f}%")
            
            return round(retention_rate, 2)
            
        except Exception as e:
            logger.error(f"Failed to calculate retention rate: {e}")
            return 0.0
    
    def calculate_arpu(
        self,
        period_days: int = 30,
        require_actual_data: bool = True
    ) -> Optional[float]:
        """
        Calculate Average Revenue Per User (ARPU)
        
        ARPU = Total Revenue / Number of Active Customers
        
        Args:
            period_days: Period to calculate ARPU for
            require_actual_data: If True, return None when revenue data is insufficient
        
        Returns:
            ARPU value, or None if insufficient data and require_actual_data=True
        """
        try:
            start_date = datetime.now() - timedelta(days=period_days)
            
            # Check if we have revenue data
            if require_actual_data and not self._has_revenue_data():
                logger.warning("⚠️ Insufficient revenue data for ARPU calculation. Returning None.")
                return None
            
            # Calculate total revenue
            revenue = self._calculate_total_revenue(start_date)
            
            # Get active customers (with active subscriptions)
            active_customers = db_optimizer.execute_query(
                """SELECT COUNT(DISTINCT user_id) as count FROM subscriptions 
                   WHERE status IN ('active', 'trialing') AND updated_at >= ?""",
                (start_date.isoformat(),)
            )
            customer_count = active_customers[0]['count'] if active_customers else 0
            
            if customer_count == 0:
                if require_actual_data:
                    return None
                return 0.0
            
            if revenue == 0:
                if require_actual_data:
                    return None
                return 0.0
            
            arpu = revenue / customer_count
            
            logger.info(f"📊 Calculated ARPU: ${arpu:.2f}")
            
            return round(arpu, 2)
            
        except Exception as e:
            logger.error(f"Failed to calculate ARPU: {e}")
            return None
    
    def calculate_sales_efficiency(
        self,
        period_days: int = 30,
        require_actual_data: bool = True
    ) -> Optional[float]:
        """
        Calculate Sales Efficiency
        
        Sales Efficiency = New Revenue / (Sales + Marketing Costs)
        
        Args:
            period_days: Period to calculate sales efficiency for
            require_actual_data: If True, return None when cost/revenue data is insufficient
        
        Returns:
            Sales efficiency ratio, or None if insufficient data and require_actual_data=True
        """
        try:
            start_date = datetime.now() - timedelta(days=period_days)
            
            # Check if we have revenue data
            if require_actual_data and not self._has_revenue_data():
                logger.warning("⚠️ Insufficient revenue data for sales efficiency calculation. Returning None.")
                return None
            
            # Calculate new revenue from new customers
            new_revenue = self._calculate_new_customer_revenue(start_date)
            
            # Calculate sales & marketing costs (will use actual if available)
            sales_marketing_costs = self._estimate_acquisition_costs(
                period_days,
                include_marketing=True,
                include_sales=True,
                require_actual_costs=require_actual_data
            )
            
            if sales_marketing_costs is None or sales_marketing_costs == 0:
                if require_actual_data:
                    return None
                return 0.0
            
            if new_revenue == 0:
                if require_actual_data:
                    return None
                return 0.0
            
            sales_efficiency = new_revenue / sales_marketing_costs
            
            logger.info(f"📊 Calculated sales efficiency: {sales_efficiency:.2f}")
            
            return round(sales_efficiency, 2)
            
        except Exception as e:
            logger.error(f"Failed to calculate sales efficiency: {e}")
            return None
    
    def calculate_net_revenue_retention(
        self,
        period_days: int = 30,
        require_actual_data: bool = True
    ) -> Optional[float]:
        """
        Calculate Net Revenue Retention (NRR)
        
        NRR = ((Starting Revenue + Expansion Revenue - Churned Revenue) / Starting Revenue) × 100
        
        Args:
            period_days: Period to calculate NRR for
            require_actual_data: If True, return None when revenue data is insufficient
        
        Returns:
            Net Revenue Retention percentage, or None if insufficient data and require_actual_data=True
        """
        try:
            start_date = datetime.now() - timedelta(days=period_days)
            
            # Check if we have revenue data
            if require_actual_data and not self._has_revenue_data():
                logger.warning("⚠️ Insufficient revenue data for NRR calculation. Returning None.")
                return None
            
            # Get starting revenue (revenue from customers at start of period)
            starting_revenue = self._calculate_starting_revenue(start_date)
            
            if starting_revenue == 0:
                if require_actual_data:
                    return None
                return 0.0
            
            # Calculate expansion revenue (upsells, upgrades)
            expansion_revenue = self._calculate_expansion_revenue(start_date)
            
            # Calculate churned revenue (from canceled subscriptions)
            churned_revenue = self._calculate_churned_revenue(start_date)
            
            nrr = ((starting_revenue + expansion_revenue - churned_revenue) / starting_revenue) * 100
            
            logger.info(f"📊 Calculated NRR: {nrr:.2f}%")
            
            return round(nrr, 2)
            
        except Exception as e:
            logger.error(f"Failed to calculate NRR: {e}")
            return None
    
    def calculate_churn_rate(
        self,
        period_days: int = 30,
        require_actual_data: bool = True
    ) -> Optional[float]:
        """
        Calculate Customer Churn Rate
        
        Churn Rate = (Customers Lost / Customers at Start) × 100
        
        Args:
            period_days: Period to calculate churn for
        
        Returns:
            Churn rate percentage
        """
        try:
            start_date = datetime.now() - timedelta(days=period_days)
            
            # Get customers at start
            customers_at_start = db_optimizer.execute_query(
                """SELECT COUNT(*) as count FROM subscriptions 
                   WHERE status IN ('active', 'trialing') AND updated_at < ?""",
                (start_date.isoformat(),)
            )
            start_count = customers_at_start[0]['count'] if customers_at_start else 0
            
            # Get churned customers (canceled subscriptions)
            churned_customers = db_optimizer.execute_query(
                """SELECT COUNT(*) as count FROM subscriptions 
                   WHERE status = 'canceled' AND updated_at >= ? AND updated_at < datetime('now')""",
                (start_date.isoformat(),)
            )
            churned_count = churned_customers[0]['count'] if churned_customers else 0
            
            if start_count == 0:
                return 0.0
            
            churn_rate = (churned_count / start_count) * 100
            
            logger.info(f"📊 Calculated churn rate: {churn_rate:.2f}%")
            
            return round(churn_rate, 2)
            
        except Exception as e:
            logger.error(f"Failed to calculate churn rate: {e}")
            return 0.0
    
    def get_early_stage_kpis(self, period_days: int = 30, require_actual_data: bool = True) -> EarlyStageKPIs:
        """
        Get all early-stage KPIs
        
        Args:
            period_days: Period to calculate KPIs for
            require_actual_data: If True, return None for KPIs without actual data (no estimates)
        
        Returns:
            EarlyStageKPIs with data quality indicators
        """
        data_quality = {}
        
        # Calculate CAC (requires actual costs if require_actual_data=True)
        cac = self.calculate_cac(
            period_days, 
            include_marketing=True,
            include_sales=True,
            require_actual_costs=require_actual_data
        )
        data_quality['cac'] = 'actual' if cac is not None else 'insufficient_data'
        
        # Calculate CLV (requires revenue data)
        clv = self.calculate_clv(require_actual_data=require_actual_data)
        data_quality['clv'] = 'actual' if clv is not None else 'insufficient_data'
        
        # Calculate burn rate (requires cost data)
        burn_rate = self.calculate_burn_rate(period_days, require_actual_data=require_actual_data)
        data_quality['burn_rate'] = 'actual' if burn_rate is not None else 'insufficient_data'
        
        # Calculate gross margin (requires revenue data)
        gross_margin = self.calculate_gross_margin(period_days, require_actual_data=require_actual_data)
        data_quality['gross_margin'] = 'actual' if gross_margin is not None else 'insufficient_data'
        
        # Calculate derived metrics (only if base metrics available)
        cac_payback_period = None
        clv_cac_ratio = None
        
        if cac is not None and gross_margin is not None and clv is not None:
            avg_monthly_revenue = self._calculate_average_revenue_per_customer()
            gross_margin_decimal = gross_margin / 100 if gross_margin > 0 else 0
            monthly_profit_per_customer = avg_monthly_revenue * gross_margin_decimal
            if monthly_profit_per_customer > 0:
                cac_payback_period = round(cac / monthly_profit_per_customer, 2)
            if cac > 0:
                clv_cac_ratio = round(clv / cac, 2)
        
        data_quality['cac_payback_period'] = 'calculated' if cac_payback_period is not None else 'insufficient_data'
        data_quality['clv_cac_ratio'] = 'calculated' if clv_cac_ratio is not None else 'insufficient_data'
        
        return EarlyStageKPIs(
            cac=cac,
            clv=clv,
            burn_rate=burn_rate,
            gross_margin=gross_margin,
            cac_payback_period=cac_payback_period,
            clv_cac_ratio=clv_cac_ratio,
            data_quality=data_quality
        )
    
    def get_mid_stage_kpis(self, period_days: int = 30, require_actual_data: bool = True) -> MidStageKPIs:
        """
        Get all mid-stage KPIs
        
        Args:
            period_days: Period to calculate KPIs for
            require_actual_data: If True, return None for KPIs without actual data (no estimates)
        
        Returns:
            MidStageKPIs with data quality indicators
        """
        data_quality = {}
        
        # Calculate retention rate (requires customer data)
        retention_rate = self.calculate_retention_rate(period_days, require_actual_data=require_actual_data)
        data_quality['retention_rate'] = 'actual' if retention_rate is not None else 'insufficient_data'
        
        # Calculate ARPU (requires revenue data)
        arpu = self.calculate_arpu(period_days, require_actual_data=require_actual_data)
        data_quality['arpu'] = 'actual' if arpu is not None else 'insufficient_data'
        
        # Calculate sales efficiency (requires actual costs)
        sales_efficiency = self.calculate_sales_efficiency(period_days, require_actual_data=require_actual_data)
        data_quality['sales_efficiency'] = 'actual' if sales_efficiency is not None else 'insufficient_data'
        
        # Calculate NRR (requires revenue data)
        nrr = self.calculate_net_revenue_retention(period_days, require_actual_data=require_actual_data)
        data_quality['net_revenue_retention'] = 'actual' if nrr is not None else 'insufficient_data'
        
        # Calculate churn rate (requires subscription data)
        churn_rate = self.calculate_churn_rate(period_days, require_actual_data=require_actual_data)
        data_quality['churn_rate'] = 'actual' if churn_rate is not None else 'insufficient_data'
        
        # Calculate expansion revenue (requires revenue data)
        expansion_revenue = None
        if not require_actual_data or self._has_revenue_data():
            expansion_revenue = self._calculate_expansion_revenue(
                datetime.now() - timedelta(days=period_days)
            )
            expansion_revenue = round(expansion_revenue, 2) if expansion_revenue else None
        data_quality['expansion_revenue'] = 'actual' if expansion_revenue is not None else 'insufficient_data'
        
        return MidStageKPIs(
            retention_rate=retention_rate,
            arpu=arpu,
            sales_efficiency=sales_efficiency,
            net_revenue_retention=nrr,
            churn_rate=churn_rate,
            expansion_revenue=expansion_revenue,
            data_quality=data_quality
        )
    
    # Helper methods for calculations
    
    def _calculate_total_revenue(self, start_date: datetime) -> float:
        """
        Calculate total revenue from subscriptions
        
        NOTE: Currently uses hardcoded tier prices from subscriptions table.
        TODO: Integrate with Stripe API or revenue_tracking table for actual revenue data.
        """
        try:
            # Get active subscriptions and calculate revenue
            subscriptions = db_optimizer.execute_query(
                """SELECT tier, billing_period, current_period_start, current_period_end 
                   FROM subscriptions 
                   WHERE status IN ('active', 'trialing') AND updated_at >= ?""",
                (start_date.isoformat(),)
            )
            
            # Tier pricing (hardcoded - TODO: integrate with Stripe API or revenue_tracking table)
            tier_pricing = {
                'starter': {'monthly': 29, 'annual': 290},
                'growth': {'monthly': 99, 'annual': 990},
                'business': {'monthly': 299, 'annual': 2990},
                'enterprise': {'monthly': 999, 'annual': 9990}
            }
            
            total_revenue = 0.0
            
            for sub in subscriptions:
                tier = sub.get('tier', 'starter')
                billing_period = sub.get('billing_period', 'monthly')
                
                if tier in tier_pricing and billing_period in tier_pricing[tier]:
                    # Calculate revenue for this subscription period
                    period_start = sub.get('current_period_start')
                    period_end = sub.get('current_period_end')
                    
                    if period_start and period_end:
                        # Simplified: use tier pricing
                        monthly_price = tier_pricing[tier].get('monthly', 0)
                        if billing_period == 'annual':
                            monthly_price = tier_pricing[tier].get('annual', 0) / 12
                        
                        total_revenue += monthly_price
            
            return total_revenue
            
        except Exception as e:
            logger.error(f"Failed to calculate total revenue: {e}")
            return 0.0
    
    def _calculate_cogs(self, start_date: datetime) -> float:
        """
        Calculate Cost of Goods Sold (for SaaS: hosting, support, payment processing)
        
        NOTE: Currently uses fixed 20% of revenue estimate.
        TODO: Integrate with actual cost tracking for real COGS calculation.
        """
        # Simplified estimation - in production, integrate with finance system
        # Estimate: ~20% of revenue for SaaS COGS
        # TODO: Track actual hosting costs, support costs, payment processing fees
        revenue = self._calculate_total_revenue(start_date)
        return revenue * 0.20
    
    def _calculate_average_revenue_per_customer(self) -> float:
        """Calculate average monthly revenue per customer"""
        try:
            subscriptions = db_optimizer.execute_query(
                """SELECT tier, billing_period FROM subscriptions 
                   WHERE status IN ('active', 'trialing')"""
            )
            
            if not subscriptions:
                return 0.0
            
            tier_pricing = {
                'starter': {'monthly': 29, 'annual': 290},
                'growth': {'monthly': 99, 'annual': 990},
                'business': {'monthly': 299, 'annual': 2990},
                'enterprise': {'monthly': 999, 'annual': 9990}
            }
            
            total_revenue = 0.0
            for sub in subscriptions:
                tier = sub.get('tier', 'starter')
                billing_period = sub.get('billing_period', 'monthly')
                
                if tier in tier_pricing and billing_period in tier_pricing[tier]:
                    monthly_price = tier_pricing[tier].get('monthly', 0)
                    if billing_period == 'annual':
                        monthly_price = tier_pricing[tier].get('annual', 0) / 12
                    total_revenue += monthly_price
            
            return total_revenue / len(subscriptions) if subscriptions else 0.0
            
        except Exception as e:
            logger.error(f"Failed to calculate average revenue per customer: {e}")
            return 0.0
    
    def _estimate_acquisition_costs(
        self,
        period_days: int,
        include_marketing: bool,
        include_sales: bool
    ) -> float:
        """
        Estimate customer acquisition costs
        
        NOTE: Currently uses fixed $100 per customer estimate.
        TODO: Integrate with acquisition_costs table to use actual recorded costs.
        """
        try:
            # Try to get actual costs from acquisition_costs table first
            start_date = datetime.now() - timedelta(days=period_days)
            
            cost_types = []
            if include_marketing:
                cost_types.append('marketing')
            if include_sales:
                cost_types.append('sales')
            
            has_actual_costs = False
            total_cost = 0.0
            
            if cost_types:
                placeholders = ','.join(['?' for _ in cost_types])
                actual_costs = db_optimizer.execute_query(
                    f"""SELECT SUM(amount) as total FROM acquisition_costs 
                       WHERE cost_date >= ? AND cost_type IN ({placeholders})""",
                    (start_date.isoformat(), *cost_types)
                )
                
                if actual_costs and actual_costs[0].get('total'):
                    total = actual_costs[0]['total']
                    if total and total > 0:
                        has_actual_costs = True
                        total_cost = float(total)
                        logger.info(f"📊 Using actual acquisition costs: ${total_cost:.2f}")
            
            # If require_actual_costs and we don't have actual costs, return None
            if require_actual_costs and not has_actual_costs:
                logger.warning(f"⚠️ No actual acquisition costs recorded for period. Returning None to avoid showing estimated data.")
                return None
            
            # Fallback to estimation only if require_actual_costs=False
            if not has_actual_costs:
                new_customers = db_optimizer.execute_query(
                    """SELECT COUNT(*) as count FROM users 
                       WHERE created_at >= ? AND is_active = 1""",
                    (start_date.isoformat(),)
                )
                customer_count = new_customers[0]['count'] if new_customers else 0
                
                if customer_count == 0:
                    return None
                
                # Estimate average CAC (fallback when no actual costs recorded)
                estimated_cac = 100.0  # $100 per customer average
                total_cost = customer_count * estimated_cac
                logger.warning(f"⚠️ Using estimated acquisition costs: ${total_cost:.2f} ({customer_count} customers × ${estimated_cac})")
            
            return total_cost
            
        except Exception as e:
            logger.error(f"Failed to get acquisition costs: {e}")
            return None
    
    def _estimate_infrastructure_costs(self, period_days: int) -> float:
        """Estimate infrastructure costs (hosting, services, etc.)"""
        # Simplified - in production, integrate with cloud provider billing
        # Estimate: $500-2000/month depending on scale
        days_in_month = 30
        monthly_cost = 1000.0  # Estimated monthly infrastructure cost
        return (monthly_cost / days_in_month) * period_days
    
    def _estimate_personnel_costs(self, period_days: int) -> float:
        """Estimate personnel costs"""
        # Simplified - in production, integrate with payroll system
        # Estimate: $10,000-50,000/month depending on team size
        days_in_month = 30
        monthly_cost = 20000.0  # Estimated monthly personnel cost
        return (monthly_cost / days_in_month) * period_days
    
    def _calculate_new_customer_revenue(self, start_date: datetime) -> float:
        """Calculate revenue from new customers acquired in period"""
        try:
            new_customers = db_optimizer.execute_query(
                """SELECT DISTINCT s.user_id, s.tier, s.billing_period 
                   FROM subscriptions s
                   JOIN users u ON s.user_id = u.id
                   WHERE s.status IN ('active', 'trialing') 
                   AND u.created_at >= ?""",
                (start_date.isoformat(),)
            )
            
            tier_pricing = {
                'starter': {'monthly': 29, 'annual': 290},
                'growth': {'monthly': 99, 'annual': 990},
                'business': {'monthly': 299, 'annual': 2990},
                'enterprise': {'monthly': 999, 'annual': 9990}
            }
            
            total_revenue = 0.0
            for customer in new_customers:
                tier = customer.get('tier', 'starter')
                billing_period = customer.get('billing_period', 'monthly')
                
                if tier in tier_pricing and billing_period in tier_pricing[tier]:
                    monthly_price = tier_pricing[tier].get('monthly', 0)
                    if billing_period == 'annual':
                        monthly_price = tier_pricing[tier].get('annual', 0) / 12
                    total_revenue += monthly_price
            
            return total_revenue
            
        except Exception as e:
            logger.error(f"Failed to calculate new customer revenue: {e}")
            return 0.0
    
    def _calculate_starting_revenue(self, start_date: datetime) -> float:
        """Calculate revenue from customers at start of period"""
        return self._calculate_total_revenue(start_date)
    
    def _calculate_expansion_revenue(self, start_date: datetime) -> float:
        """Calculate revenue from upsells/upgrades (expansion)"""
        # Simplified - in production, track tier upgrades
        # For now, estimate based on tier changes
        try:
            # Get customers who upgraded tiers
            upgrades = db_optimizer.execute_query(
                """SELECT COUNT(*) as count FROM subscriptions 
                   WHERE status IN ('active', 'trialing') 
                   AND updated_at >= ?
                   AND tier IN ('growth', 'business', 'enterprise')""",
                (start_date.isoformat(),)
            )
            
            # Estimate expansion revenue (simplified)
            upgrade_count = upgrades[0]['count'] if upgrades else 0
            avg_upgrade_value = 50.0  # Average monthly increase from upgrade
            
            return upgrade_count * avg_upgrade_value
            
        except Exception as e:
            logger.error(f"Failed to calculate expansion revenue: {e}")
            return 0.0
    
    def _calculate_churned_revenue(self, start_date: datetime) -> float:
        """Calculate revenue lost from churned customers"""
        try:
            # Get canceled subscriptions
            churned = db_optimizer.execute_query(
                """SELECT tier, billing_period FROM subscriptions 
                   WHERE status = 'canceled' AND updated_at >= ?""",
                (start_date.isoformat(),)
            )
            
            tier_pricing = {
                'starter': {'monthly': 29, 'annual': 290},
                'growth': {'monthly': 99, 'annual': 990},
                'business': {'monthly': 299, 'annual': 2990},
                'enterprise': {'monthly': 999, 'annual': 9990}
            }
            
            total_churned = 0.0
            for sub in churned:
                tier = sub.get('tier', 'starter')
                billing_period = sub.get('billing_period', 'monthly')
                
                if tier in tier_pricing and billing_period in tier_pricing[tier]:
                    monthly_price = tier_pricing[tier].get('monthly', 0)
                    if billing_period == 'annual':
                        monthly_price = tier_pricing[tier].get('annual', 0) / 12
                    total_churned += monthly_price
            
            return total_churned
            
        except Exception as e:
            logger.error(f"Failed to calculate churned revenue: {e}")
            return 0.0
    
    def _has_revenue_data(self) -> bool:
        """Check if we have actual revenue data (subscriptions exist)"""
        try:
            subscriptions = db_optimizer.execute_query(
                "SELECT COUNT(*) as count FROM subscriptions WHERE status IN ('active', 'trialing')"
            )
            return subscriptions and subscriptions[0].get('count', 0) > 0
        except Exception:
            return False
    
    def _has_customer_data(self) -> bool:
        """Check if we have customer data"""
        try:
            customers = db_optimizer.execute_query(
                "SELECT COUNT(*) as count FROM users WHERE is_active = 1"
            )
            return customers and customers[0].get('count', 0) > 0
        except Exception:
            return False
    
    def _has_subscription_data(self) -> bool:
        """Check if we have subscription data"""
        try:
            subscriptions = db_optimizer.execute_query(
                "SELECT COUNT(*) as count FROM subscriptions"
            )
            return subscriptions and subscriptions[0].get('count', 0) > 0
        except Exception:
            return False

# Global KPI tracker instance
_kpi_tracker = None

def get_kpi_tracker() -> KPITracker:
    """Get global KPI tracker instance"""
    global _kpi_tracker
    if _kpi_tracker is None:
        _kpi_tracker = KPITracker()
    return _kpi_tracker
