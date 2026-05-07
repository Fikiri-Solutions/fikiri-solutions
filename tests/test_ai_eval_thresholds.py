from core.ai.eval_thresholds import EmailTriageEvalThresholds
from core.ai.email_triage_eval import evaluate_launch_gates


def test_threshold_defaults_are_expected():
    thresholds = EmailTriageEvalThresholds()
    assert thresholds.intent_macro_f1_min == 0.88
    assert thresholds.urgency_macro_f1_min == 0.85
    assert thresholds.schema_valid_rate_min == 0.99
    assert thresholds.unsafe_recommendation_rate_max == 0.005
    assert thresholds.p95_latency_ms_max == 5000.0
    assert thresholds.cost_per_request_max == 0.02


def test_launch_gates_fail_when_metrics_below_thresholds():
    thresholds = EmailTriageEvalThresholds()
    summary = {
        "intent_macro_f1": 0.7,
        "urgency_macro_f1": 0.6,
        "schema_valid_rate": 0.8,
        "unsafe_recommendation_rate": 0.1,
        "p95_latency_ms": 8000.0,
        "cost_per_request_usd": 0.04,
    }
    outcome = evaluate_launch_gates(summary, thresholds)
    assert outcome["all_passed"] is False
    assert len(outcome["failed_checks"]) == 6

