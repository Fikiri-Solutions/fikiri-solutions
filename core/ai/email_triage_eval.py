#!/usr/bin/env python3
"""Offline evaluator for inbound email triage launch gates."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence, Tuple

from core.ai.eval_thresholds import EmailTriageEvalThresholds


@dataclass(frozen=True)
class EmailTriageEvalRecord:
    gold_intent: str
    pred_intent: str
    gold_urgency: str
    pred_urgency: str
    schema_valid: bool
    unsafe_recommendation: bool
    latency_ms: float
    cost_usd: float


def _safe_str(value: Any) -> str:
    return str(value or "").strip().lower()


def _safe_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y"}
    return bool(value)


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def load_eval_records(dataset_path: Path) -> List[EmailTriageEvalRecord]:
    records: List[EmailTriageEvalRecord] = []
    with dataset_path.open("r", encoding="utf-8") as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if not line:
                continue
            row = json.loads(line)
            records.append(
                EmailTriageEvalRecord(
                    gold_intent=_safe_str(row.get("gold_intent")),
                    pred_intent=_safe_str(row.get("pred_intent")),
                    gold_urgency=_safe_str(row.get("gold_urgency")),
                    pred_urgency=_safe_str(row.get("pred_urgency")),
                    schema_valid=_safe_bool(row.get("schema_valid")),
                    unsafe_recommendation=_safe_bool(row.get("unsafe_recommendation")),
                    latency_ms=_safe_float(row.get("latency_ms"), 0.0),
                    cost_usd=_safe_float(row.get("cost_usd"), 0.0),
                )
            )
    return records


def _macro_f1(pairs: Sequence[Tuple[str, str]]) -> float:
    labels = sorted({gold for gold, _ in pairs if gold} | {pred for _, pred in pairs if pred})
    if not labels:
        return 0.0
    scores: List[float] = []
    for label in labels:
        tp = sum(1 for gold, pred in pairs if gold == label and pred == label)
        fp = sum(1 for gold, pred in pairs if gold != label and pred == label)
        fn = sum(1 for gold, pred in pairs if gold == label and pred != label)
        precision = tp / (tp + fp) if (tp + fp) else 0.0
        recall = tp / (tp + fn) if (tp + fn) else 0.0
        f1 = 0.0 if (precision + recall) == 0 else (2 * precision * recall) / (precision + recall)
        scores.append(f1)
    return sum(scores) / len(scores)


def _p95(values: Sequence[float]) -> float:
    if not values:
        return 0.0
    sorted_values = sorted(values)
    idx = int(round(0.95 * (len(sorted_values) - 1)))
    return sorted_values[idx]


def compute_eval_summary(records: Sequence[EmailTriageEvalRecord]) -> Dict[str, float]:
    total = len(records)
    if total == 0:
        return {
            "count": 0.0,
            "intent_macro_f1": 0.0,
            "urgency_macro_f1": 0.0,
            "schema_valid_rate": 0.0,
            "unsafe_recommendation_rate": 0.0,
            "p95_latency_ms": 0.0,
            "cost_per_request_usd": 0.0,
        }

    intent_pairs = [(r.gold_intent, r.pred_intent) for r in records]
    urgency_pairs = [(r.gold_urgency, r.pred_urgency) for r in records]
    schema_valid = sum(1 for r in records if r.schema_valid)
    unsafe = sum(1 for r in records if r.unsafe_recommendation)
    latencies = [r.latency_ms for r in records]
    total_cost = sum(r.cost_usd for r in records)

    return {
        "count": float(total),
        "intent_macro_f1": _macro_f1(intent_pairs),
        "urgency_macro_f1": _macro_f1(urgency_pairs),
        "schema_valid_rate": schema_valid / total,
        "unsafe_recommendation_rate": unsafe / total,
        "p95_latency_ms": _p95(latencies),
        "cost_per_request_usd": total_cost / total,
    }


def evaluate_launch_gates(
    summary: Dict[str, float],
    thresholds: EmailTriageEvalThresholds,
) -> Dict[str, Any]:
    checks = {
        "intent_macro_f1": summary["intent_macro_f1"] >= thresholds.intent_macro_f1_min,
        "urgency_macro_f1": summary["urgency_macro_f1"] >= thresholds.urgency_macro_f1_min,
        "schema_valid_rate": summary["schema_valid_rate"] >= thresholds.schema_valid_rate_min,
        "unsafe_recommendation_rate": summary["unsafe_recommendation_rate"] <= thresholds.unsafe_recommendation_rate_max,
        "p95_latency_ms": summary["p95_latency_ms"] <= thresholds.p95_latency_ms_max,
        "cost_per_request_usd": summary["cost_per_request_usd"] <= thresholds.cost_per_request_max,
    }
    failed_checks = [name for name, passed in checks.items() if not passed]
    return {
        "all_passed": len(failed_checks) == 0,
        "checks": checks,
        "failed_checks": failed_checks,
    }


def generate_eval_report(
    records: Sequence[EmailTriageEvalRecord],
    dataset_path: Path,
    thresholds: EmailTriageEvalThresholds | None = None,
) -> Dict[str, Any]:
    active_thresholds = thresholds or EmailTriageEvalThresholds()
    summary = compute_eval_summary(records)
    gates = evaluate_launch_gates(summary, active_thresholds)
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "dataset_path": str(dataset_path),
        "thresholds": active_thresholds.to_dict(),
        "summary": summary,
        "launch_gates": gates,
    }

