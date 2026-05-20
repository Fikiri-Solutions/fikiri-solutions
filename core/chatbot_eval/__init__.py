"""Local/dev chatbot evaluation harness (retrieval, grounding, fallback, hallucination)."""

from core.chatbot_eval.chatbot_eval_cases import ChatbotEvalCase, load_eval_cases
from core.chatbot_eval.chatbot_eval_metrics import CaseMetrics, score_eval_case
from core.chatbot_eval.chatbot_eval_runner import (
    EvalRunReport,
    run_eval_case,
    run_eval_suite,
)

__all__ = [
    "ChatbotEvalCase",
    "CaseMetrics",
    "EvalRunReport",
    "load_eval_cases",
    "run_eval_case",
    "run_eval_suite",
    "score_eval_case",
]
