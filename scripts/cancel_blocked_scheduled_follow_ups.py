#!/usr/bin/env python3
"""
One-off: cancel scheduled_follow_ups whose lead email would be blocked by
should_skip_scheduled_follow_up_email (newsletter/noreply/reserved domains).

Does not send mail. Safe to run locally against data/fikiri.db when backend is stopped.

Usage:
  python3 scripts/cancel_blocked_scheduled_follow_ups.py
  python3 scripts/cancel_blocked_scheduled_follow_ups.py --dry-run
"""

from __future__ import annotations

import argparse
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)


def _load_dotenv() -> None:
    """Load .env before db_optimizer init (standalone scripts do not import app.py)."""
    try:
        from dotenv import load_dotenv

        load_dotenv(os.path.join(ROOT, ".env"), override=False)
    except ImportError:
        pass


_load_dotenv()

from core.database_optimization import db_optimizer
from core.workflow_followups import should_skip_scheduled_follow_up_email


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print rows that would be cancelled without updating",
    )
    args = parser.parse_args()

    print(f"Database backend: {db_optimizer.db_type}")
    if db_optimizer.db_type != "postgresql":
        print(
            "WARNING: Not using PostgreSQL. Set DATABASE_URL in .env (or export it) "
            "and ensure python-dotenv is installed, then re-run."
        )

    rows = db_optimizer.execute_query(
        """
        SELECT s.id, s.user_id, s.lead_id, l.email
        FROM scheduled_follow_ups s
        LEFT JOIN leads l ON l.id = s.lead_id
        WHERE s.status = 'scheduled' AND s.follow_up_type = 'email'
        ORDER BY s.id
        """
    )
    to_cancel = []
    for row in rows or []:
        email = (row.get("email") or "").strip()
        skip, reason = should_skip_scheduled_follow_up_email(email)
        if skip:
            to_cancel.append((row["id"], row["user_id"], row["lead_id"], reason, email))

    if not to_cancel:
        print("No blocked scheduled email follow-ups found.")
        return 0

    print(f"{'[dry-run] ' if args.dry_run else ''}Would cancel {len(to_cancel)} follow-up(s):")
    for fid, uid, lid, reason, email in to_cancel:
        domain = email.rsplit("@", 1)[-1] if "@" in email else ""
        print(f"  id={fid} user_id={uid} lead_id={lid} reason={reason} domain={domain}")

    if args.dry_run:
        return 0

    for fid, _, _, _, _ in to_cancel:
        db_optimizer.execute_query(
            "UPDATE scheduled_follow_ups SET status = 'cancelled' WHERE id = ? AND status = 'scheduled'",
            (fid,),
            fetch=False,
        )
    print(f"Cancelled {len(to_cancel)} scheduled follow-up(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
