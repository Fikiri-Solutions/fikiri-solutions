#!/usr/bin/env python3
"""Chatbot dev eval harness: cases, metrics, runner (no production changes)."""

import json
import os
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

os.environ.setdefault("FLASK_ENV", "test")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.chatbot_eval.chatbot_eval_cases import (
    ChatbotEvalCase,
    case_from_dict,
    load_eval_cases,
)
from core.chatbot_eval.chatbot_eval_metrics import (
    forbidden_keyword_hits,
    keyword_hit_rate,
    score_eval_case,
    source_grounding_coverage,
)
from core.chatbot_eval.chatbot_eval_runner import run_eval_case, run_eval_suite
from core.chatbot_response_service import ChatbotAnswerResult
from core.chatbot_retrieval import RetrievalResult


def _mock_retrieval_empty(_case, _cid):
    return RetrievalResult(
        sources=[],
        snippets=[],
        context_text="",
        retrieval_confidence=0.0,
        fallback_needed=True,
        source_count=0,
        retrieval_debug={
            "final_source_count": 0,
            "retrieval_confidence": 0.0,
            "fallback_needed": True,
            "latency_ms": 5,
        },
    )


def _mock_answer_fallback(case, retrieval, *, allow_llm, correlation_id):
    return ChatbotAnswerResult(
        answer="I am missing some context to answer that accurately.",
        confidence=0.2,
        llm_confidence=None,
        combined_confidence=0.2,
        fallback_used=True,
        escalation_recommended=True,
        llm_trace_id=None,
        retrieval_confidence=retrieval.retrieval_confidence,
    )


def _mock_retrieval_hours(_case, _cid):
    return RetrievalResult(
        sources=[{"type": "faq", "id": "faq_1", "question": "Hours?", "answer": "9-5"}],
        snippets=[],
        context_text="FAQ: Hours? — 9-5 weekdays.",
        retrieval_confidence=0.85,
        fallback_needed=False,
        source_count=1,
        retrieval_debug={
            "final_source_count": 1,
            "retrieval_confidence": 0.85,
            "fallback_needed": False,
            "latency_ms": 12,
        },
    )


def _mock_answer_hours(case, retrieval, *, allow_llm, correlation_id):
    return ChatbotAnswerResult(
        answer="We are open 9-5 on weekdays.",
        confidence=0.9,
        llm_confidence=0.9,
        combined_confidence=0.88,
        fallback_used=False,
        escalation_recommended=False,
        llm_trace_id="eval-trace",
        retrieval_confidence=retrieval.retrieval_confidence,
    )


class TestChatbotEvalMetrics(unittest.TestCase):
    def test_keyword_hit_rate_all_and_partial(self):
        self.assertEqual(keyword_hit_rate("open 9 to 5", ("9", "5")), 1.0)
        self.assertEqual(keyword_hit_rate("open nine", ("9", "5")), 0.0)

    def test_forbidden_keyword_detection(self):
        hits = forbidden_keyword_hits("The secret code is ABC", ("secret code",))
        self.assertEqual(hits, ["secret code"])

    def test_source_grounding_coverage(self):
        cov = source_grounding_coverage(
            "We are open weekdays nine to five",
            "FAQ: open weekdays nine to five",
        )
        self.assertGreater(cov, 0.5)

    def test_score_case_fails_on_forbidden_and_fallback_mismatch(self):
        case = ChatbotEvalCase(
            case_id="t1",
            tenant_id="1",
            query="q",
            expected_fallback=True,
            forbidden_keywords=("classified",),
        )
        metrics = score_eval_case(
            case,
            answer="This is classified information",
            context_text="",
            sources=[],
            retrieval_confidence=0.0,
            fallback_used=False,
            retrieval_fallback_needed=True,
            latency_ms=10,
        )
        self.assertFalse(metrics.passed)
        self.assertIn("forbidden_keywords", " ".join(metrics.failure_reasons))
        self.assertIn("expected_fallback", " ".join(metrics.failure_reasons))


class TestChatbotEvalRunner(unittest.TestCase):
    def test_fallback_detection_with_mocks(self):
        case = ChatbotEvalCase(
            case_id="fallback_case",
            tenant_id="1",
            query="unknown",
            expected_keywords=("context",),
            expected_fallback=True,
        )
        result = run_eval_case(
            case,
            retrieve_fn=_mock_retrieval_empty,
            answer_fn=_mock_answer_fallback,
        )
        self.assertTrue(result.metrics["fallback_used"])
        self.assertTrue(result.metrics["retrieval_fallback_needed"])
        self.assertEqual(result.metrics["retrieval_source_count"], 0)
        self.assertIn("final_source_count", result.retrieval_debug)

    def test_grounded_case_passes_with_mocks(self):
        case = ChatbotEvalCase(
            case_id="hours_case",
            tenant_id="t1",
            query="hours?",
            expected_keywords=("9", "5"),
            expected_source_ids=("faq_1",),
            expected_fallback=False,
        )
        result = run_eval_case(
            case,
            retrieve_fn=_mock_retrieval_hours,
            answer_fn=_mock_answer_hours,
        )
        self.assertTrue(result.passed)
        self.assertGreater(result.metrics["retrieval_confidence"], 0.5)
        self.assertGreater(result.metrics["source_grounding_coverage"], 0.0)

    def test_suite_pass_fail_counts(self):
        cases = [
            ChatbotEvalCase(
                case_id="b",
                tenant_id="1",
                query="q2",
                expected_fallback=True,
            ),
            ChatbotEvalCase(
                case_id="a",
                tenant_id="1",
                query="q1",
                expected_keywords=("missing_kw",),
            ),
        ]
        report = run_eval_suite(
            cases,
            retrieve_fn=_mock_retrieval_empty,
            answer_fn=_mock_answer_fallback,
        )
        self.assertEqual(report.cases_total, 2)
        self.assertEqual(report.cases_passed, 1)
        self.assertEqual(report.cases_failed, 1)
        self.assertIn("avg_latency_ms", report.summary_metrics)

    def test_deterministic_json_report(self):
        case = ChatbotEvalCase(
            case_id="det",
            tenant_id="1",
            query="q",
            expected_fallback=True,
            expected_keywords=("context",),
        )
        report1 = run_eval_suite(
            [case],
            retrieve_fn=_mock_retrieval_empty,
            answer_fn=_mock_answer_fallback,
        )
        report2 = run_eval_suite(
            [case],
            retrieve_fn=_mock_retrieval_empty,
            answer_fn=_mock_answer_fallback,
        )
        d1 = json.loads(report1.to_json())
        d2 = json.loads(report2.to_json())
        self.assertEqual(d1["cases_total"], d2["cases_total"])
        self.assertEqual(d1["results"][0]["case_id"], d2["results"][0]["case_id"])
        self.assertEqual(
            d1["results"][0]["metrics"]["keyword_hit_rate"],
            d2["results"][0]["metrics"]["keyword_hit_rate"],
        )
        self.assertNotEqual(d1["run_id"], d2["run_id"])

    def test_load_cases_from_json_file(self):
        payload = {
            "cases": [
                {
                    "case_id": "json_case",
                    "tenant_id": "99",
                    "query": "hello",
                    "expected_fallback": False,
                    "notes": "file load",
                }
            ]
        }
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
            json.dump(payload, f)
            path = f.name
        try:
            cases = load_eval_cases(path)
            self.assertEqual(len(cases), 1)
            self.assertEqual(cases[0].case_id, "json_case")
        finally:
            os.unlink(path)

    def test_case_from_dict_requires_ids(self):
        with self.assertRaises(ValueError):
            case_from_dict({"tenant_id": "1", "query": "x"})

    @patch("core.chatbot_usage_tracking.record_chatbot_ai_usage_if_needed")
    @patch("core.chatbot_usage_tracking.record_chatbot_billing_usage")
    @patch("core.chatbot_usage_tracking.check_chatbot_usage_allowed")
    @patch("core.chatbot_response_service.LLMRouter")
    def test_runner_does_not_hit_public_billing_by_default(
        self, mock_llm, mock_usage_check, mock_billing, mock_ai_usage
    ):
        case = ChatbotEvalCase(
            case_id="no_billing",
            tenant_id="1",
            query="test",
            expected_fallback=True,
            expected_keywords=("context",),
        )
        run_eval_case(
            case,
            allow_llm=False,
            retrieve_fn=_mock_retrieval_empty,
            answer_fn=_mock_answer_fallback,
        )
        mock_usage_check.assert_not_called()
        mock_billing.assert_not_called()
        mock_ai_usage.assert_not_called()
        mock_llm.assert_not_called()


class TestChatbotEvalLiveRetrieval(unittest.TestCase):
    @patch("core.chatbot_retrieval.get_feature_flags")
    @patch("core.chatbot_retrieval.get_vector_search")
    @patch("core.chatbot_retrieval._get_knowledge_base")
    @patch("core.chatbot_retrieval._get_faq_system")
    def test_unsynced_retrieval_metrics_included(
        self, mock_faq_fn, mock_kb_fn, mock_get_vs, mock_flags
    ):
        mock_flags.return_value.is_enabled.return_value = False
        mock_faq = Mock()
        mock_faq.search_faqs.return_value = Mock(success=True, matches=[])
        mock_faq_fn.return_value = mock_faq
        mock_kb = Mock()
        mock_kb.search.return_value = Mock(success=True, results=[])
        mock_kb_fn.return_value = mock_kb

        case = ChatbotEvalCase(
            case_id="live_empty",
            tenant_id="tenant_x",
            user_id=1,
            query="obscure topic",
            expected_fallback=True,
            expected_keywords=("context",),
        )
        result = run_eval_case(case, allow_llm=False)
        self.assertIn("retrieval_confidence", result.metrics)
        self.assertIn("latency_ms", result.metrics)
        self.assertTrue(result.metrics["retrieval_fallback_needed"])


class TestLiveEvalPreflight(unittest.TestCase):
    def test_preflight_runs_without_vector_when_flag_off(self):
        from core.chatbot_eval.live_preflight import preflight_live_eval_dependencies

        with patch(
            "core.chatbot_eval.live_preflight.live_eval_needs_vector_probe",
            return_value=False,
        ):
            checkpoints = preflight_live_eval_dependencies(timeout_sec=5.0)
        self.assertTrue(any("faq/kb" in c for c in checkpoints))

    def test_preflight_raises_on_vector_timeout(self):
        from core.chatbot_eval.live_preflight import (
            LiveEvalUnavailableError,
            preflight_live_eval_dependencies,
        )

        with patch(
            "core.chatbot_eval.live_preflight.live_eval_needs_vector_probe",
            return_value=True,
        ):
            with patch(
                "core.chatbot_eval.live_preflight._probe_vector_singleton",
                side_effect=LiveEvalUnavailableError("vector init timed out"),
            ):
                with self.assertRaises(LiveEvalUnavailableError):
                    preflight_live_eval_dependencies(
                        timeout_sec=0.1,
                        require_vector=True,
                    )

    def test_mock_mode_does_not_preflight(self):
        from core.chatbot_eval.chatbot_eval_runner import run_eval_suite
        from core.chatbot_eval.chatbot_eval_cases import ChatbotEvalCase

        case = ChatbotEvalCase(
            case_id="pf_skip",
            tenant_id="1",
            query="q",
            expected_fallback=True,
            expected_keywords=("context",),
        )
        with patch(
            "core.chatbot_eval.live_preflight.preflight_live_eval_dependencies"
        ) as mock_pf:
            run_eval_suite(
                [case],
                retrieve_fn=_mock_retrieval_empty,
                answer_fn=_mock_answer_fallback,
                preflight_live=False,
            )
            mock_pf.assert_not_called()


if __name__ == "__main__":
    unittest.main()
