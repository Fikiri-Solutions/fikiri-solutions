#!/usr/bin/env python3
"""
Slice A — schedule entry point for site-chat transcript retention.

Calls company_chatbot.transcript_store.purge_expired_transcripts().
Does not touch chatbot routing, turn caps, or message handling.

Usage:
  python3 scripts/purge_site_chat_transcripts.py
  python3 scripts/purge_site_chat_transcripts.py --dry-run
  python3 scripts/purge_site_chat_transcripts.py --batch-size 200

Requires:
  DATABASE_URL (production Postgres)
  FIKIRI_SITE_BOT_PERSIST_TRANSCRIPTS=1  (otherwise purge is a no-op)
  FIKIRI_SITE_BOT_TRANSCRIPT_RETENTION_DAYS (default 90)
"""

from __future__ import annotations

import argparse
import logging
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)


def _load_dotenv() -> None:
    try:
        from dotenv import load_dotenv

        load_dotenv(os.path.join(ROOT, ".env"), override=False)
    except ImportError:
        pass


_load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("purge_site_chat_transcripts")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Count expired sessions without deleting",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=500,
        help="Max sessions deleted per batch (default 500)",
    )
    args = parser.parse_args()

    from company_chatbot import config
    from company_chatbot.transcript_store import purge_expired_transcripts

    logger.info(
        "Starting site chat transcript purge dry_run=%s batch_size=%s persist=%s retention_days=%s",
        args.dry_run,
        args.batch_size,
        config.persist_transcripts_enabled(),
        config.transcript_retention_days(),
    )

    try:
        removed = purge_expired_transcripts(
            dry_run=args.dry_run,
            batch_size=args.batch_size,
        )
    except Exception:
        logger.exception("Site chat transcript purge failed")
        return 1

    action = "would_remove" if args.dry_run else "removed"
    logger.info("Site chat transcript purge finished %s=%s", action, removed)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
