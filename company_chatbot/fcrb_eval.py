"""FCRB pilot runner — grades real orchestrator responses (no production changes)."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

import yaml

from company_chatbot.orchestrator import clear_sessions_for_tests, handle_message, start_session
from company_chatbot.retrieval import clear_kb_cache_for_tests, retrieve

FAILURE_RETRIEVAL = "RETRIEVAL_FAILURE"
FAILURE_INTENT = "INTENT_CLASSIFICATION_FAILURE"
FAILURE_ROUTING_FALLBACK = "ROUTING_FALLBACK_FAILURE"
FAILURE_RESPONSE = "RESPONSE_COMPOSITION_FAILURE"
FAILURE_MISSING_KNOWLEDGE = "MISSING_KNOWLEDGE"
FAILURE_LANGUAGE = "LANGUAGE_COMPREHENSION_FAILURE"
FAILURE_HANDOFF = "INCORRECT_HANDOFF"
FAILURE_UNSUPPORTED_CLAIM = "UNSUPPORTED_CLAIM"

DEFAULT_SUITE = Path(__file__).resolve().parents[1] / "tests" / "company_chatbot_fcrb_pilot.yaml"


@dataclass
class FcrbCaseResult:
    case_id: str
    category: str
    language_category: str
    review_status: str
    auto_pass: bool
    needs_human_review: bool
    failures: List[str] = field(default_factory=list)
    mode: str = ""
    fallback: bool = False
    grounded: bool = False
    source_ids: List[str] = field(default_factory=list)
    retrieved_ids: List[str] = field(default_factory=list)
    response: str = ""
    handoff_applicable: bool = False
    handoff_secondary: Optional[str] = None
    evidence: Dict[str, Any] = field(default_factory=dict)


def load_fcrb_cases(path: Path | None = None) -> List[Dict[str, Any]]:
    data = yaml.safe_load((path or DEFAULT_SUITE).read_text(encoding="utf-8"))
    cases = data.get("cases") or []
    if not isinstance(cases, list):
        raise ValueError("FCRB suite missing cases list")
    return cases


def _source_ids(result) -> List[str]:
    ids: List[str] = []
    for src in result.sources or []:
        if isinstance(src, dict):
            chunk_id = src.get("chunk_id") or src.get("id")
            if chunk_id:
                ids.append(str(chunk_id))
    return ids


def _contains_any(text: str, needles: Sequence[str]) -> bool:
    lowered = (text or "").lower()
    return any(n.lower() in lowered for n in needles if n)


def _contains_any_forbidden(text: str, needles: Sequence[str]) -> List[str]:
    lowered = (text or "").lower()
    return [n for n in needles if n and n.lower() in lowered]


def classify_and_grade(case: Dict[str, Any], *, last_result, retrieved_ids: List[str]) -> FcrbCaseResult:
    expected = case.get("expected") or {}
    mode = last_result.mode
    response = last_result.response or ""
    source_ids = _source_ids(last_result)
    fallback = mode == "fallback"
    handoff = last_result.handoff
    category = str(case.get("category") or "")
    language_category = str(case.get("language_category") or "")
    provenance = case.get("provenance") or {}
    review_status = str(provenance.get("review_status") or "draft_unvalidated")

    failures: List[str] = []
    modes_allowed = list(expected.get("modes_allowed") or [])
    modes_forbidden = list(expected.get("modes_forbidden") or [])
    fallback_forbidden = bool(expected.get("fallback_forbidden"))
    clarification_expected = bool(expected.get("clarification_expected"))
    clarification_or_limitation_ok = bool(expected.get("clarification_or_limitation_ok"))
    handoff_expected = bool(expected.get("handoff_expected"))

    # Intent / mode
    if modes_allowed and mode not in modes_allowed:
        # Soft multilingual / clarification cases may allow fallback via clarification_or_limitation_ok
        if not (clarification_or_limitation_ok and fallback):
            failures.append(FAILURE_INTENT)
    if modes_forbidden and mode in modes_forbidden:
        failures.append(FAILURE_INTENT)

    if fallback_forbidden and fallback:
        failures.append(FAILURE_ROUTING_FALLBACK)
        # Known pattern: retrieval hit + fallback
        acceptable = set(expected.get("acceptable_source_ids_any") or [])
        if acceptable & set(retrieved_ids):
            failures.append(FAILURE_ROUTING_FALLBACK + ":retrieved_ok_still_fallback")

    if category in {"typo_slang", "non_native_dialect"} and fallback and fallback_forbidden:
        failures.append(FAILURE_LANGUAGE)

    # Retrieval (informational when sources empty — also check peek retrieve)
    acceptable = list(expected.get("acceptable_source_ids_any") or [])
    forbidden_sources = set(expected.get("forbidden_source_ids") or [])
    check_pool = source_ids or retrieved_ids
    if acceptable and not (set(acceptable) & set(check_pool)):
        if not check_pool:
            failures.append(FAILURE_MISSING_KNOWLEDGE)
        else:
            failures.append(FAILURE_RETRIEVAL)
    if forbidden_sources & set(source_ids[:3]):
        failures.append(FAILURE_RETRIEVAL + ":forbidden_source")

    # Response composition
    required_any = list(expected.get("required_substrings_any") or [])
    if required_any and mode != "fallback" and not _contains_any(response, required_any):
        failures.append(FAILURE_RESPONSE)
    forbidden_hits = _contains_any_forbidden(response, list(expected.get("forbidden_substrings") or []))
    if forbidden_hits:
        failures.append(FAILURE_UNSUPPORTED_CLAIM)

    # Clarification heuristic: fallback or question mark / "not sure" / "tell me more"
    clarificationish = fallback or bool(
        re.search(
            r"\b(not sure|could you|can you tell|which|what do you mean|clarify)\b",
            response,
            re.I,
        )
    )
    if clarification_expected and not clarificationish:
        failures.append(FAILURE_RESPONSE + ":expected_clarification")

    # Handoff
    if handoff_expected:
        if not handoff.applicable:
            failures.append(FAILURE_HANDOFF)
        secondary_any = list(expected.get("handoff_secondary_any") or [])
        if secondary_any and (handoff.secondary or "") not in secondary_any:
            failures.append(FAILURE_HANDOFF)

    # Deduplicate failure labels while preserving order
    seen = set()
    uniq_failures = []
    for item in failures:
        base = item.split(":")[0]
        key = item
        if key in seen:
            continue
        seen.add(key)
        uniq_failures.append(item)

    # Auto-pass is strict deterministic checks only; human_review always flagged when declared
    needs_human = bool(expected.get("human_review"))
    auto_pass = len(uniq_failures) == 0

    # Soft multilingual: if clarification_or_limitation_ok and fallback, treat as needs human not auto fail
    # (unless unsupported claims). Already may have INTENT failure — clear soft path:
    if clarification_or_limitation_ok and fallback and FAILURE_UNSUPPORTED_CLAIM not in "".join(uniq_failures):
        uniq_failures = [f for f in uniq_failures if not f.startswith(FAILURE_INTENT)]
        # Keep as needs human; auto_pass only if no hard failures remain
        auto_pass = len(uniq_failures) == 0
        needs_human = True

    return FcrbCaseResult(
        case_id=str(case.get("id")),
        category=category,
        language_category=language_category,
        review_status=review_status,
        auto_pass=auto_pass,
        needs_human_review=needs_human,
        failures=uniq_failures,
        mode=mode,
        fallback=fallback,
        grounded=bool(last_result.grounded),
        source_ids=source_ids,
        retrieved_ids=retrieved_ids,
        response=response,
        handoff_applicable=bool(handoff.applicable),
        handoff_secondary=handoff.secondary,
        evidence={
            "intent": expected.get("intent"),
            "turns": case.get("turns"),
            "notes": expected.get("notes") or case.get("notes"),
            "retrieved_ok_still_fallback": any(
                "retrieved_ok_still_fallback" in f for f in uniq_failures
            ),
        },
    )


def run_fcrb_case(case: Dict[str, Any]) -> FcrbCaseResult:
    clear_sessions_for_tests()
    started = start_session()
    session_id = started.session_id
    last_result = None
    retrieved_ids: List[str] = []
    turns = case.get("turns") or []
    previous = None
    for turn in turns:
        user = (turn.get("user") or "").strip()
        retrieved_ids = [c.id for c in retrieve(user, top_k=3, previous_query=previous).chunks]
        last_result = handle_message(session_id, user)
        previous = user
    assert last_result is not None
    return classify_and_grade(case, last_result=last_result, retrieved_ids=retrieved_ids)


def run_fcrb_suite(path: Path | None = None) -> List[FcrbCaseResult]:
    clear_kb_cache_for_tests()
    cases = load_fcrb_cases(path)
    return [run_fcrb_case(case) for case in cases]


def summarize_fcrb(results: Sequence[FcrbCaseResult]) -> Dict[str, Any]:
    n = len(results) or 1
    auto_pass = sum(1 for r in results if r.auto_pass)
    fallbacks = sum(1 for r in results if r.fallback)
    by_cat: Dict[str, Dict[str, float]] = {}
    by_lang: Dict[str, Dict[str, float]] = {}
    failure_counts: Dict[str, int] = {}

    def _bucket(store: Dict[str, Dict[str, float]], key: str, result: FcrbCaseResult) -> None:
        bucket = store.setdefault(key, {"n": 0.0, "auto_pass": 0.0, "fallback": 0.0})
        bucket["n"] += 1
        bucket["auto_pass"] += 1.0 if result.auto_pass else 0.0
        bucket["fallback"] += 1.0 if result.fallback else 0.0

    for result in results:
        _bucket(by_cat, result.category or "unknown", result)
        _bucket(by_lang, result.language_category or "unknown", result)
        for failure in result.failures:
            base = failure.split(":")[0]
            failure_counts[base] = failure_counts.get(base, 0) + 1

    def _rates(store: Dict[str, Dict[str, float]]) -> Dict[str, Dict[str, float]]:
        out = {}
        for key, bucket in store.items():
            count = max(bucket["n"], 1.0)
            out[key] = {
                "n": bucket["n"],
                "auto_pass_rate": bucket["auto_pass"] / count,
                "fallback_rate": bucket["fallback"] / count,
            }
        return out

    noisy = [r for r in results if r.category in {"typo_slang", "non_native_dialect"}]
    clean = [r for r in results if r.category == "standard"]
    multi = [r for r in results if r.category == "multi_turn"]
    unsupported = sum(1 for r in results if any(f.startswith(FAILURE_UNSUPPORTED_CLAIM) for f in r.failures))
    retrieved_ok_fallback = sum(1 for r in results if r.evidence.get("retrieved_ok_still_fallback"))

    return {
        "cases": len(results),
        "auto_pass_rate": auto_pass / n,
        "auto_pass_count": auto_pass,
        "fallback_rate": fallbacks / n,
        "unsupported_claim_rate": unsupported / n,
        "needs_human_review_count": sum(1 for r in results if r.needs_human_review),
        "all_draft_unvalidated": all(r.review_status == "draft_unvalidated" for r in results),
        "clean_auto_pass_rate": (
            sum(1 for r in clean if r.auto_pass) / len(clean) if clean else None
        ),
        "noisy_auto_pass_rate": (
            sum(1 for r in noisy if r.auto_pass) / len(noisy) if noisy else None
        ),
        "multi_turn_auto_pass_rate": (
            sum(1 for r in multi if r.auto_pass) / len(multi) if multi else None
        ),
        "retrieved_ok_still_fallback_count": retrieved_ok_fallback,
        "by_category": _rates(by_cat),
        "by_language": _rates(by_lang),
        "failure_counts": failure_counts,
    }


def prioritize_fixes(results: Sequence[FcrbCaseResult]) -> List[Dict[str, Any]]:
    """Smallest high-impact fix themes from pilot failures (suggestions only)."""
    themes: Dict[str, List[str]] = {}
    for result in results:
        if result.auto_pass:
            continue
        if result.evidence.get("retrieved_ok_still_fallback"):
            themes.setdefault(
                "Widen MODE_ANSWER / business-need bridge for informal email pain language",
                [],
            ).append(result.case_id)
        elif FAILURE_LANGUAGE in result.failures or (
            result.category == "non_native_dialect" and result.fallback
        ):
            themes.setdefault(
                "Add language-limitation or simplified-company answer path (no LLM)",
                [],
            ).append(result.case_id)
        elif any(f.startswith(FAILURE_HANDOFF) for f in result.failures):
            themes.setdefault("Expand contact-mode phrases for human-request variants", []).append(
                result.case_id
            )
        elif any(f.startswith(FAILURE_RETRIEVAL) for f in result.failures):
            themes.setdefault("Localized aliases for FCRB failures (after review)", []).append(
                result.case_id
            )
        elif any(f.startswith(FAILURE_RESPONSE) for f in result.failures):
            themes.setdefault("Response composition / required claim fixtures", []).append(
                result.case_id
            )
        else:
            themes.setdefault("Other routing/intent mismatches", []).append(result.case_id)

    ranked = sorted(themes.items(), key=lambda item: -len(item[1]))
    return [
        {"priority": index + 1, "fix_theme": theme, "case_ids": ids, "count": len(ids)}
        for index, (theme, ids) in enumerate(ranked)
    ]


def format_fcrb_report(results: Sequence[FcrbCaseResult]) -> str:
    summary = summarize_fcrb(results)
    lines = [
        "=== FCRB Pilot Baseline (automated; labels draft_unvalidated) ===",
        f"cases={summary['cases']} auto_pass={summary['auto_pass_count']}/{summary['cases']} "
        f"({summary['auto_pass_rate']:.1%})",
        f"fallback_rate={summary['fallback_rate']:.1%} "
        f"unsupported_claim_rate={summary['unsupported_claim_rate']:.1%}",
        f"clean_auto_pass={summary['clean_auto_pass_rate']!s} "
        f"noisy_auto_pass={summary['noisy_auto_pass_rate']!s} "
        f"multi_turn_auto_pass={summary['multi_turn_auto_pass_rate']!s}",
        f"retrieved_ok_still_fallback={summary['retrieved_ok_still_fallback_count']}",
        f"needs_human_review={summary['needs_human_review_count']} "
        f"(all_draft_unvalidated={summary['all_draft_unvalidated']})",
        "",
        "By category:",
    ]
    for key, bucket in sorted(summary["by_category"].items()):
        lines.append(
            f"  {key}: n={int(bucket['n'])} auto_pass={bucket['auto_pass_rate']:.1%} "
            f"fallback={bucket['fallback_rate']:.1%}"
        )
    lines.append("By language:")
    for key, bucket in sorted(summary["by_language"].items()):
        lines.append(
            f"  {key}: n={int(bucket['n'])} auto_pass={bucket['auto_pass_rate']:.1%} "
            f"fallback={bucket['fallback_rate']:.1%}"
        )
    lines.append("Failure taxonomy counts:")
    for key, count in sorted(summary["failure_counts"].items(), key=lambda kv: -kv[1]):
        lines.append(f"  {key}: {count}")
    lines.append("")
    lines.append("Failed cases:")
    for result in results:
        if result.auto_pass:
            continue
        snippet = result.response.replace("\n", " ")[:100]
        lines.append(
            f"  - {result.case_id} [{result.category}/{result.language_category}] "
            f"mode={result.mode} failures={result.failures}"
        )
        lines.append(f"    retrieved={result.retrieved_ids} sources={result.source_ids}")
        lines.append(f"    response={snippet!r}")
    lines.append("")
    lines.append("Prioritized fix themes (do not apply in this phase):")
    for item in prioritize_fixes(results):
        lines.append(
            f"  P{item['priority']} ({item['count']}): {item['fix_theme']} -> {item['case_ids']}"
        )
    lines.append("")
    lines.append(
        "NOTE: auto_pass ≠ human-verified correctness. "
        "Dual review + holdout required before customer-facing claims."
    )
    return "\n".join(lines) + "\n"
