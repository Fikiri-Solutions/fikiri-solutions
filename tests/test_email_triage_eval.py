import json
from pathlib import Path

from core.ai.email_triage_eval import (
    compute_eval_summary,
    generate_eval_report,
    load_eval_records,
)


def test_load_eval_records_and_summary(tmp_path: Path):
    dataset = tmp_path / "sample.jsonl"
    rows = [
        {
            "gold_intent": "lead_inquiry",
            "pred_intent": "lead_inquiry",
            "gold_urgency": "high",
            "pred_urgency": "high",
            "schema_valid": True,
            "unsafe_recommendation": False,
            "latency_ms": 1200,
            "cost_usd": 0.01,
        },
        {
            "gold_intent": "support_request",
            "pred_intent": "general_info",
            "gold_urgency": "medium",
            "pred_urgency": "low",
            "schema_valid": False,
            "unsafe_recommendation": True,
            "latency_ms": 6200,
            "cost_usd": 0.03,
        },
    ]
    dataset.write_text("\n".join(json.dumps(r) for r in rows), encoding="utf-8")

    records = load_eval_records(dataset)
    summary = compute_eval_summary(records)
    assert len(records) == 2
    assert summary["schema_valid_rate"] == 0.5
    assert summary["unsafe_recommendation_rate"] == 0.5
    assert summary["p95_latency_ms"] == 6200


def test_generate_eval_report_contains_launch_gates(tmp_path: Path):
    dataset = tmp_path / "passing.jsonl"
    row = {
        "gold_intent": "lead_inquiry",
        "pred_intent": "lead_inquiry",
        "gold_urgency": "high",
        "pred_urgency": "high",
        "schema_valid": True,
        "unsafe_recommendation": False,
        "latency_ms": 1000,
        "cost_usd": 0.001,
    }
    dataset.write_text("\n".join(json.dumps(row) for _ in range(5)), encoding="utf-8")
    records = load_eval_records(dataset)
    report = generate_eval_report(records, dataset_path=dataset)
    assert "launch_gates" in report
    assert report["launch_gates"]["all_passed"] is True

