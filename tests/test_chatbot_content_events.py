#!/usr/bin/env python3
"""Unit tests for chatbot content event helpers and FAQ tenant visibility."""

import os
import sys

os.environ.setdefault("FLASK_ENV", "test")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_content_fingerprint_empty():
    from core.chatbot_content_events import content_fingerprint_from_sources

    assert content_fingerprint_from_sources([]) == ""
    assert content_fingerprint_from_sources(None) == ""


def test_content_fingerprint_stable():
    from core.chatbot_content_events import content_fingerprint_from_sources

    sources = [
        {"type": "faq", "id": "f1"},
        {"type": "knowledge_base", "id": "d1"},
    ]
    a = content_fingerprint_from_sources(sources)
    b = content_fingerprint_from_sources(sources)
    assert len(a) == 40
    assert a == b


def test_persistence_disabled_under_pytest():
    from core import chatbot_content_events as mod

    assert mod._skip_side_effects() is True
    assert mod.persistence_enabled() is False
    assert mod.hydration_enabled() is False
    assert mod.kb_hydration_enabled() is False


def test_kb_tenant_scope_coerces_string_user_id():
    from core.knowledge_base_system import KnowledgeBaseSystem

    tu, tid = KnowledgeBaseSystem._tenant_scope_from_metadata(
        {"user_id": "42", "tenant_id": "tenant_x"}
    )
    assert tu == 42
    assert tid == "tenant_x"
    assert KnowledgeBaseSystem._tenant_scope_from_metadata({"user_id": True})[0] is None


def test_coerce_numeric_user_id():
    from core.chatbot_smart_faq_api import _coerce_numeric_user_id

    assert _coerce_numeric_user_id(None) is None
    assert _coerce_numeric_user_id(42) == 42
    assert _coerce_numeric_user_id(" 99 ") == 99
    assert _coerce_numeric_user_id("not_a_number") is None
    assert _coerce_numeric_user_id(True) is None


def test_faq_visible_for_tenant():
    from datetime import datetime

    from core.smart_faq_system import FAQCategory, FAQEntry, SmartFAQSystem

    faq = FAQEntry(
        id="t1",
        question="q",
        answer="a",
        category=FAQCategory.GENERAL,
        keywords=[],
        variations=[],
        user_id=42,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    assert SmartFAQSystem._faq_visible_for_tenant(faq, None) is False
    assert SmartFAQSystem._faq_visible_for_tenant(faq, 42) is True
    assert SmartFAQSystem._faq_visible_for_tenant(faq, 99) is False

    global_faq = FAQEntry(
        id="g1",
        question="q2",
        answer="a2",
        category=FAQCategory.GENERAL,
        keywords=[],
        variations=[],
        user_id=None,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    assert SmartFAQSystem._faq_visible_for_tenant(global_faq, 99) is True


def test_normalize_faq_category_string():
    from core.smart_faq_system import FAQCategory, _normalize_faq_category

    assert _normalize_faq_category("pricing") == FAQCategory.PRICING
    assert _normalize_faq_category("not_a_real_category") == FAQCategory.GENERAL
    assert _normalize_faq_category(FAQCategory.TECHNICAL) == FAQCategory.TECHNICAL
    assert _normalize_faq_category(123) == FAQCategory.GENERAL


def test_update_faq_ignores_privileged_keys():
    from core.smart_faq_system import FAQCategory, SmartFAQSystem

    s = SmartFAQSystem()
    fid = s.add_faq("Q", "A", FAQCategory.GENERAL, [], [], user_id=7)
    orig_id = s.faq_entries[fid].id
    assert s.update_faq(
        fid,
        {
            "id": "evil",
            "user_id": 99,
            "question": "Q2",
            "helpful_votes": 999,
        },
    )
    after = s.faq_entries[fid]
    assert after.id == orig_id
    assert after.user_id == 7
    assert after.question == "Q2"
    assert after.helpful_votes == 0


def test_add_faq_coerces_string_category():
    from core.smart_faq_system import FAQCategory, SmartFAQSystem

    s = SmartFAQSystem()
    fid = s.add_faq("Q", "A", "technical", [], [])
    assert s.faq_entries[fid].category == FAQCategory.TECHNICAL


def test_update_document_ignores_privileged_keys():
    from core.knowledge_base_system import DocumentType, KnowledgeBaseSystem

    kb = KnowledgeBaseSystem()
    did = kb.add_document("T", "C", document_type=DocumentType.ARTICLE)
    orig_id = kb.documents[did].id
    assert kb.update_document(
        did,
        {
            "id": "stolen",
            "view_count": 99999,
            "title": "T2",
        },
    )
    doc = kb.documents[did]
    assert doc.id == orig_id
    assert doc.view_count == 0
    assert doc.title == "T2"
