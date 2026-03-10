# KPI Tracking System

**Status**: ✅ Complete  
**Date**: Feb 2026

## Overview

Comprehensive KPI tracking system for early-stage and mid-stage companies, tracking key financial and growth metrics aligned with industry best practices.

## Philosophy: No Wrong Data

**The system prioritizes accuracy over completeness.** By default, KPIs are only returned when actual data is available. Estimated or hardcoded values are not shown unless explicitly requested via the `allow_estimates=true` query parameter. This prevents misleading stakeholders with inaccurate data and builds trust through transparency.

### Key Principles

1. **Default: Actual Data Only** - KPIs return `null` when actual data is insufficient
2. **Estimates Are Opt-In** - Use `?allow_estimates=true` to include estimated values
3. **Clear Data Quality Indicators** - Each response includes `data_quality` showing whether values are `actual`, `estimated`, or `insufficient_data`
4. **Helpful Guidance** - When no KPIs are available, responses include instructions on how to enable them

### Enabling KPIs

To enable KPI calculations, ensure you have:

- **CAC**: Record actual costs via `POST /api/kpi/costs` with `cost_type: "marketing"` or `"sales"`
- **CLV, Gross Margin, ARPU, NRR**: Ensure subscriptions exist with active status
- **Churn Rate, Retention Rate**: Ensure subscription/customer data exists
- **Burn Rate**: Record infrastructure and personnel costs (or use `allow_estimates=true`)

## Early-Stage KPIs

### 1. Customer Acquisition Cost (CAC)
**Definition**: Measures the cost to acquire a new customer. For early-stage companies, it's vital to understand if the cost to bring in new customers is sustainable in the long run.

**Formula**: `CAC = (Total Sales & Marketing Costs) / (New Customers Acquired)`

**Calculation**:
- Tracks new customers acquired in period
- **Currently**: Estimates sales & marketing costs using fixed $100 per customer estimate
- **Future**: Will use actual costs from `acquisition_costs` table
- Divides total costs by customer count

**Endpoint**: `GET /api/kpi/early-stage?period_days=30`

### 2. Customer Lifetime Value (CLV)
**Definition**: Predicts the net profit attributed to the entire future relationship with a customer. Ideally, the LTV should be significantly higher than the CAC.

**Formula**: `CLV = (Average Revenue Per Customer) × (Average Customer Lifespan) × (Gross Margin %)`

**Calculation**:
- Average monthly revenue per customer from subscriptions
- Customer lifespan estimated from churn rate (1 / monthly churn rate)
- Gross margin percentage calculated from revenue and COGS

**Endpoint**: `GET /api/kpi/early-stage?period_days=30`

### 3. Burn Rate
**Definition**: Represents how much cash the company is spending each month. For startups not yet profitable, understanding the burn rate is essential to determine runway before additional funding or revenue is required.

**Formula**: `Burn Rate = Total Monthly Operating Expenses`

**Calculation**:
- Infrastructure costs (hosting, services)
- Personnel costs (salaries, benefits)
- Marketing & sales costs
- Other operating expenses

**Endpoint**: `GET /api/kpi/early-stage?period_days=30`

### 4. Gross Margin
**Definition**: Represents the difference between revenue and the cost of goods sold (COGS). It helps determine the basic profitability of the core business.

**Formula**: `Gross Margin % = ((Revenue - COGS) / Revenue) × 100`

**Calculation**:
- Total revenue estimated from `subscriptions` table using hardcoded tier prices
- **Currently**: COGS hardcoded as 20% of revenue (`_calculate_cogs()`)
- **Future**: Will use actual COGS from cost tracking
- Calculates margin percentage

**Endpoint**: `GET /api/kpi/early-stage?period_days=30`

### Derived Metrics
- **CAC Payback Period**: Time (months) to recover customer acquisition cost
- **CLV:CAC Ratio**: Ratio of Customer Lifetime Value to CAC (healthy: 3:1 or higher)

## Mid-Stage KPIs

### 1. Customer Retention Rate
**Definition**: Unlike early-stage companies that often focus on customer acquisition, mid-stage companies emphasize retaining existing customers to ensure sustainable growth.

**Formula**: `Retention Rate = ((Customers at End - New Customers) / Customers at Start) × 100`

**Calculation**:
- Tracks customers at start of period
- Subtracts new customers acquired
- Divides by customers at start

**Endpoint**: `GET /api/kpi/mid-stage?period_days=30`

### 2. Average Revenue Per User (ARPU)
**Definition**: This metric helps understand the revenue generated per user or customer and is crucial for pricing and revenue strategies.

**Formula**: `ARPU = Total Revenue / Number of Active Customers`

**Calculation**:
- Total revenue estimated from `subscriptions` table using hardcoded tier prices
- Number of active customers (with active/trialing subscriptions)
- Divides revenue by customer count

**Endpoint**: `GET /api/kpi/mid-stage?period_days=30`

### 3. Sales Efficiency
**Definition**: This can be evaluated by assessing the ratio of new revenue gained to sales and marketing costs over a specific period.

**Formula**: `Sales Efficiency = New Revenue / (Sales + Marketing Costs)`

**Calculation**:
- Revenue from new customers estimated using tier prices
- **Currently**: Sales & marketing costs estimated (fixed $100 per customer)
- **Future**: Will use actual costs from `acquisition_costs` table
- Ratio of new revenue to costs

**Endpoint**: `GET /api/kpi/mid-stage?period_days=30`

### 4. Net Revenue Retention (NRR)
**Definition**: Measures the changes in recurring revenue from existing customers, accounting for upsells, churn, and contractions.

**Formula**: `NRR = ((Starting Revenue + Expansion Revenue - Churned Revenue) / Starting Revenue) × 100`

**Calculation**:
- Starting revenue from existing customers
- Expansion revenue from upsells/upgrades
- Churned revenue from canceled subscriptions
- Calculates net retention percentage

**Endpoint**: `GET /api/kpi/mid-stage?period_days=30`

### Additional Metrics
- **Churn Rate**: Percentage of customers lost during period
- **Expansion Revenue**: Revenue from upsells and upgrades

## API Endpoints

### Default Behavior: Actual Data Only

All KPI endpoints return `null` for KPIs when actual data is insufficient. This prevents showing misleading estimates.

To include estimated values (when available), add `?allow_estimates=true` to the request URL.

### Response Format

Each KPI response includes:
- `data_quality`: Dictionary indicating data quality for each KPI (`actual`, `estimated`, `insufficient_data`)
- `kpis`: Object containing only KPIs with actual values (null values are excluded)
- Message indicating if no KPIs are available and guidance on enabling them

### Get Early-Stage KPIs
```bash
GET /api/kpi/early-stage?period_days=30
```

**Response**:
```json
{
  "success": true,
  "data": {
    "stage": "early_stage",
    "period_days": 30,
    "kpis": {
      "cac": {
        "value": 100.0,
        "label": "Customer Acquisition Cost",
        "description": "...",
        "unit": "USD"
      },
      "clv": {
        "value": 2500.0,
        "label": "Customer Lifetime Value",
        "description": "...",
        "unit": "USD"
      },
      "burn_rate": {
        "value": 20000.0,
        "label": "Burn Rate",
        "description": "...",
        "unit": "USD/month"
      },
      "gross_margin": {
        "value": 80.0,
        "label": "Gross Margin",
        "description": "...",
        "unit": "%"
      },
      "clv_cac_ratio": {
        "value": 25.0,
        "label": "CLV:CAC Ratio",
        "description": "...",
        "unit": "ratio",
        "target": 3.0
      }
    }
  }
}
```

### Get Mid-Stage KPIs
```bash
GET /api/kpi/mid-stage?period_days=30
GET /api/kpi/mid-stage?period_days=30&allow_estimates=true
```

**Query Parameters:** Same as early-stage endpoint.

**Response Format:** Same structure as early-stage endpoint (see above).

### Get All KPIs
```bash
GET /api/kpi/all?period_days=30
GET /api/kpi/all?period_days=30&allow_estimates=true
```

**Query Parameters:** Same as above.

**Response Format:** Includes both `early_stage` and `mid_stage` objects, each with `data_quality` and `kpis` fields.

### Historical KPI Data
```bash
GET /api/kpi/historical?days=90&kpi_type=cac&stage=early_stage
```

### Create KPI Snapshot
```bash
POST /api/kpi/snapshot
```
Creates a snapshot of current KPIs for historical tracking.

### Record Acquisition Costs
```bash
POST /api/kpi/costs
{
  "cost_date": "2026-02-19",
  "cost_type": "marketing",
  "amount": 5000.0,
  "description": "Google Ads campaign",
  "channel": "paid"
}
```

### Get Acquisition Costs
```bash
GET /api/kpi/costs?days=30&cost_type=marketing
```

## Database Schema

### kpi_snapshots
Stores historical KPI snapshots for trend analysis:
- `snapshot_date` - Date of snapshot
- `company_stage` - 'early_stage' or 'mid_stage'
- `kpi_type` - Type of KPI (cac, clv, burn_rate, etc.)
- `kpi_value` - KPI value
- `metadata` - Additional context (JSON)

### acquisition_costs
Tracks marketing and sales costs:
- `cost_date` - Date of cost
- `cost_type` - 'marketing', 'sales', 'advertising', 'other'
- `amount` - Cost amount
- `description` - Cost description
- `channel` - Acquisition channel

### revenue_tracking
Tracks detailed revenue data (table exists but not currently used in calculations):
- `revenue_date` - Date of revenue
- `user_id` - Customer user ID
- `subscription_id` - Subscription ID
- `revenue_type` - 'subscription', 'upsell', 'expansion', 'one_time'
- `amount` - Revenue amount
- `tier` - Subscription tier
- `billing_period` - 'monthly' or 'annual'

**Note**: This table exists but revenue calculations currently use hardcoded tier prices from `subscriptions` table instead.

## Implementation Notes

### Current Implementation State

**✅ Implemented:**
- KPI calculation engine with all 8 metrics
- API endpoints for retrieving KPIs
- Database tables for historical tracking
- Cost recording endpoints (data collection ready)

**⚠️ Current Limitations (Estimation-Based):**

1. **Revenue Calculation**: 
   - **Current**: Estimated from `subscriptions` table using hardcoded tier prices in `kpi_tracker.py`
   - **NOT used**: Stripe API or `revenue_tracking` table
   - **In production**: Integrate with Stripe API for actual revenue, track one-time payments, include usage-based revenue

2. **Cost Estimation**: 
   - **Current**: Attempts to read from `acquisition_costs` table first, falls back to fixed $100 per customer estimate if no data
   - **Status**: Code updated to use actual costs when available, but estimation fallback remains
   - **In production**: Ensure all costs are recorded via `/api/kpi/costs` endpoint for accurate CAC

3. **COGS Calculation**: 
   - **Current**: Hardcoded as 20% of revenue in `_calculate_cogs()`
   - **NOT used**: Real cost data
   - **In production**: Track actual hosting costs, support costs, payment processing fees

### Production Enhancements
1. **Real-time Cost Tracking**: Integrate with finance systems
2. **Stripe Integration**: Pull actual revenue from Stripe
3. **Automated Snapshots**: Daily/weekly KPI snapshots
4. **Alerting**: Alert when KPIs fall below thresholds
5. **Forecasting**: Predict future KPIs based on trends
6. **Benchmarking**: Compare against industry benchmarks

## Usage Examples

### Track Marketing Spend
```bash
POST /api/kpi/costs
{
  "cost_type": "marketing",
  "amount": 5000.0,
  "description": "Facebook Ads - Q1 Campaign",
  "channel": "paid"
}
```

### Get Current KPIs
```bash
GET /api/kpi/all?period_days=30
```

### View Historical Trends
```bash
GET /api/kpi/historical?days=90&kpi_type=cac
```

### Create Daily Snapshot
```bash
POST /api/kpi/snapshot
```

## Files Created

- `core/kpi_tracker.py` - KPI calculation engine
- `routes/kpi_api.py` - KPI API endpoints
- `docs/KPI_TRACKING_SYSTEM.md` - This documentation

## Database Tables Added

- `kpi_snapshots` - Historical KPI data (✅ used for snapshots)
- `acquisition_costs` - Marketing/sales cost tracking (⚠️ endpoints exist, data not yet consumed in calculations)
- `revenue_tracking` - Detailed revenue tracking (⚠️ table exists, not currently used)

## Current Data Flow

**Revenue Calculation:**
- ✅ Reads from `subscriptions` table
- ⚠️ Uses hardcoded tier prices (not Stripe API or `revenue_tracking`)

**Cost Calculation:**
- ✅ Code attempts to read from `acquisition_costs` table first
- ⚠️ Falls back to fixed $100 per customer estimate if no costs recorded
- ✅ To get accurate CAC: Record all marketing/sales costs via `POST /api/kpi/costs`

**COGS Calculation:**
- ⚠️ Hardcoded as 20% of revenue
- ⚠️ Not using actual cost data

## Integration

**Current Data Sources:**
- `subscriptions` table - For revenue estimation (using hardcoded tier prices) and customer data
- `users` table - For customer acquisition tracking
- `billing_usage` table - Available but not currently used in calculations

**Future Data Sources (Not Yet Integrated):**
- `acquisition_costs` table - Cost recording endpoints exist, but data not consumed in calculations
- `revenue_tracking` table - Table exists but not used for revenue calculations
- Stripe API - For actual revenue data (not yet integrated)

## Next Steps

### Priority 1: Use Actual Data Sources
1. ✅ **`acquisition_costs` table integration**: Code updated to read from table (falls back to estimation if empty)
2. **Integrate Stripe API**: Replace hardcoded tier prices with actual Stripe revenue data
3. **Use `revenue_tracking` table**: Populate and use for detailed revenue analysis
4. **Real COGS tracking**: Replace 20% estimate with actual cost data

### Priority 2: Enhancements
5. **Cost Tracking UI**: Frontend for recording costs
6. **KPI Dashboard**: Visual dashboard for KPIs
7. **Automated Snapshots**: Scheduled daily/weekly snapshots
8. **Alerting**: Alert when KPIs exceed thresholds
9. **Forecasting**: ML-based KPI forecasting
