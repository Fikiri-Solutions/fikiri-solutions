#!/usr/bin/env python3
"""
Run evaluation over chatbot eval sets (gold, needs_review, ambiguous JSONL).

Uses heuristic metrics only (no Ragas dependency):
  - Retrieval: recall@1 (pct with >=1 citation), recall@3, avg retrieved per query, % with citations
  - Answer quality: avg answer length, correct rate (from set composition)
  - Placeholders: MRR, groundedness (require labeled data or Ragas)

Output: data/evals/report_{timestamp}.json

Usage:
  python scripts/run_eval.py [data/evals]
  python scripts/run_eval.py

Optional: set RAGAS_AVAILABLE=1 and install ragas for future groundedness/faithfulness.
"""

import json
import os
import sys
from datetime import datetime, timezone
from glob import glob

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
DEFAULT_EVALS_DIR = os.path.join(PROJECT_ROOT, "data", "evals")


def load_jsonl(path: str) -> list:
    out = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            out.append(json.loads(line))
    return out


def latest_files(evals_dir: str, prefix: str) -> list:
    """Return paths for prefix_*.jsonl sorted by mtime descending."""
    pattern = os.path.join(evals_dir, f"{prefix}_*.jsonl")
    paths = glob(pattern)
    paths.sort(key=os.path.getmtime, reverse=True)
    return paths


def compute_metrics(records: list) -> dict:
    if not records:
        return {
            "n": 0,
            "pct_with_citations": 0.0,
            "recall_at_1": 0.0,
            "recall_at_3": 0.0,
            "avg_retrieved_per_query": 0.0,
            "avg_answer_length": 0.0,
            "avg_top_k_similarity": None,
        }
    n = len(records)
    with_citations = sum(1 for r in records if (r.get("retrieved_doc_ids") or []))
    lengths = [len((r.get("answer") or "").strip()) for r in records]
    retrieved_counts = [len(r.get("retrieved_doc_ids") or []) for r in records]
    recall_at_1 = (sum(1 for c in retrieved_counts if c >= 1) / n * 100) if n else 0.0
    recall_at_3 = (sum(1 for c in retrieved_counts if c >= 3) / n * 100) if n else 0.0
    return {
        "n": n,
        "pct_with_citations": round(with_citations / n * 100, 2) if n else 0.0,
        "recall_at_1": round(recall_at_1, 2),
        "recall_at_3": round(recall_at_3, 2),
        "avg_retrieved_per_query": round(sum(retrieved_counts) / n, 2) if n else 0.0,
        "avg_answer_length": round(sum(lengths) / n, 1) if n else 0.0,
        "avg_top_k_similarity": None,
    }


def main():
    evals_dir = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_EVALS_DIR
    if not os.path.isdir(evals_dir):
        print(f"Evals dir not found: {evals_dir}", file=sys.stderr)
        sys.exit(1)

    gold_paths = latest_files(evals_dir, "gold")
    needs_review_paths = latest_files(evals_dir, "needs_review")
    ambiguous_paths = latest_files(evals_dir, "ambiguous")

    gold = load_jsonl(gold_paths[0]) if gold_paths else []
    needs_review = load_jsonl(needs_review_paths[0]) if needs_review_paths else []
    ambiguous = load_jsonl(ambiguous_paths[0]) if ambiguous_paths else []

    all_records = gold + needs_review + ambiguous
    total = len(all_records)

    metrics_gold = compute_metrics(gold)
    metrics_needs_review = compute_metrics(needs_review)
    metrics_ambiguous = compute_metrics(ambiguous)
    metrics_overall = compute_metrics(all_records)

    correct_rate = (len(gold) / total * 100) if total else 0.0
    needs_review_rate = (len(needs_review) / total * 100) if total else 0.0
    ambiguous_rate = (len(ambiguous) / total * 100) if total else 0.0

    report = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "evals_dir": os.path.abspath(evals_dir),
        "sources": {
            "gold": gold_paths[0] if gold_paths else None,
            "needs_review": needs_review_paths[0] if needs_review_paths else None,
            "ambiguous": ambiguous_paths[0] if ambiguous_paths else None,
        },
        "counts": {
            "gold": len(gold),
            "needs_review": len(needs_review),
            "ambiguous": len(ambiguous),
            "total": total,
        },
        "retrieval": {
            "recall_at_1": metrics_overall["recall_at_1"],
            "recall_at_3": metrics_overall["recall_at_3"],
            "pct_with_citations": metrics_overall["pct_with_citations"],
            "avg_retrieved_per_query": metrics_overall["avg_retrieved_per_query"],
            "mrr": None,
            "note": "MRR requires ground-truth relevant doc ids per query; use Ragas or labeled set for full retrieval metrics.",
        },
        "answer_quality": {
            "avg_answer_length": metrics_overall["avg_answer_length"],
            "pct_with_citations": metrics_overall["pct_with_citations"],
            "correct_rate_pct": round(correct_rate, 2),
            "needs_review_rate_pct": round(needs_review_rate, 2),
            "ambiguous_rate_pct": round(ambiguous_rate, 2),
            "groundedness": None,
            "relevance": None,
            "note": "groundedness/relevance require Ragas or LLM-as-judge.",
        },
        "by_set": {
            "gold": metrics_gold,
            "needs_review": metrics_needs_review,
            "ambiguous": metrics_ambiguous,
        },
    }

    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%S")
    report_path = os.path.join(evals_dir, f"report_{ts}.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print("Eval report written to:", report_path)
    print("  total examples:", total)
    print("  retrieval recall@1:", report["retrieval"]["recall_at_1"], "%")
    print("  retrieval recall@3:", report["retrieval"]["recall_at_3"], "%")
    print("  % with citations:", report["retrieval"]["pct_with_citations"], "%")
    print("  avg answer length:", report["answer_quality"]["avg_answer_length"])
    print("  correct rate:", report["answer_quality"]["correct_rate_pct"], "%")


if __name__ == "__main__":
    main()
