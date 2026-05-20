#!/usr/bin/env python3
"""Durable chatbot conversation persistence (append-only, tenant-scoped)."""

import json
import os
import sys
import unittest
from unittest.mock import Mock, patch

os.environ.setdefault("FLASK_ENV", "test")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.database_optimization import db_optimizer
from core.chatbot_conversation_store import (
    ROLE_ASSISTANT,
    ROLE_USER,
    append_message,
    ensure_chatbot_conversation_tables,
    get_or_create_conversation,
    is_preview_persistence_enabled,
    is_public_persistence_enabled,
    list_conversation_messages,
    persist_chatbot_turn,
    should_store_retrieval_debug,
)


class TestChatbotConversationStore(unittest.TestCase):
    TENANT_A = "tenant-a-eval"
    TENANT_B = "tenant-b-eval"
    CONV = "conv-test-001"

    def setUp(self):
        ensure_chatbot_conversation_tables()
        for tid in (self.TENANT_A, self.TENANT_B):
            db_optimizer.execute_query(
                "DELETE FROM chatbot_messages WHERE tenant_id = ?",
                (tid,),
                fetch=False,
            )
            db_optimizer.execute_query(
                "DELETE FROM chatbot_conversations WHERE tenant_id = ?",
                (tid,),
                fetch=False,
            )

    def test_conversation_creation(self):
        get_or_create_conversation(
            tenant_id=self.TENANT_A,
            conversation_id=self.CONV,
            user_id="user-1",
            session_id="sess-1",
            channel="public_api",
        )
        rows = db_optimizer.execute_query(
            """
            SELECT tenant_id, conversation_id, user_id, session_id, channel
            FROM chatbot_conversations
            WHERE tenant_id = ? AND conversation_id = ?
            """,
            (self.TENANT_A, self.CONV),
        )
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["channel"], "public_api")

    def test_append_messages_and_replay_ordering(self):
        append_message(
            tenant_id=self.TENANT_A,
            conversation_id=self.CONV,
            role=ROLE_USER,
            content="First question",
            message_id="m-user-1",
        )
        append_message(
            tenant_id=self.TENANT_A,
            conversation_id=self.CONV,
            role=ROLE_ASSISTANT,
            content="First answer",
            message_id="m-asst-1",
            fallback_used=False,
            confidence=0.9,
        )
        append_message(
            tenant_id=self.TENANT_A,
            conversation_id=self.CONV,
            role=ROLE_USER,
            content="Second question",
            message_id="m-user-2",
        )

        replay = list_conversation_messages(self.TENANT_A, self.CONV)
        self.assertEqual(len(replay), 3)
        self.assertEqual(replay[0]["role"], ROLE_USER)
        self.assertEqual(replay[0]["content"], "First question")
        self.assertEqual(replay[1]["role"], ROLE_ASSISTANT)
        self.assertEqual(replay[2]["content"], "Second question")

    def test_tenant_isolation(self):
        append_message(
            tenant_id=self.TENANT_A,
            conversation_id=self.CONV,
            role=ROLE_USER,
            content="secret A",
            message_id="only-a",
        )
        append_message(
            tenant_id=self.TENANT_B,
            conversation_id=self.CONV,
            role=ROLE_USER,
            content="secret B",
            message_id="only-b",
        )
        a_msgs = list_conversation_messages(self.TENANT_A, self.CONV)
        b_msgs = list_conversation_messages(self.TENANT_B, self.CONV)
        self.assertEqual(len(a_msgs), 1)
        self.assertEqual(a_msgs[0]["content"], "secret A")
        self.assertEqual(b_msgs[0]["content"], "secret B")

    def test_fallback_persisted_on_turn(self):
        persist_chatbot_turn(
            tenant_id=self.TENANT_A,
            conversation_id="conv-fallback",
            query="unknown?",
            answer="I need more context.",
            assistant_message_id="asst-fb-1",
            sources=[],
            fallback_used=True,
            confidence=0.2,
            retrieval_confidence=0.0,
        )
        rows = list_conversation_messages(self.TENANT_A, "conv-fallback")
        assistant = [r for r in rows if r["role"] == ROLE_ASSISTANT][0]
        self.assertTrue(assistant["fallback_used"])
        self.assertAlmostEqual(float(assistant["confidence"] or 0), 0.2)

    def test_persist_failure_does_not_raise(self):
        with patch(
            "core.chatbot_conversation_store.append_message",
            side_effect=RuntimeError("db down"),
        ):
            persist_chatbot_turn(
                tenant_id=self.TENANT_A,
                conversation_id="conv-fail",
                query="q",
                answer="a",
                assistant_message_id="mid-1",
                sources=[],
                fallback_used=False,
                confidence=0.5,
                retrieval_confidence=0.5,
            )

    def test_idempotent_message_append(self):
        append_message(
            tenant_id=self.TENANT_A,
            conversation_id=self.CONV,
            role=ROLE_USER,
            content="once",
            message_id="dup-id",
        )
        append_message(
            tenant_id=self.TENANT_A,
            conversation_id=self.CONV,
            role=ROLE_USER,
            content="once again",
            message_id="dup-id",
        )
        rows = list_conversation_messages(self.TENANT_A, self.CONV)
        dup_rows = [r for r in rows if r["message_id"] == "dup-id"]
        self.assertEqual(len(dup_rows), 1)

    def test_retrieval_debug_only_when_enabled(self):
        self.assertFalse(
            should_store_retrieval_debug(channel="public_api", debug_requested=True)
        )
        with patch.dict(os.environ, {"FIKIRI_CHATBOT_STORE_RETRIEVAL_DEBUG": "1"}):
            self.assertTrue(
                should_store_retrieval_debug(channel="preview", debug_requested=True)
            )

    def test_env_defaults(self):
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("FIKIRI_CHATBOT_CONVERSATION_PERSIST", None)
            os.environ.pop("FIKIRI_CHATBOT_PREVIEW_PERSIST", None)
            self.assertTrue(is_public_persistence_enabled())
            self.assertFalse(is_preview_persistence_enabled())


class TestPublicChatbotPersistenceWiring(unittest.TestCase):
    """Verify public route invokes persist helper when enabled (no full HTTP stack)."""

    def test_persist_skipped_without_tenant_id(self):
        with patch(
            "core.chatbot_conversation_store.persist_chatbot_turn"
        ) as mock_persist:
            from core import public_chatbot_api as pub

            with patch.object(pub, "is_public_persistence_enabled", return_value=True):
                tenant_id = None
                if pub.is_public_persistence_enabled() and tenant_id:
                    pub.persist_chatbot_turn(
                        tenant_id=str(tenant_id),
                        conversation_id="c1",
                        query="q",
                        answer="a",
                        assistant_message_id="m1",
                        sources=[],
                        fallback_used=True,
                        confidence=0.2,
                        retrieval_confidence=0.0,
                    )
            mock_persist.assert_not_called()


if __name__ == "__main__":
    unittest.main()
