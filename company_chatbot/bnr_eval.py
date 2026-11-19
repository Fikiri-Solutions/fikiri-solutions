"""Business-need recognition benchmark runner (dev vs holdout)."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

import yaml

from company_chatbot.business_needs import detect_business_needs
from company_chatbot.orchestrator import clear_sessions_for_tests, handle_message, start_session
from company_chatbot.retrieval import clear_kb_cache_for_tests, retrieve

DEFAULT_SUITE = Path(__file__).resolve().parents[1] / "tests" / "company_chatbot_bnr_benchmark.yaml"


@dataclass
class BnrCaseResult:
    case_id: str
    need_id: str
    style: str
    split: str
    auto_pass: bool
    mode: str
    fallback: bool
    need_hit: bool
    retrieved_ids: List[str] = field(default_factory=list)
    source_ids: List[str] = field(default_factory=list)
    response: str = ""
    failures: List[str] = field(default_factory=list)
    unsupported_claim: bool = False


def load_bnr_cases(path: Path | None = None, *, split: Optional[str] = None) -> List[Dict[str, Any]]:
    data = yaml.safe_load((path or DEFAULT_SUITE).read_text(encoding="utf-8"))
    cases = data.get("cases") or []
    if split:
        cases = [c for c in cases if c.get("split") == split]
    return cases


def _source_ids(result) -> List[str]:
    ids = []
    for src in result.sources or []:
        if isinstance(src, dict):
            chunk_id = src.get("chunk_id") or src.get("id")
            if chunk_id:
                ids.append(str(chunk_id))
    return ids


def run_bnr_case(case: Dict[str, Any]) -> BnrCaseResult:
    clear_sessions_for_tests()
    session_id = start_session().session_id
    expected = case.get("expected") or {}
    turns = case.get("turns") or []
    previous = None
    last = None
    retrieved_ids: List[str] = []
    for turn in turns:
        user = (turn.get("user") or "").strip()
        retrieved_ids = [c.id for c in retrieve(user, top_k=3, previous_query=previous).chunks]
        last = handle_message(session_id, user)
        previous = user
    assert last is not None

    need_expected = list(expected.get("need_ids_any") or [case.get("need_id")])
    detected = detect_business_needs(turns[-1]["user"] if turns else "")
    need_hit = bool(set(need_expected) & set(detected.need_ids))

    mode = last.mode
    fallback = mode == "fallback"
    response = last.response or ""
    failures: List[str] = []
    modes_allowed = list(expected.get("modes_allowed") or [])
    if modes_allowed and mode not in modes_allowed:
        if not (expected.get("clarification_or_limitation_ok") and fallback):
            failures.append("MODE")
    if expected.get("fallback_forbidden") and fallback:
        failures.append("FALLBACK")
    style = str(case.get("style") or "")
    if (
        need_expected
        and not need_hit
        and not case.get("contrast")
        and style not in {"ambiguous", "contrast"}
    ):
        # Hard need miss only when we also failed to produce a useful mode.
        if fallback or mode not in ("answer", "explore_fit", "workflow_audit", "consulting"):
            failures.append("NEED_MISS")

    forbidden = list(expected.get("forbidden_substrings") or [])
    unsupported = any(f.lower() in response.lower() for f in forbidden if f)
    if unsupported:
        failures.append("UNSUPPORTED_CLAIM")

    auto_pass = len(failures) == 0
    return BnrCaseResult(
        case_id=str(case.get("id")),
        need_id=str(case.get("need_id")),
        style=str(case.get("style")),
        split=str(case.get("split")),
        auto_pass=auto_pass,
        mode=mode,
        fallback=fallback,
        need_hit=need_hit,
        retrieved_ids=retrieved_ids,
        source_ids=_source_ids(last),
        response=response,
        failures=failures,
        unsupported_claim=unsupported,
    )


def run_bnr_suite(path: Path | None = None, *, split: Optional[str] = None) -> List[BnrCaseResult]:
    clear_kb_cache_for_tests()
    return [run_bnr_case(case) for case in load_bnr_cases(path, split=split)]


def summarize_bnr(results: Sequence[BnrCaseResult]) -> Dict[str, Any]:
    n = len(results) or 1
    by_need: Dict[str, Dict[str, float]] = {}
    for result in results:
        bucket = by_need.setdefault(result.need_id, {"n": 0, "pass": 0, "need_hit": 0, "fallback": 0})
        bucket["n"] += 1
        bucket["pass"] += 1 if result.auto_pass else 0
        bucket["need_hit"] += 1 if result.need_hit else 0
        bucket["fallback"] += 1 if result.fallback else 0
    return {
        "cases": len(results),
        "auto_pass_rate": sum(1 for r in results if r.auto_pass) / n,
        "need_recognition_rate": sum(1 for r in results if r.need_hit) / n,
        "fallback_rate": sum(1 for r in results if r.fallback) / n,
        "unsupported_claim_rate": sum(1 for r in results if r.unsupported_claim) / n,
        "by_need": {
            key: {
                "n": val["n"],
                "auto_pass_rate": val["pass"] / max(val["n"], 1),
                "need_recognition_rate": val["need_hit"] / max(val["n"], 1),
                "fallback_rate": val["fallback"] / max(val["n"], 1),
            }
            for key, val in by_need.items()
        },
        "failures": [r for r in results if not r.auto_pass],
    }


def format_bnr_report(dev: Dict[str, Any], holdout: Dict[str, Any] | None = None) -> str:
    lines = [
        "=== BNR Benchmark Report ===",
        f"DEV auto_pass={dev['auto_pass_rate']:.1%} need_recog={dev['need_recognition_rate']:.1%} "
        f"fallback={dev['fallback_rate']:.1%} unsupported={dev['unsupported_claim_rate']:.1%} "
        f"n={dev['cases']}",
    ]
    if holdout:
        lines.append(
            f"HOLDOUT auto_pass={holdout['auto_pass_rate']:.1%} "
            f"need_recog={holdout['need_recognition_rate']:.1%} "
            f"fallback={holdout['fallback_rate']:.1%} unsupported={holdout['unsupported_claim_rate']:.1%} "
            f"n={holdout['cases']}"
        )
    lines.append("DEV failures (first 20):")
    for result in (dev.get("failures") or [])[:20]:
        lines.append(
            f"  - {result.case_id} mode={result.mode} fails={result.failures} "
            f"need_hit={result.need_hit} q_resp={result.response[:80]!r}"
        )
    return "\n".join(lines) + "\n"
