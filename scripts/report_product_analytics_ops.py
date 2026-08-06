#!/usr/bin/env python3
"""Manual product-analytics ops report (read-only, no backfill).

Usage:
  PRODUCT_ANALYTICS_ENABLED=true \\
    python3 scripts/report_product_analytics_ops.py --tenant-id 42 --lookback-days 7

Does not mutate CRM, sync jobs, or analytics events.
"""

from __future__ import annotations

import argparse
import json
import os
import sys


def main() -> int:
    parser = argparse.ArgumentParser(description="Read-only analytics ops report")
    parser.add_argument("--tenant-id", type=int, required=True)
    parser.add_argument("--lookback-days", type=int, default=7, choices=[7, 30])
    parser.add_argument(
        "--no-reconcile",
        action="store_true",
        help="Health/counters only (skip lead/sync reconciliation)",
    )
    args = parser.parse_args()

    # Ensure repo root imports work when run as a script.
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if root not in sys.path:
        sys.path.insert(0, root)

    from core.product_analytics_ops import build_analytics_ops_report
    from core.product_analytics_store import ensure_product_analytics_tables

    try:
        ensure_product_analytics_tables()
    except Exception:
        pass

    report = build_analytics_ops_report(
        args.tenant_id,
        lookback_days=args.lookback_days,
        include_reconciliation=not args.no_reconcile,
    )
    print(json.dumps(report, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
