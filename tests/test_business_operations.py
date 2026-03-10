"""
Business operations service tests.
Covers analytics, intelligence, legal compliance, and business blueprint routes.
"""

from datetime import datetime, timedelta

import pytest

from services.business_operations import (
    BusinessAnalytics,
    BusinessIntelligence,
    LegalCompliance,
    business_analytics,
    business_intelligence,
    legal_compliance,
)


@pytest.fixture(autouse=True)
def reset_business_state():
    business_analytics.metrics = {}
    business_analytics.reports = []
    business_intelligence._initialize_default_kpis()
    legal_compliance._initialize_legal_documents()
    legal_compliance.consents = {}
    yield


def test_business_analytics_track_event_records_user():
    analytics = BusinessAnalytics()
    analytics.track_event("signup", {"user_id": "user_1", "plan": "pro"})

    assert "signup" in analytics.metrics
    assert len(analytics.metrics["signup"]) == 1
    event = analytics.metrics["signup"][0]
    assert event["user_id"] == "user_1"
    assert event["properties"]["plan"] == "pro"
    # Should be ISO-8601 and parseable
    assert datetime.fromisoformat(event["timestamp"])


def test_business_analytics_summary_filters_by_days():
    analytics = BusinessAnalytics()
    now = datetime.now()
    recent_ts = (now - timedelta(days=2)).isoformat()
    old_ts = (now - timedelta(days=40)).isoformat()

    analytics.metrics = {
        "signup": [
            {"type": "signup", "properties": {"user_id": "u1"}, "timestamp": recent_ts, "user_id": "u1"},
            {"type": "signup", "properties": {"user_id": "u2"}, "timestamp": old_ts, "user_id": "u2"},
        ],
        "upgrade": [
            {"type": "upgrade", "properties": {"user_id": "u1"}, "timestamp": recent_ts, "user_id": "u1"},
        ],
    }

    summary = analytics.get_analytics_summary(days=30)

    assert summary["total_events"] == 2
    assert summary["event_types"]["signup"] == 1
    assert summary["event_types"]["upgrade"] == 1
    assert summary["unique_users"] == 1
    assert summary["top_events"][0][0] in {"signup", "upgrade"}
    assert isinstance(summary["daily_breakdown"], dict)


def test_business_analytics_generate_report_unknown_type():
    analytics = BusinessAnalytics()
    report = analytics.generate_report("unknown_type")
    assert report["data"]["error"] == "Unknown report type"


def test_business_analytics_generate_user_engagement_report():
    analytics = BusinessAnalytics()
    analytics.track_event("signup", {"user_id": "u1"})
    analytics.track_event("login", {"user_id": "u1"})

    report = analytics.generate_report("user_engagement", {"days": 30})
    data = report["data"]
    assert data["total_users"] == 1
    assert data["total_events"] == 2
    assert data["avg_events_per_user"] == 2


def test_business_intelligence_update_kpi_and_dashboard():
    bi = BusinessIntelligence()
    bi.update_kpi("user_registrations", 1000)
    bi.update_kpi("churn_rate", 3)

    dashboard = bi.get_kpi_dashboard()
    kpis = dashboard["kpis"]
    assert kpis["user_registrations"]["goal_met"] is True
    assert kpis["churn_rate"]["goal_met"] is True
    assert dashboard["goals_met"] >= 2
    assert dashboard["overall_health"] > 0


def test_legal_compliance_get_document_and_consent_status():
    lc = LegalCompliance()
    doc = lc.get_document("privacy_policy")

    assert doc["version"] == "1.0"
    assert "Privacy Policy" in doc["rendered"]

    lc.record_consent("user_1", "privacy_policy", True)
    lc.record_consent("user_1", "privacy_policy", False)

    status = lc.get_consent_status("user_1")
    assert status["privacy_policy"]["consent_given"] is False
    assert status["privacy_policy"]["timestamp"]


def test_legal_compliance_unknown_document():
    lc = LegalCompliance()
    doc = lc.get_document("does_not_exist")
    assert doc["error"] == "Document not found"


@pytest.fixture
def business_client():
    from flask import Flask
    from services.business_operations import create_business_blueprint

    app = Flask(__name__)
    app.register_blueprint(create_business_blueprint())
    return app.test_client()


def test_business_routes_legal_pages(business_client):
    response = business_client.get("/business/privacy-policy")
    assert response.status_code == 200
    assert "Privacy Policy" in response.get_data(as_text=True)

    response = business_client.get("/business/terms-of-service")
    assert response.status_code == 200
    assert "Terms of Service" in response.get_data(as_text=True)

    response = business_client.get("/business/cookie-policy")
    assert response.status_code == 200


def test_business_routes_analytics_summary(business_client):
    response = business_client.get("/business/analytics/summary")
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["success"] is True
    assert "data" in payload


def test_business_routes_track_event_validation(business_client):
    response = business_client.post("/business/analytics/track", json={})
    assert response.status_code == 400
    payload = response.get_json()
    assert payload["success"] is False


def test_business_routes_track_event_success(business_client):
    response = business_client.post(
        "/business/analytics/track",
        json={"event_type": "signup", "properties": {"user_id": "u1"}},
    )
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["success"] is True
    assert "signup" in business_analytics.metrics


def test_business_routes_kpi_update_validation(business_client):
    response = business_client.post("/business/kpi/update", json={"kpi_name": "user_registrations"})
    assert response.status_code == 400


def test_business_routes_kpi_update_success(business_client):
    response = business_client.post(
        "/business/kpi/update",
        json={"kpi_name": "user_registrations", "value": 123},
    )
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["success"] is True
    assert business_intelligence.kpis["user_registrations"]["value"] == 123


def test_business_routes_report_generate_validation(business_client):
    response = business_client.post("/business/reports/generate", json={})
    assert response.status_code == 400


def test_business_routes_report_generate_success(business_client):
    response = business_client.post(
        "/business/reports/generate",
        json={"report_type": "feature_usage", "parameters": {}},
    )
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["success"] is True
    assert payload["data"]["type"] == "feature_usage"
