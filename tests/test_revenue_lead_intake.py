#!/usr/bin/env python3
"""Revenue-critical lead intake tests."""

import os
import sys
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from flask import Flask
from crm.completion_api import crm_bp
from core.webhook_intake_service import WebhookIntakeService, WebhookConfig

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("FLASK_ENV", "test")


class _Idem:
    def __init__(self):
        self.store = {}

    def check_key(self, key):
        return self.store.get(key)

    def store_key(self, key, *_args, **_kwargs):
        self.store[key] = {"status": "pending"}

    def update_key_result(self, key, status, response_data=None):
        self.store[key] = {"status": status, "response_data": response_data}


@pytest.fixture
def client():
    app = Flask(__name__)
    app.config["TESTING"] = True
    app.register_blueprint(crm_bp)
    return app.test_client()


class TestRevenueLeadIntake:
    @patch('crm.completion_api.db_optimizer')
    @patch('core.webhook_intake_service.db_optimizer')
    @patch('core.webhook_intake_service.get_lead_scoring_service')
    def test_webhook_idempotent_upsert_and_pipeline(self, mock_scoring, mock_db, mock_crm_db, client):
        scoring = SimpleNamespace(score=80, quality='A', breakdown={'base': 80})
        mock_scoring.return_value.score_lead.return_value = scoring

        calls = {"inserted": 0}
        def _db_side_effect(sql, params=None, fetch=True):
            sql_upper = sql.strip().upper()
            if sql_upper.startswith("SELECT ID FROM LEADS"):
                return [] if calls["inserted"] == 0 else [{"id": 1}]
            if sql_upper.startswith("UPDATE LEADS"):
                return None
            if sql_upper.startswith("INSERT INTO LEADS"):
                calls["inserted"] += 1
                return None
            if "FROM LEADS L" in sql_upper:
                return [{
                    "id": 1,
                    "user_id": 1,
                    "email": "lead@example.com",
                    "name": "Lead",
                    "phone": None,
                    "company": None,
                    "source": "tally",
                    "stage": "new",
                    "score": 80,
                    "created_at": "2025-01-01",
                    "updated_at": "2025-01-01",
                    "last_contact": None,
                    "notes": "",
                    "tags": "[]",
                    "metadata": "{}",
                    "activity_count": 0,
                    "last_activity": None
                }]
            return []

        mock_db.execute_query.side_effect = _db_side_effect
        mock_crm_db.execute_query.side_effect = _db_side_effect

        service = WebhookIntakeService(WebhookConfig(secret_key="s", allowed_origins=[], enable_verification=False))
        payload = {
            "formId": "f1",
            "submissionId": "sub1",
            "createdAt": "2025-01-01",
            "data": {"name": "Lead", "email": "lead@example.com"}
        }

        idem = _Idem()
        with patch('core.webhook_intake_service.idempotency_manager', idem):
            first = service.process_tally_webhook(payload)
            second = service.process_tally_webhook(payload)

        assert first["success"] is True
        assert second["success"] is True
        assert calls["inserted"] == 1

        # pipeline includes lead (endpoint)
        response = client.get('/api/crm/pipeline/leads/1')
        assert response.status_code == 200
        data = response.get_json()
        pipeline = data.get('pipeline', {})
        assert pipeline.get('new')
