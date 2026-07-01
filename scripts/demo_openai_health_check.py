#!/usr/bin/env python3
"""
Pre-demo health checks for OpenAI-dependent features.

Never prints API keys or full error bodies that may contain secrets.
Exit 0 = safe to attempt Email AI / in-app verification; exit 1 = fix before demo.

Usage (from repo root):
  python3 scripts/demo_openai_health_check.py
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

try:
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env")
except ImportError:
    pass


def _env_truthy(name: str) -> bool:
    return os.getenv(name, "").strip().lower() in ("1", "true", "yes", "on")


def _check_openai_key() -> tuple[bool, str]:
    key = (os.getenv("OPENAI_API_KEY") or "").strip()
    if not key:
        return False, "OPENAI_API_KEY is not set"
    if key.startswith("your-") or key == "your-openai-api-key":
        return False, "OPENAI_API_KEY is still a placeholder"
    return True, "OPENAI_API_KEY is configured"


def _check_openai_api() -> tuple[bool, str]:
    key = (os.getenv("OPENAI_API_KEY") or "").strip()
    if not key:
        return False, "skipped (no key)"

    req = urllib.request.Request(
        "https://api.openai.com/v1/models",
        headers={"Authorization": f"Bearer {key}"},
        method="GET",
    )
    try:
        import ssl

        try:
            import certifi

            ssl_ctx = ssl.create_default_context(cafile=certifi.where())
        except ImportError:
            ssl_ctx = ssl.create_default_context()
        with urllib.request.urlopen(req, timeout=20, context=ssl_ctx) as resp:
            if resp.status != 200:
                return False, f"OpenAI API returned HTTP {resp.status}"
            return True, "OpenAI API reachable (GET /v1/models → 200)"
    except urllib.error.HTTPError as exc:
        code = exc.code
        hint = "billing or quota issue" if code in (402, 429) else "auth or config issue"
        if code == 401:
            hint = "invalid or revoked API key"
        return False, f"OpenAI API HTTP {code} ({hint})"
    except urllib.error.URLError as exc:
        return False, f"OpenAI API network error: {exc.reason}"


def _check_site_bot_mode() -> tuple[bool, str]:
    if _env_truthy("FIKIRI_SITE_BOT_LLM_POLISH"):
        return (
            False,
            "FIKIRI_SITE_BOT_LLM_POLISH is on — site chatbot may call OpenAI; disable for deterministic demo",
        )
    if _env_truthy("FIKIRI_SITE_BOT_TEST_MODE"):
        return True, "FIKIRI_SITE_BOT_TEST_MODE is on (OK for local; unset on production Render)"
    return True, "Site bot deterministic mode OK (LLM polish off)"


def main() -> int:
    print("Fikiri pre-demo AI health check")
    print("=" * 40)

    checks: list[tuple[str, bool, str]] = []

    ok, msg = _check_openai_key()
    checks.append(("OpenAI key", ok, msg))

    ok_api, msg_api = _check_openai_api()
    checks.append(("OpenAI API", ok_api, msg_api))

    ok_site, msg_site = _check_site_bot_mode()
    checks.append(("Site chatbot mode", ok_site, msg_site))

    all_ok = True
    for label, passed, detail in checks:
        status = "PASS" if passed else "FAIL"
        print(f"[{status}] {label}: {detail}")
        if not passed:
            all_ok = False

    print("=" * 40)
    if all_ok and ok_api:
        print("Email Analyze/Generate Reply: eligible for in-app verification (run manual /inbox test).")
        print("CRM: always safe. Site chatbot: safe if widget enabled on marketing pages.")
        print("/assistant: do not demo to clients.")
        return 0

    if all_ok and not ok_api:
        print("OpenAI key present but API check failed — do NOT demo Email AI or /assistant.")
        return 1

    print("Fix failures above before demoing OpenAI-dependent features.")
    print("CRM and deterministic site chatbot can still be demoed.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
