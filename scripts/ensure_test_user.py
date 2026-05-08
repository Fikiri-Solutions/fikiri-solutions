#!/usr/bin/env python3
"""
Ensure a deterministic local test user exists with known credentials.

Usage:
  python3 scripts/ensure_test_user.py
  TEST_USER_EMAIL=... TEST_USER_PASSWORD=... python3 scripts/ensure_test_user.py
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.database_optimization import db_optimizer
from core.user_auth import user_auth_manager


def main() -> int:
    email = os.getenv("TEST_USER_EMAIL", "test@example.com").strip().lower()
    password = os.getenv("TEST_USER_PASSWORD", "TestPassword123!")
    name = os.getenv("TEST_USER_NAME", "E2E Test User").strip() or "E2E Test User"
    business_name = os.getenv("TEST_USER_BUSINESS", "E2E Test").strip() or "E2E Test"

    existing = db_optimizer.execute_query(
        "SELECT id, metadata FROM users WHERE email = ? LIMIT 1",
        (email,),
    )

    if not existing:
        created = user_auth_manager.create_user(
            email=email,
            password=password,
            name=name,
            business_name=business_name,
        )
        if not created.get("success"):
            print(f"failed_create: {created.get('error', 'unknown')}")
            return 1
        print(f"created_user:{email}")
        return 0

    user_id = int(existing[0]["id"])
    metadata = existing[0].get("metadata") or "{}"
    try:
        metadata_obj = json.loads(metadata) if isinstance(metadata, str) else dict(metadata)
    except Exception:
        metadata_obj = {}

    password_hash, salt = user_auth_manager._hash_password(password)  # noqa: SLF001
    metadata_obj["salt"] = salt
    metadata_obj["password_salt"] = salt
    db_optimizer.execute_query(
        """
        UPDATE users
        SET password_hash = ?, metadata = ?, is_active = """ + db_optimizer.sql_true_literal() + """, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """,
        (password_hash, json.dumps(metadata_obj), user_id),
        fetch=False,
    )
    print(f"updated_password:{email}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
