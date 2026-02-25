#!/usr/bin/env python3
"""
KPI API Endpoints
Endpoints for retrieving business KPIs for early-stage and mid-stage companies
"""

import json
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify

from core.kpi_tracker import get_kpi_tracker, CompanyStage
from core.api_validation import handle_api_errors, create_success_response, create_error_response
from core.secure_sessions import get_current_user_id
from core.database_optimization import db_optimizer

logger = logging.getLogger(__name__)

# Create blueprint
kpi_bp = Blueprint('kpi', __name__, url_prefix='/api/kpi')

# Initialize KPI tracker
kpi_tracker = get_kpi_tracker()

@kpi_bp.route('/early-stage', methods=['GET'])
@handle_api_errors
def get_early_stage_kpis():
    """
    Get early-stage company KPIs:
    - Customer Acquisition Cost (CAC)
    - Customer Lifetime Value (CLV)
    - Burn Rate
    - Gross Margin
    
    Returns None for KPIs when actual data is insufficient (no estimates shown).
    Use ?allow_estimates=true to include estimated values.
    """
    try:
        user_id = get_current_user_id()
        if not user_id:
            return create_error_response("Authentication required", 401, 'AUTHENTICATION_REQUIRED')
        
        period_days = request.args.get('period_days', type=int, default=30)
        allow_estimates = request.args.get('allow_estimates', 'false').lower() == 'true'
        
        kpis = kpi_tracker.get_early_stage_kpis(period_days=period_days, require_actual_data=not allow_estimates)
        
        # Build KPI response with data quality indicators
        kpi_response = {
            'stage': 'early_stage',
            'period_days': period_days,
            'data_quality': kpis.data_quality,
            'kpis': {}
        }
        
        # Only include KPIs that have values (not None)
        if kpis.cac is not None:
            kpi_response['kpis']['cac'] = {
                'value': kpis.cac,
                'label': 'Customer Acquisition Cost',
                'description': 'Measures the cost to acquire a new customer. For early-stage companies, it\'s vital to understand if the cost to bring in new customers is sustainable in the long run.',
                'unit': 'USD',
                'data_quality': kpis.data_quality.get('cac', 'unknown'),
                'target': None
            }
        
        if kpis.clv is not None:
            kpi_response['kpis']['clv'] = {
                'value': kpis.clv,
                'label': 'Customer Lifetime Value',
                'description': 'Predicts the net profit attributed to the entire future relationship with a customer. Ideally, the LTV should be significantly higher than the CAC.',
                'unit': 'USD',
                'data_quality': kpis.data_quality.get('clv', 'unknown'),
                'target': None
            }
        
        if kpis.burn_rate is not None:
            kpi_response['kpis']['burn_rate'] = {
                'value': kpis.burn_rate,
                'label': 'Burn Rate',
                'description': 'Represents how much cash the company is spending each month. For startups not yet profitable, understanding the burn rate is essential to determine runway before additional funding or revenue is required.',
                'unit': 'USD/month',
                'data_quality': kpis.data_quality.get('burn_rate', 'unknown'),
                'target': None
            }
        
        if kpis.gross_margin is not None:
            kpi_response['kpis']['gross_margin'] = {
                'value': kpis.gross_margin,
                'label': 'Gross Margin',
                'description': 'Represents the difference between revenue and the cost of goods sold (COGS). It helps determine the basic profitability of the core business.',
                'unit': '%',
                'data_quality': kpis.data_quality.get('gross_margin', 'unknown'),
                'target': None
            }
        
        if kpis.cac_payback_period is not None:
            kpi_response['kpis']['cac_payback_period'] = {
                'value': kpis.cac_payback_period,
                'label': 'CAC Payback Period',
                'description': 'Time (in months) to recover customer acquisition cost',
                'unit': 'months',
                'data_quality': kpis.data_quality.get('cac_payback_period', 'unknown'),
                'target': None
            }
        
        if kpis.clv_cac_ratio is not None:
            kpi_response['kpis']['clv_cac_ratio'] = {
                'value': kpis.clv_cac_ratio,
                'label': 'CLV:CAC Ratio',
                'description': 'Ratio of Customer Lifetime Value to Customer Acquisition Cost. Healthy ratio is typically 3:1 or higher.',
                'unit': 'ratio',
                'data_quality': kpis.data_quality.get('clv_cac_ratio', 'unknown'),
                'target': 3.0
            }
        
        message = 'Early-stage KPIs retrieved successfully'
        if not kpi_response['kpis']:
            message = 'No KPIs available - insufficient actual data. Record costs via POST /api/kpi/costs to enable CAC calculation.'
        
        return create_success_response(kpi_response, message)
        
    except Exception as e:
        logger.error(f"Failed to get early-stage KPIs: {e}", exc_info=True)
        return create_error_response(f"Failed to retrieve KPIs: {str(e)}", 500, 'KPI_ERROR')

@kpi_bp.route('/mid-stage', methods=['GET'])
@handle_api_errors
def get_mid_stage_kpis():
    """
    Get mid-stage company KPIs:
    - Customer Retention Rate
    - Average Revenue Per User (ARPU)
    - Sales Efficiency
    - Net Revenue Retention (NRR)
    
    Returns None for KPIs when actual data is insufficient (no estimates shown).
    Use ?allow_estimates=true to include estimated values.
    """
    try:
        user_id = get_current_user_id()
        if not user_id:
            return create_error_response("Authentication required", 401, 'AUTHENTICATION_REQUIRED')
        
        period_days = request.args.get('period_days', type=int, default=30)
        allow_estimates = request.args.get('allow_estimates', 'false').lower() == 'true'
        
        kpis = kpi_tracker.get_mid_stage_kpis(period_days=period_days, require_actual_data=not allow_estimates)
        
        # Build KPI response with data quality indicators
        kpi_response = {
            'stage': 'mid_stage',
            'period_days': period_days,
            'data_quality': kpis.data_quality,
            'kpis': {}
        }
        
        # Only include KPIs that have values (not None)
        if kpis.retention_rate is not None:
            kpi_response['kpis']['retention_rate'] = {
                'value': kpis.retention_rate,
                'label': 'Customer Retention Rate',
                'description': 'Unlike early-stage companies that often focus on customer acquisition, mid-stage companies emphasize retaining existing customers to ensure sustainable growth.',
                'unit': '%',
                'data_quality': kpis.data_quality.get('retention_rate', 'unknown'),
                'target': 90.0
            }
        
        if kpis.arpu is not None:
            kpi_response['kpis']['arpu'] = {
                'value': kpis.arpu,
                'label': 'Average Revenue Per User',
                'description': 'This metric helps understand the revenue generated per user or customer and is crucial for pricing and revenue strategies.',
                'unit': 'USD',
                'data_quality': kpis.data_quality.get('arpu', 'unknown'),
                'target': None
            }
        
        if kpis.sales_efficiency is not None:
            kpi_response['kpis']['sales_efficiency'] = {
                'value': kpis.sales_efficiency,
                'label': 'Sales Efficiency',
                'description': 'This can be evaluated by assessing the ratio of new revenue gained to sales and marketing costs over a specific period.',
                'unit': 'ratio',
                'data_quality': kpis.data_quality.get('sales_efficiency', 'unknown'),
                'target': 1.0
            }
        
        if kpis.net_revenue_retention is not None:
            kpi_response['kpis']['net_revenue_retention'] = {
                'value': kpis.net_revenue_retention,
                'label': 'Net Revenue Retention',
                'description': 'Measures the changes in recurring revenue from existing customers, accounting for upsells, churn, and contractions.',
                'unit': '%',
                'data_quality': kpis.data_quality.get('net_revenue_retention', 'unknown'),
                'target': 100.0
            }
        
        if kpis.churn_rate is not None:
            kpi_response['kpis']['churn_rate'] = {
                'value': kpis.churn_rate,
                'label': 'Churn Rate',
                'description': 'Percentage of customers lost during the period',
                'unit': '%',
                'data_quality': kpis.data_quality.get('churn_rate', 'unknown'),
                'target': 5.0
            }
        
        if kpis.expansion_revenue is not None:
            kpi_response['kpis']['expansion_revenue'] = {
                'value': kpis.expansion_revenue,
                'label': 'Expansion Revenue',
                'description': 'Revenue from upsells and upgrades',
                'unit': 'USD',
                'data_quality': kpis.data_quality.get('expansion_revenue', 'unknown'),
                'target': None
            }
        
        message = 'Mid-stage KPIs retrieved successfully'
        if not kpi_response['kpis']:
            message = 'No KPIs available - insufficient actual data. Ensure subscriptions and customer data exist.'
        
        return create_success_response(kpi_response, message)
        
    except Exception as e:
        logger.error(f"Failed to get mid-stage KPIs: {e}", exc_info=True)
        return create_error_response(f"Failed to retrieve KPIs: {str(e)}", 500, 'KPI_ERROR')

@kpi_bp.route('/all', methods=['GET'])
@handle_api_errors
def get_all_kpis():
    """
    Get both early-stage and mid-stage KPIs
    
    Returns None for KPIs when actual data is insufficient (no estimates shown).
    Use ?allow_estimates=true to include estimated values.
    """
    try:
        user_id = get_current_user_id()
        if not user_id:
            return create_error_response("Authentication required", 401, 'AUTHENTICATION_REQUIRED')
        
        period_days = request.args.get('period_days', type=int, default=30)
        allow_estimates = request.args.get('allow_estimates', 'false').lower() == 'true'
        
        early_stage = kpi_tracker.get_early_stage_kpis(period_days=period_days, require_actual_data=not allow_estimates)
        mid_stage = kpi_tracker.get_mid_stage_kpis(period_days=period_days, require_actual_data=not allow_estimates)
        
        # Build response with only non-None values
        response_data = {
            'period_days': period_days,
            'allow_estimates': allow_estimates,
            'early_stage': {
                'data_quality': early_stage.data_quality,
                'kpis': {}
            },
            'mid_stage': {
                'data_quality': mid_stage.data_quality,
                'kpis': {}
            }
        }
        
        # Add early-stage KPIs (only non-None)
        if early_stage.cac is not None:
            response_data['early_stage']['kpis']['cac'] = early_stage.cac
        if early_stage.clv is not None:
            response_data['early_stage']['kpis']['clv'] = early_stage.clv
        if early_stage.burn_rate is not None:
            response_data['early_stage']['kpis']['burn_rate'] = early_stage.burn_rate
        if early_stage.gross_margin is not None:
            response_data['early_stage']['kpis']['gross_margin'] = early_stage.gross_margin
        if early_stage.cac_payback_period is not None:
            response_data['early_stage']['kpis']['cac_payback_period'] = early_stage.cac_payback_period
        if early_stage.clv_cac_ratio is not None:
            response_data['early_stage']['kpis']['clv_cac_ratio'] = early_stage.clv_cac_ratio
        
        # Add mid-stage KPIs (only non-None)
        if mid_stage.retention_rate is not None:
            response_data['mid_stage']['kpis']['retention_rate'] = mid_stage.retention_rate
        if mid_stage.arpu is not None:
            response_data['mid_stage']['kpis']['arpu'] = mid_stage.arpu
        if mid_stage.sales_efficiency is not None:
            response_data['mid_stage']['kpis']['sales_efficiency'] = mid_stage.sales_efficiency
        if mid_stage.net_revenue_retention is not None:
            response_data['mid_stage']['kpis']['net_revenue_retention'] = mid_stage.net_revenue_retention
        if mid_stage.churn_rate is not None:
            response_data['mid_stage']['kpis']['churn_rate'] = mid_stage.churn_rate
        if mid_stage.expansion_revenue is not None:
            response_data['mid_stage']['kpis']['expansion_revenue'] = mid_stage.expansion_revenue
        
        message = 'All KPIs retrieved successfully'
        if not response_data['early_stage']['kpis'] and not response_data['mid_stage']['kpis']:
            message = 'No KPIs available - insufficient actual data. Record costs and ensure subscription data exists.'
        
        return create_success_response(response_data, message)
        
    except Exception as e:
        logger.error(f"Failed to get all KPIs: {e}", exc_info=True)
        return create_error_response(f"Failed to retrieve KPIs: {str(e)}", 500, 'KPI_ERROR')

@kpi_bp.route('/historical', methods=['GET'])
@handle_api_errors
def get_historical_kpis():
    """Get historical KPI data for trend analysis"""
    try:
        user_id = get_current_user_id()
        if not user_id:
            return create_error_response("Authentication required", 401, 'AUTHENTICATION_REQUIRED')
        
        kpi_type = request.args.get('kpi_type')  # Optional: filter by KPI type
        stage = request.args.get('stage')  # Optional: 'early_stage' or 'mid_stage'
        days = request.args.get('days', type=int, default=90)
        
        start_date = datetime.now() - timedelta(days=days)
        
        query = """SELECT snapshot_date, company_stage, kpi_type, kpi_value, metadata 
                   FROM kpi_snapshots 
                   WHERE snapshot_date >= ?"""
        params = [start_date.isoformat()]
        
        if kpi_type:
            query += " AND kpi_type = ?"
            params.append(kpi_type)
        
        if stage:
            query += " AND company_stage = ?"
            params.append(stage)
        
        query += " ORDER BY snapshot_date DESC"
        
        historical_data = db_optimizer.execute_query(query, tuple(params))
        
        return create_success_response({
            'historical_data': [
                {
                    'date': row['snapshot_date'],
                    'stage': row['company_stage'],
                    'kpi_type': row['kpi_type'],
                    'value': row['kpi_value'],
                    'metadata': json.loads(row['metadata']) if row.get('metadata') else {}
                }
                for row in historical_data
            ],
            'period_days': days
        }, 'Historical KPI data retrieved successfully')
        
    except Exception as e:
        logger.error(f"Failed to get historical KPIs: {e}", exc_info=True)
        return create_error_response(f"Failed to retrieve historical KPIs: {str(e)}", 500, 'KPI_ERROR')

@kpi_bp.route('/snapshot', methods=['POST'])
@handle_api_errors
def create_kpi_snapshot():
    """Create a snapshot of current KPIs for historical tracking"""
    try:
        user_id = get_current_user_id()
        if not user_id:
            return create_error_response("Authentication required", 401, 'AUTHENTICATION_REQUIRED')
        
        # Calculate current KPIs
        early_stage = kpi_tracker.get_early_stage_kpis()
        mid_stage = kpi_tracker.get_mid_stage_kpis()
        
        snapshot_date = datetime.now().date().isoformat()
        snapshots_created = []
        
        # Early-stage KPIs
        early_stage_kpis = [
            ('cac', early_stage.cac),
            ('clv', early_stage.clv),
            ('burn_rate', early_stage.burn_rate),
            ('gross_margin', early_stage.gross_margin)
        ]
        
        for kpi_type, value in early_stage_kpis:
            db_optimizer.execute_query(
                """INSERT OR REPLACE INTO kpi_snapshots 
                   (snapshot_date, company_stage, kpi_type, kpi_value)
                   VALUES (?, ?, ?, ?)""",
                (snapshot_date, CompanyStage.EARLY_STAGE.value, kpi_type, value),
                fetch=False
            )
            snapshots_created.append(f"{CompanyStage.EARLY_STAGE.value}.{kpi_type}")
        
        # Mid-stage KPIs
        mid_stage_kpis = [
            ('retention_rate', mid_stage.retention_rate),
            ('arpu', mid_stage.arpu),
            ('sales_efficiency', mid_stage.sales_efficiency),
            ('nrr', mid_stage.net_revenue_retention)
        ]
        
        for kpi_type, value in mid_stage_kpis:
            db_optimizer.execute_query(
                """INSERT OR REPLACE INTO kpi_snapshots 
                   (snapshot_date, company_stage, kpi_type, kpi_value)
                   VALUES (?, ?, ?, ?)""",
                (snapshot_date, CompanyStage.MID_STAGE.value, kpi_type, value),
                fetch=False
            )
            snapshots_created.append(f"{CompanyStage.MID_STAGE.value}.{kpi_type}")
        
        logger.info(f"📊 Created KPI snapshot for {snapshot_date}: {len(snapshots_created)} KPIs")
        
        return create_success_response({
            'snapshot_date': snapshot_date,
            'snapshots_created': snapshots_created,
            'count': len(snapshots_created)
        }, 'KPI snapshot created successfully')
        
    except Exception as e:
        logger.error(f"Failed to create KPI snapshot: {e}", exc_info=True)
        return create_error_response(f"Failed to create snapshot: {str(e)}", 500, 'KPI_SNAPSHOT_ERROR')

@kpi_bp.route('/costs', methods=['POST'])
@handle_api_errors
def record_acquisition_cost():
    """Record marketing or sales acquisition cost"""
    try:
        user_id = get_current_user_id()
        if not user_id:
            return create_error_response("Authentication required", 401, 'AUTHENTICATION_REQUIRED')
        
        data = request.get_json() or {}
        cost_date = data.get('cost_date', datetime.now().date().isoformat())
        cost_type = data.get('cost_type', '').strip()
        amount = data.get('amount', 0)
        description = data.get('description', '').strip()
        channel = data.get('channel', '').strip()
        
        if not cost_type:
            return create_error_response("cost_type is required", 400, 'MISSING_FIELD')
        
        if amount <= 0:
            return create_error_response("amount must be greater than 0", 400, 'INVALID_AMOUNT')
        
        cost_id = db_optimizer.execute_query(
            """INSERT INTO acquisition_costs 
               (cost_date, cost_type, amount, description, channel)
               VALUES (?, ?, ?, ?, ?)""",
            (cost_date, cost_type, amount, description, channel),
            fetch=False
        )
        
        logger.info(f"📊 Recorded acquisition cost: ${amount} ({cost_type})")
        
        return create_success_response({
            'cost_id': cost_id,
            'cost_date': cost_date,
            'cost_type': cost_type,
            'amount': amount
        }, 'Acquisition cost recorded successfully')
        
    except Exception as e:
        logger.error(f"Failed to record acquisition cost: {e}", exc_info=True)
        return create_error_response(f"Failed to record cost: {str(e)}", 500, 'COST_RECORD_ERROR')

@kpi_bp.route('/costs', methods=['GET'])
@handle_api_errors
def get_acquisition_costs():
    """Get acquisition costs for a period"""
    try:
        user_id = get_current_user_id()
        if not user_id:
            return create_error_response("Authentication required", 401, 'AUTHENTICATION_REQUIRED')
        
        days = request.args.get('days', type=int, default=30)
        cost_type = request.args.get('cost_type')  # Optional filter
        
        start_date = datetime.now() - timedelta(days=days)
        
        query = """SELECT cost_date, cost_type, amount, description, channel 
                   FROM acquisition_costs 
                   WHERE cost_date >= ?"""
        params = [start_date.isoformat()]
        
        if cost_type:
            query += " AND cost_type = ?"
            params.append(cost_type)
        
        query += " ORDER BY cost_date DESC"
        
        costs = db_optimizer.execute_query(query, tuple(params))
        
        total_cost = sum(row['amount'] for row in costs)
        
        return create_success_response({
            'costs': [
                {
                    'date': row['cost_date'],
                    'type': row['cost_type'],
                    'amount': row['amount'],
                    'description': row['description'],
                    'channel': row['channel']
                }
                for row in costs
            ],
            'total_cost': total_cost,
            'period_days': days
        }, 'Acquisition costs retrieved successfully')
        
    except Exception as e:
        logger.error(f"Failed to get acquisition costs: {e}", exc_info=True)
        return create_error_response(f"Failed to retrieve costs: {str(e)}", 500, 'COST_RETRIEVE_ERROR')
