#!/usr/bin/env python3
"""Regression tests for chatbot knowledge lifecycle and retrieval health."""

import os
import unittest
from unittest.mock import patch

os.environ.setdefault("FLASK_ENV", "test")

from core.chatbot_knowledge_lifecycle import (
    ArtifactType,
    LifecycleState,
    compute_tenant_retrieval_health,
    lifecycle_table_enabled,
    mark_kb_stored,
    mark_kb_vectorization_completed,
    upsert_lifecycle_row,
)
from core.database_optimization import db_optimizer


class TestChatbotKnowledgeLifecycle(unittest.TestCase):
    def setUp(self):
        os.environ["FIKIRI_CHATBOT_LIFECYCLE_FORCE"] = "1"
        db_optimizer._initialize_database()

    def tearDown(self):
        os.environ.pop("FIKIRI_CHATBOT_LIFECYCLE_FORCE", None)

    def test_lifecycle_table_exists_after_init(self):
        self.assertTrue(lifecycle_table_enabled())

    def test_upsert_and_health_reflects_kb_semantic_ready(self):
        tenant = "lifecycle_test_tenant"
        doc_id = "doc_lifecycle_1"
        mark_kb_stored(doc_id=doc_id, tenant_id=tenant, user_id=99)
        mark_kb_vectorization_completed(
            doc_id=doc_id,
            tenant_id=tenant,
            user_id=99,
            vector_chunk_count=2,
        )
        rows = db_optimizer.execute_query(
            """
            SELECT lifecycle_state, retrieval_ready, vector_chunk_count
            FROM chatbot_knowledge_lifecycle
            WHERE artifact_id = ? AND artifact_type = ?
            """,
            (doc_id, ArtifactType.KB_DOCUMENT.value),
            fetch=True,
        )
        self.assertEqual(len(rows), 1)
        row = dict(rows[0]) if not isinstance(rows[0], dict) else rows[0]
        self.assertEqual(row["lifecycle_state"], LifecycleState.RETRIEVAL_READY.value)
        self.assertEqual(row["retrieval_ready"], 1)
        self.assertEqual(row["vector_chunk_count"], 2)

    def test_compute_health_includes_preview_parity_flag(self):
        health = compute_tenant_retrieval_health("1", user_id=1)
        self.assertTrue(health.get("preview_live_parity"))
        self.assertIn("summary", health)
        self.assertIn("platform_seed_faq_count", health["summary"])

    @patch("core.chatbot_smart_faq_api.retrieve_chatbot_context")
    @patch("core.chatbot_smart_faq_api.generate_chatbot_answer")
    @patch("core.chatbot_smart_faq_api.load_chatbot_config")
    def test_retrieval_health_endpoint_requires_auth(
        self, mock_cfg, mock_gen, mock_ret
    ):
        from flask import Flask
        from core.chatbot_smart_faq_api import chatbot_bp

        app = Flask(__name__)
        app.config["TESTING"] = True
        app.register_blueprint(chatbot_bp)
        client = app.test_client()
        response = client.get("/api/chatbot/knowledge/retrieval-health")
        self.assertEqual(response.status_code, 401)

    @patch("core.chatbot_smart_faq_api._require_authenticated_user_id", return_value=42)
    def test_retrieval_health_endpoint_returns_truthful_summary(self, _mock_uid):
        from flask import Flask
        from core.chatbot_smart_faq_api import chatbot_bp

        app = Flask(__name__)
        app.config["TESTING"] = True
        app.register_blueprint(chatbot_bp)
        client = app.test_client()
        response = client.get("/api/chatbot/knowledge/retrieval-health")
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data["success"])
        self.assertEqual(data["health"]["tenant_id"], "42")
        self.assertIn("kb_stored_count", data["health"]["summary"])


if __name__ == "__main__":
    unittest.main()
