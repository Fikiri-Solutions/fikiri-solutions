from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from core.database import get_db
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/dashboard/timeseries")
def get_dashboard_timeseries(user_id: int, db: Session = Depends(get_db)):
    """Get dashboard timeseries data for the last 14 days with change calculations"""
    try:
        # Get last 14 days (7 current + 7 previous)
        rows = db.execute("""
            SELECT
                DATE(created_at) as day,
                COUNT(*) FILTER (WHERE type='lead') as leads,
                COUNT(*) FILTER (WHERE type='email') as emails,
                SUM(amount) FILTER (WHERE type='deal') as revenue
            FROM metrics
            WHERE user_id = :uid
            GROUP BY day
            ORDER BY day DESC
            LIMIT 14
        """, {"uid": user_id}).fetchall()

        data = [
            {
                "day": str(r.day),
                "leads": r.leads or 0,
                "emails": r.emails or 0,
                "revenue": float(r.revenue or 0.0),
            }
            for r in rows
        ][::-1]  # oldest → newest

        # Split into current vs previous 7 days
        current = data[-7:]
        previous = data[:7] if len(data) > 7 else []

        def calc_change(key):
            cur = sum(d[key] for d in current)
            prev = sum(d[key] for d in previous) if previous else 0
            if prev == 0: 
                return {"change_pct": None, "positive": True}
            change = ((cur - prev) / prev) * 100
            return {"change_pct": round(change, 1), "positive": change >= 0}

        return {
            "timeseries": data,
            "summary": {
                "leads": calc_change("leads"),
                "emails": calc_change("emails"),
                "revenue": calc_change("revenue")
            }
        }
    except Exception as e:
        logger.error(f"Error fetching dashboard timeseries: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch dashboard data")

@router.get("/dashboard/metrics")
def get_dashboard_metrics(user_id: int, db: Session = Depends(get_db)):
    """Get current dashboard metrics summary"""
    try:
        # Get current metrics
        metrics = db.execute("""
            SELECT
                COUNT(*) FILTER (WHERE type='lead') as total_leads,
                COUNT(*) FILTER (WHERE type='email') as total_emails,
                SUM(amount) FILTER (WHERE type='deal') as total_revenue,
                COUNT(*) FILTER (WHERE type='lead' AND DATE(created_at) = CURRENT_DATE) as today_leads,
                COUNT(*) FILTER (WHERE type='email' AND DATE(created_at) = CURRENT_DATE) as today_emails
            FROM metrics
            WHERE user_id = :uid
        """, {"uid": user_id}).fetchone()

        return {
            "total_leads": metrics.total_leads or 0,
            "total_emails": metrics.total_emails or 0,
            "total_revenue": float(metrics.total_revenue or 0.0),
            "today_leads": metrics.today_leads or 0,
            "today_emails": metrics.today_emails or 0
        }
    except Exception as e:
        logger.error(f"Error fetching dashboard metrics: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch dashboard metrics")
