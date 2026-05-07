#!/usr/bin/env python3
"""Run offline launch-gate evaluation for inbound email triage."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
import sys


SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.ai.email_triage_eval import generate_eval_report, load_eval_records


DEFAULT_DATASET = PROJECT_ROOT / "data" / "evals" / "email_triage" / "email-triage-v1.jsonl"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "data" / "evals" / "reports"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run email triage offline evaluation.")
    parser.add_argument(
        "--dataset",
        type=Path,
        default=DEFAULT_DATASET,
        help=f"JSONL dataset path (default: {DEFAULT_DATASET})",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help=f"Directory for evaluation reports (default: {DEFAULT_OUTPUT_DIR})",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    dataset_path = args.dataset
    output_dir = args.output_dir

    if not dataset_path.exists():
        print(f"Dataset not found: {dataset_path}", file=sys.stderr)
        return 1

    records = load_eval_records(dataset_path)
    report = generate_eval_report(records, dataset_path=dataset_path)

    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")
    report_path = output_dir / f"email_triage_eval_report_{timestamp}.json"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    summary = report["summary"]
    gates = report["launch_gates"]
    print(f"Report written: {report_path}")
    print(f"Records: {int(summary['count'])}")
    print(f"Intent macro F1: {summary['intent_macro_f1']:.4f}")
    print(f"Urgency macro F1: {summary['urgency_macro_f1']:.4f}")
    print(f"Schema valid rate: {summary['schema_valid_rate']:.4f}")
    print(f"Unsafe recommendation rate: {summary['unsafe_recommendation_rate']:.4f}")
    print(f"P95 latency ms: {summary['p95_latency_ms']:.2f}")
    print(f"Cost/request USD: {summary['cost_per_request_usd']:.5f}")
    print(f"Launch gates passed: {gates['all_passed']}")
    if gates["failed_checks"]:
        print(f"Failed checks: {', '.join(gates['failed_checks'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

