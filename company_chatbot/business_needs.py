"""Business-need recognition — concept patterns mapped to capability families."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

from company_chatbot import config
from company_chatbot.retrieval import normalize_query_text


def _phrase_matches(normalized_query: str, phrase: str) -> bool:
    """Token-boundary match; allow stem prefixes (profit→profitability) but not infix (profit↛nonprofit)."""
    phrase_norm = normalize_query_text(phrase)
    if not phrase_norm or not normalized_query:
        return False
    # Exact token/phrase boundaries.
    exact = r"(?<!\w)" + re.escape(phrase_norm) + r"(?!\w)"
    if re.search(exact, normalized_query):
        return True
    # Single-token stems of length >= 4 may match longer tokens they prefix.
    if " " not in phrase_norm and len(phrase_norm) >= 4:
        stem = r"(?<!\w)" + re.escape(phrase_norm) + r"\w+"
        return re.search(stem, normalized_query) is not None
    return False


@dataclass(frozen=True)
class BusinessNeedDef:
    id: str
    label: str
    concept_phrases: Tuple[str, ...]
    capability_status: str
    capability_families: Tuple[str, ...]
    allowed_claims: Tuple[str, ...]
    forbidden_claims: Tuple[str, ...]


@dataclass
class BusinessNeedHit:
    need_id: str
    label: str
    status: str
    families: List[str] = field(default_factory=list)
    score: float = 0.0


@dataclass
class BusinessNeedResult:
    hits: List[BusinessNeedHit] = field(default_factory=list)
    primary_need_id: Optional[str] = None
    family_boosts: Dict[str, float] = field(default_factory=dict)

    @property
    def need_ids(self) -> List[str]:
        return [hit.need_id for hit in self.hits]


@lru_cache(maxsize=1)
def load_business_need_taxonomy(path: Path | None = None) -> Tuple[BusinessNeedDef, ...]:
    tax_path = path or (config.kb_data_dir() / "fikiri_business_need_taxonomy.json")
    raw = json.loads(tax_path.read_text(encoding="utf-8"))
    needs: List[BusinessNeedDef] = []
    for row in raw.get("needs") or []:
        needs.append(
            BusinessNeedDef(
                id=str(row["id"]),
                label=str(row.get("label") or row["id"]),
                concept_phrases=tuple(str(p) for p in (row.get("concept_phrases") or [])),
                capability_status=str(row.get("capability_status") or "custom_discovery"),
                capability_families=tuple(str(f) for f in (row.get("capability_families") or [])),
                allowed_claims=tuple(str(c) for c in (row.get("allowed_claims") or [])),
                forbidden_claims=tuple(str(c) for c in (row.get("forbidden_claims") or [])),
            )
        )
    return tuple(needs)


def clear_business_need_cache_for_tests() -> None:
    load_business_need_taxonomy.cache_clear()


def detect_business_needs(query: str) -> BusinessNeedResult:
    """Score reusable business-need concepts (not industry-specific memorization)."""
    normalized = normalize_query_text(query or "")
    if not normalized:
        return BusinessNeedResult()

    hits: List[BusinessNeedHit] = []
    family_boosts: Dict[str, float] = {}
    for need in load_business_need_taxonomy():
        matched = 0
        for phrase in need.concept_phrases:
            if _phrase_matches(normalized, phrase):
                matched += 1
        if matched <= 0:
            continue
        score = float(matched)
        hits.append(
            BusinessNeedHit(
                need_id=need.id,
                label=need.label,
                status=need.capability_status,
                families=list(need.capability_families),
                score=score,
            )
        )
        # Stronger boost for verified families; still allow custom_discovery bridges.
        weight = 0.9 if need.capability_status.startswith("verified") else 0.7
        for family_id in need.capability_families:
            family_boosts[family_id] = family_boosts.get(family_id, 0.0) + score * weight

    hits.sort(key=lambda item: (-item.score, item.need_id))
    return BusinessNeedResult(
        hits=hits,
        primary_need_id=hits[0].need_id if hits else None,
        family_boosts=family_boosts,
    )


def qualified_bridge_suffix(need_result: BusinessNeedResult) -> str:
    """Cautious next-step language based on capability status."""
    if not need_result.hits:
        return (
            " If this is a custom workflow, we'd confirm fit after a short discovery call "
            "rather than promising a turnkey build."
        )
    statuses = {hit.status for hit in need_result.hits[:2]}
    if "unsupported_or_discovery" in statuses:
        return (
            " That area may require custom discovery rather than a packaged product feature. "
            "We can clarify what is in scope before promising a build."
        )
    if any(status.startswith("custom") or status.endswith("partial") for status in statuses):
        return (
            " This is often a custom automation or integration fit, so we'd map your current "
            "tools and workflow before confirming what we can implement. Want to talk through it?"
        )
    return (
        " Fikiri can help with the related capabilities above; tell me which part matters most "
        "or ask to talk with the team."
    )


def taxonomy_forbidden_claims(need_ids: Sequence[str]) -> List[str]:
    blocked: List[str] = []
    index = {need.id: need for need in load_business_need_taxonomy()}
    for need_id in need_ids:
        need = index.get(need_id)
        if need:
            blocked.extend(need.forbidden_claims)
    return list(dict.fromkeys(blocked))
