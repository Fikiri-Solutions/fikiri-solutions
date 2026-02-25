#!/usr/bin/env python3
"""
Dump top N incorrect/needs-review questions from the latest needs_review JSONL for human review.

Reads: data/evals/needs_review_*.jsonl (latest by mtime)
Writes: data/evals/incorrect_for_review_{timestamp}.md

Usage:
  python scripts/dump_incorrect_for_review.py [evals_dir] [limit]
  python scripts/dump_incorrect_for_review.py
  python scripts/dump_incorrect_for_review.py data/evals 50
"""

import json
import os
import sys
from datetime import datetime, timezone
from glob import glob
from typing import Optional

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
DEFAULT_EVALS_DIR = os.path.join(PROJECT_ROOT, "data", "evals")
DEFAULT_LIMIT = 50


def load_jsonl(path: str) -> list:
    out = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            out.append(json.loads(line))
    return out


def latest_file(evals_dir: str, prefix: str) -> Optional[str]:
    pattern = os.path.join(evals_dir, f"{prefix}_*.jsonl")
    paths = glob(pattern)
    paths.sort(key=os.path.getmtime, reverse=True)
    return paths[0] if paths else None


def main():
    evals_dir = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_EVALS_DIR
    try:
        limit = int(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_LIMIT
    except ValueError:
        limit = DEFAULT_LIMIT

    if not os.path.isdir(evals_dir):
        print(f"Evals dir not found: {evals_dir}", file=sys.stderr)
        sys.exit(1)

    path = latest_file(evals_dir, "needs_review")
    if not path:
        print("No needs_review_*.jsonl found. Run scripts/build_eval_sets.py first.", file=sys.stderr)
        sys.exit(1)

    records = load_jsonl(path)
    top = records[:limit]

    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%S")
    out_path = os.path.join(evals_dir, f"incorrect_for_review_{ts}.md")

    lines = [
        "# Top incorrect / needs-review questions for RAG improvement",
        "",
        f"Generated: {ts}",
        f"Source: {os.path.basename(path)}",
        f"Showing up to {len(top)} of {len(records)} needs_review records.",
        "",
        "| # | Question | Answer (snippet) | Rating | ID |",
        "|---|----------|------------------|--------|-----|",
    ]
    for i, r in enumerate(top, 1):
        q = (r.get("question") or "").strip().replace("|", "\\|").replace("\n", " ")
        a = (r.get("answer") or "").strip().replace("|", "\\|").replace("\n", " ")[:200]
        if len((r.get("answer") or "")) > 200:
            a += "..."
        rating = (r.get("rating") or "").strip()
        row_id = r.get("id", "")
        lines.append(f"| {i} | {q} | {a} | {rating} | {row_id} |")

    lines.extend(["", ""])
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print("Wrote", out_path)
    print(f"  {len(top)} questions (of {len(records)} needs_review)")


if __name__ == "__main__":
    main()
