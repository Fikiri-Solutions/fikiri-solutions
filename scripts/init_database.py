#!/usr/bin/env python3
"""
Initialize the application database (tables via db_optimizer).

Run from repository root:
  python3 scripts/init_database.py
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

repo_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(repo_root))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main() -> bool:
    try:
        from core.database_init import check_database_health, init_database

        logger.info("Checking database health...")
        check_database_health()
        logger.info("Running database initialization...")
        if init_database():
            logger.info("Database initialization completed successfully.")
            return True
        logger.error("Database initialization returned false.")
        return False
    except Exception as exc:
        logger.error("Database initialization failed: %s", exc)
        return False


if __name__ == "__main__":
    sys.exit(0 if main() else 1)
