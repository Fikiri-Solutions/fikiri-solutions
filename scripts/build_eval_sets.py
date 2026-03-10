#!/usr/bin/env python3
"""
Build evaluation datasets from chatbot_feedback table.

Outputs (JSONL under data/evals/, timestamped):
  - gold:          rating = correct
  - needs_review:  rating in (somewhat_incorrect, incorrect)
  - ambiguous:     rating = somewhat_correct

Usage:
  python scripts/build_eval_sets.py

Env:
  Optional: load from .env via dotenv. DB path from core.database_optimization / app config.
"""

import json
import os
import sys
from datetime import datetime, timezone

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
EVALS_DIR = os.path.join(PROJECT_ROOT, "data", "evals")


def main():
    os.makedirs(EVALS_DIR, exist_ok=True)
    sys.path.insert(0, PROJECT_ROOT)
    os.environ.setdefault("FLASK_ENV", "development")

    from core.database_optimization import db_optimizer

    if not db_optimizer.table_exists("chatbot_feedback"):
        print("Table chatbot_feedback not found. Run the app once to create it.", file=sys.stderr)
        sys.exit(1)

    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%S")
    all_rows = db_optimizer.execute_query(
        """SELECT id, user_id, session_id, question, answer, retrieved_doc_ids,
                  rating, created_at, metadata, prompt_version, retriever_version
           FROM chatbot_feedback
           ORDER BY created_at ASC"""
    )

    def row_to_record(r):
        doc_ids = r.get("retrieved_doc_ids")
        if isinstance(doc_ids, str):
            try:
                doc_ids = json.loads(doc_ids) if doc_ids else []
            except json.JSONDecodeError:
                doc_ids = []
        meta = r.get("metadata")
        if isinstance(meta, str) and meta:
            try:
                meta = json.loads(meta)
            except json.JSONDecodeError:
                meta = None
        return {
            "id": r.get("id"),
            "user_id": r.get("user_id"),
            "session_id": r.get("session_id"),
            "question": (r.get("question") or "").strip(),
            "answer": (r.get("answer") or "").strip(),
            "retrieved_doc_ids": doc_ids if isinstance(doc_ids, list) else [],
            "rating": (r.get("rating") or "").strip(),
            "created_at": r.get("created_at"),
            "metadata": meta,
            "prompt_version": r.get("prompt_version"),
            "retriever_version": r.get("retriever_version"),
        }

    gold = []
    needs_review = []
    ambiguous = []

    for r in all_rows or []:
        rec = row_to_record(r)
        rating = (rec.get("rating") or "").lower()
        if rating == "correct":
            gold.append(rec)
        elif rating in ("somewhat_incorrect", "incorrect"):
            needs_review.append(rec)
        elif rating == "somewhat_correct":
            ambiguous.append(rec)

    def write_jsonl(records, name):
        path = os.path.join(EVALS_DIR, f"{name}_{ts}.jsonl")
        with open(path, "w", encoding="utf-8") as f:
            for rec in records:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        print(f"  {path} ({len(records)} records)")
        return path

    print("Writing eval sets to", EVALS_DIR)
    write_jsonl(gold, "gold")
    write_jsonl(needs_review, "needs_review")
    write_jsonl(ambiguous, "ambiguous")
    print("Done.")


if __name__ == "__main__":
    main()
