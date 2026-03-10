"""Contract test reporting for provider readiness."""

import json
import os
from pathlib import Path

import warnings

import pytest

# Load .env so Gmail/Stripe contract tests see creds (this conftest always runs for contract tests)
try:
    from dotenv import load_dotenv
    _root = Path(__file__).resolve().parent.parent.parent
    load_dotenv(_root / ".env", override=True)
except ImportError:
    pass

_RESULTS: dict[str, list[str]] = {}


def _provider_from_nodeid(nodeid: str) -> str | None:
    nodeid_lower = nodeid.lower()
    if "gmail" in nodeid_lower:
        return "gmail"
    if "stripe" in nodeid_lower:
        return "stripe"
    return None


def pytest_runtest_logreport(report):
    if report.when != "call":
        return

    provider = _provider_from_nodeid(report.nodeid)
    if not provider:
        return

    results = _RESULTS.setdefault(provider, [])
    results.append(report.outcome)


def pytest_sessionfinish(session, exitstatus):
    results = _RESULTS
    if not results:
        return

    summary = {}
    for provider, outcomes in results.items():
        if outcomes and all(o == "skipped" for o in outcomes):
            summary[provider] = {"configured": False, "contract_pass": None, "reason": "not_run"}
        elif outcomes and all(o == "passed" for o in outcomes):
            summary[provider] = {"configured": True, "contract_pass": True, "reason": "ok"}
        else:
            summary[provider] = {"configured": True, "contract_pass": False, "reason": "test_failed"}

    output_path = os.getenv("PROVIDER_CONTRACT_RESULTS", str(Path("reports") / "provider_contract.json"))
    try:
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        Path(output_path).write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    except Exception as exc:
        warnings.warn(f"Failed to write provider contract results: {exc}", RuntimeWarning)
