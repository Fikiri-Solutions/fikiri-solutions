#!/usr/bin/env python3
"""
Local/dev chatbot evaluation harness CLI.

Does not modify production routes, prompts, or billing. Uses library pipeline:
retrieve_chatbot_context → generate_chatbot_answer (allow_llm off by default).

Example:
  python scripts/run_chatbot_eval.py \\
    --cases data/evals/chatbot/default_cases.json \\
    --output reports/chatbot_eval_latest.json
"""

from __future__ import annotations

import argparse
import os
import sys

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

os.environ.setdefault("FLASK_ENV", "test")
os.environ.setdefault("SKIP_HEAVY_DEP_CHECKS", "true")


def _mock_retrieve(case, _cid):
    from core.chatbot_retrieval import RetrievalResult

    if case.expected_fallback:
        return RetrievalResult(
            sources=[],
            snippets=[],
            context_text="",
            retrieval_confidence=0.0,
            fallback_needed=True,
            source_count=0,
            retrieval_debug={"final_source_count": 0, "fallback_needed": True},
        )
    return RetrievalResult(
        sources=[{"type": "faq", "id": "faq_1", "question": "Q", "answer": "9-5", "confidence": 0.9}],
        snippets=[],
        context_text="FAQ: open 9-5 weekdays.",
        retrieval_confidence=0.85,
        fallback_needed=False,
        source_count=1,
        retrieval_debug={"final_source_count": 1, "fallback_needed": False},
    )


def _mock_answer(case, retrieval, *, allow_llm, correlation_id):
    from core.chatbot_response_service import ChatbotAnswerResult

    if retrieval.fallback_needed:
        return ChatbotAnswerResult(
            answer="I am missing some context to answer that accurately.",
            confidence=0.2,
            llm_confidence=None,
            combined_confidence=0.2,
            fallback_used=True,
            escalation_recommended=True,
            llm_trace_id=None,
            retrieval_confidence=0.0,
        )
    return ChatbotAnswerResult(
        answer="We are open 9-5 on weekdays.",
        confidence=0.88,
        llm_confidence=None,
        combined_confidence=0.88,
        fallback_used=False,
        escalation_recommended=False,
        llm_trace_id=None,
        retrieval_confidence=retrieval.retrieval_confidence,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Run chatbot eval harness (dev/local)")
    parser.add_argument(
        "--cases",
        default="",
        help="Path to JSON cases file (default: built-in sample cases)",
    )
    parser.add_argument(
        "--output",
        default="reports/chatbot_eval_report.json",
        help="JSON report output path",
    )
    parser.add_argument(
        "--allow-llm",
        action="store_true",
        help="Call LLM router (non-deterministic; may record usage)",
    )
    parser.add_argument(
        "--mock",
        action="store_true",
        help="Use in-process mocks (fast; no FAQ/KB/vector/LLM; for smoke/CI)",
    )
    parser.add_argument(
        "--preflight-timeout",
        type=float,
        default=45.0,
        help="Live mode: max seconds for vector singleton init before fail-fast",
    )
    parser.add_argument(
        "--trace",
        action="store_true",
        help="Print preflight/import checkpoints (FIKIRI_EVAL_TRACE_IMPORTS=1)",
    )
    args = parser.parse_args()

    if args.trace:
        os.environ["FIKIRI_EVAL_TRACE_IMPORTS"] = "1"

    from core.chatbot_eval.chatbot_eval_cases import builtin_sample_cases, load_eval_cases
    from core.chatbot_eval.chatbot_eval_runner import run_eval_suite, write_eval_report
    from core.chatbot_eval.live_preflight import LiveEvalUnavailableError

    if args.cases:
        cases = load_eval_cases(args.cases)
    else:
        cases = builtin_sample_cases()

    retrieve_fn = _mock_retrieve if args.mock else None
    answer_fn = _mock_answer if args.mock else None
    try:
        report = run_eval_suite(
            cases,
            allow_llm=args.allow_llm and not args.mock,
            retrieve_fn=retrieve_fn,
            answer_fn=answer_fn,
            preflight_live=not args.mock,
            preflight_timeout_sec=args.preflight_timeout,
        )
    except LiveEvalUnavailableError as exc:
        print(f"Live eval unavailable: {exc}", file=sys.stderr)
        return 2
    out_path = write_eval_report(report, args.output)

    print(f"Wrote report: {out_path}")
    print(
        f"Passed {report.cases_passed}/{report.cases_total} "
        f"(failed {report.cases_failed})"
    )
    print(f"Summary: {report.summary_metrics}")

    return 0 if report.cases_failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
