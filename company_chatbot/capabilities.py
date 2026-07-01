"""Capability map and mix-and-match needs detection (Phase 6e)."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple

from company_chatbot import config
from company_chatbot.retrieval import normalize_query_text

_UNCERTAINTY_RE = re.compile(
    r"don't know if|not sure (?:whether|if)|website or (?:a )?crm|automation or a new form",
    re.I,
)
_PHRASE_SCORE = 1.0
_RELATED_FAMILY_SCORE = 0.35
_CAPABILITY_SCORE = 0.75
_BUNDLE_FAMILY_OVERLAP_WEIGHT = 0.5


@dataclass(frozen=True)
class FamilyDef:
    id: str
    label: str
    capabilities: Tuple[str, ...]
    client_phrases: Tuple[str, ...]
    related_families: Tuple[str, ...]
    kb_chunk_ids: Tuple[str, ...]
    legacy_family_ids: Tuple[str, ...]
    disambiguation_question: str


@dataclass(frozen=True)
class CapabilityDef:
    id: str
    label: str
    client_phrases: Tuple[str, ...]
    family_ids: Tuple[str, ...]


@dataclass(frozen=True)
class BundleDef:
    id: str
    label: str
    summary: str
    family_ids: Tuple[str, ...]
    capability_ids: Tuple[str, ...]
    client_phrases: Tuple[str, ...]
    kb_chunk_ids: Tuple[str, ...]
    next_step: str


@dataclass
class NeedsDetectionResult:
    query: str
    detected_families: List[str] = field(default_factory=list)
    detected_capabilities: List[str] = field(default_factory=list)
    family_scores: Dict[str, float] = field(default_factory=dict)
    capability_scores: Dict[str, float] = field(default_factory=dict)
    suggested_bundle: Optional[str] = None
    suggested_bundle_label: Optional[str] = None
    confidence: float = 0.0
    kb_chunk_ids: List[str] = field(default_factory=list)
    disambiguation_question: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "detected_families": self.detected_families,
            "detected_capabilities": self.detected_capabilities,
            "suggested_bundle": self.suggested_bundle,
            "suggested_bundle_label": self.suggested_bundle_label,
            "confidence": round(self.confidence, 4),
            "kb_chunk_ids": self.kb_chunk_ids,
            "disambiguation_question": self.disambiguation_question,
        }


@dataclass(frozen=True)
class CapabilityMap:
    families: Dict[str, FamilyDef]
    capabilities: Dict[str, CapabilityDef]
    bundles: Dict[str, BundleDef]


def _tuple_strs(values: Any) -> Tuple[str, ...]:
    if not values:
        return tuple()
    return tuple(str(v) for v in values)


def load_capability_map(path: Path | None = None) -> CapabilityMap:
    map_path = path or (config.kb_data_dir() / "fikiri_capability_map.json")
    raw = json.loads(map_path.read_text(encoding="utf-8"))
    families = {
        str(row["id"]): FamilyDef(
            id=str(row["id"]),
            label=str(row.get("label") or row["id"]),
            capabilities=_tuple_strs(row.get("capabilities")),
            client_phrases=_tuple_strs(row.get("client_phrases")),
            related_families=_tuple_strs(row.get("related_families")),
            kb_chunk_ids=_tuple_strs(row.get("kb_chunk_ids")),
            legacy_family_ids=_tuple_strs(row.get("legacy_family_ids")),
            disambiguation_question=str(row.get("disambiguation_question") or ""),
        )
        for row in raw.get("families") or []
    }
    capabilities = {
        str(row["id"]): CapabilityDef(
            id=str(row["id"]),
            label=str(row.get("label") or row["id"]),
            client_phrases=_tuple_strs(row.get("client_phrases")),
            family_ids=_tuple_strs(row.get("family_ids")),
        )
        for row in raw.get("capabilities") or []
    }
    bundles = {
        str(row["id"]): BundleDef(
            id=str(row["id"]),
            label=str(row.get("label") or row["id"]),
            summary=str(row.get("summary") or ""),
            family_ids=_tuple_strs(row.get("family_ids")),
            capability_ids=_tuple_strs(row.get("capability_ids")),
            client_phrases=_tuple_strs(row.get("client_phrases")),
            kb_chunk_ids=_tuple_strs(row.get("kb_chunk_ids")),
            next_step=str(row.get("next_step") or ""),
        )
        for row in raw.get("bundles") or []
    }
    return CapabilityMap(families=families, capabilities=capabilities, bundles=bundles)


@lru_cache(maxsize=1)
def _cached_map() -> CapabilityMap:
    return load_capability_map()


def clear_capability_map_cache_for_tests() -> None:
    _cached_map.cache_clear()


def effective_query_for_needs(query: str, previous_query: str | None = None) -> str:
    from company_chatbot.retrieval import effective_query_for_retrieval

    return effective_query_for_retrieval(query, previous_query)


def _phrase_hits(normalized_query: str, phrases: Sequence[str]) -> int:
    hits = 0
    for phrase in phrases:
        phrase_norm = normalize_query_text(phrase)
        if phrase_norm and phrase_norm in normalized_query:
            hits += 1
    return hits


def _rank_scored(scores: Dict[str, float], min_score: float = 0.35) -> List[str]:
    ranked = sorted(scores.items(), key=lambda item: (-item[1], item[0]))
    return [key for key, score in ranked if score >= min_score]


def detect_needs(
    query: str,
    *,
    previous_query: str | None = None,
    effective_query: str | None = None,
) -> NeedsDetectionResult:
    effective = (effective_query or "").strip() or effective_query_for_needs(query, previous_query)
    normalized = normalize_query_text(effective)
    cmap = _cached_map()

    family_scores: Dict[str, float] = {}
    for family in cmap.families.values():
        hits = _phrase_hits(normalized, family.client_phrases)
        if hits:
            family_scores[family.id] = family_scores.get(family.id, 0.0) + hits * _PHRASE_SCORE

    if _UNCERTAINTY_RE.search(normalized):
        family_scores["consulting_and_workflow_audit"] = (
            family_scores.get("consulting_and_workflow_audit", 0.0) + 1.6
        )

    for family_id, score in list(family_scores.items()):
        family = cmap.families[family_id]
        for related_id in family.related_families:
            if related_id in family_scores:
                continue
            family_scores[related_id] = family_scores.get(related_id, 0.0) + score * _RELATED_FAMILY_SCORE

    capability_scores: Dict[str, float] = {}
    for capability in cmap.capabilities.values():
        hits = _phrase_hits(normalized, capability.client_phrases)
        if hits:
            capability_scores[capability.id] = hits * _CAPABILITY_SCORE
            for family_id in capability.family_ids:
                family_scores[family_id] = family_scores.get(family_id, 0.0) + hits * 0.45

    detected_families = _rank_scored(family_scores)
    detected_capabilities = _rank_scored(capability_scores, min_score=0.5)
    detected_capability_labels = [
        cmap.capabilities[cid].label for cid in detected_capabilities if cid in cmap.capabilities
    ]

    best_bundle: Optional[BundleDef] = None
    best_bundle_score = 0.0
    detected_family_set = set(detected_families)
    for bundle in cmap.bundles.values():
        bundle_phrase_hits = _phrase_hits(normalized, bundle.client_phrases)
        overlap = len(detected_family_set & set(bundle.family_ids))
        overlap_ratio = overlap / max(len(bundle.family_ids), 1)
        score = bundle_phrase_hits * 1.2 + overlap_ratio * len(bundle.family_ids) * _BUNDLE_FAMILY_OVERLAP_WEIGHT
        if bundle.id == "workflow_audit_path" and _UNCERTAINTY_RE.search(normalized):
            score += 1.5
        if score > best_bundle_score:
            best_bundle_score = score
            best_bundle = bundle

    kb_ids: List[str] = []
    for family_id in detected_families[:4]:
        kb_ids.extend(cmap.families[family_id].kb_chunk_ids)
    if best_bundle:
        kb_ids.extend(best_bundle.kb_chunk_ids)
    kb_ids = list(dict.fromkeys(kb_ids))

    confidence = 0.0
    if family_scores:
        top = max(family_scores.values())
        second = sorted(family_scores.values(), reverse=True)[1] if len(family_scores) > 1 else 0.0
        breadth = min(1.0, len(detected_families) / 3.0)
        confidence = min(1.0, (top * 0.45) + (second * 0.15) + (best_bundle_score * 0.25) + (breadth * 0.15))

    disambiguation: Optional[str] = None
    if len(detected_families) >= 3 and confidence < 0.75:
        for family_id in detected_families[:2]:
            question = cmap.families[family_id].disambiguation_question
            if question:
                disambiguation = question
                break

    return NeedsDetectionResult(
        query=effective,
        detected_families=detected_families,
        detected_capabilities=detected_capability_labels,
        family_scores=family_scores,
        capability_scores=capability_scores,
        suggested_bundle=best_bundle.id if best_bundle and best_bundle_score >= 0.8 else None,
        suggested_bundle_label=best_bundle.label if best_bundle and best_bundle_score >= 0.8 else None,
        confidence=round(confidence, 4),
        kb_chunk_ids=kb_ids,
        disambiguation_question=disambiguation,
    )


def capability_chunk_boost(chunk_id: str, needs: NeedsDetectionResult) -> float:
    if chunk_id in needs.kb_chunk_ids:
        rank = needs.kb_chunk_ids.index(chunk_id)
        return max(0.18, 0.32 - (rank * 0.04))
    return 0.0


def legacy_families_from_needs(needs: NeedsDetectionResult) -> List[str]:
    cmap = _cached_map()
    legacy: List[str] = []
    for family_id in needs.detected_families:
        family = cmap.families.get(family_id)
        if not family:
            continue
        legacy.extend(family.legacy_family_ids)
    return list(dict.fromkeys(legacy))


def should_use_capability_bridge(needs: NeedsDetectionResult) -> bool:
    return len(needs.detected_families) >= 2 or bool(needs.suggested_bundle)


def compose_capability_bridge(
    needs: NeedsDetectionResult,
    chunks: Sequence[object],
) -> str:
    cmap = _cached_map()
    labels = [cmap.families[fid].label for fid in needs.detected_families[:3] if fid in cmap.families]
    if not labels:
        labels = ["workflow automation"]

    opener = (
        f"That sounds like a mix of {labels[0]}"
        + (f", {labels[1]}" if len(labels) > 1 else "")
        + (f", and {labels[2]}" if len(labels) > 2 else "")
        + "."
    )

    bundle_text = ""
    if needs.suggested_bundle and needs.suggested_bundle in cmap.bundles:
        bundle = cmap.bundles[needs.suggested_bundle]
        bundle_text = f" It is closest to our {bundle.label} path: {bundle.summary}"

    capability_text = ""
    if needs.detected_capabilities:
        capability_text = (
            " The likely capabilities are "
            + ", ".join(needs.detected_capabilities[:4])
            + "."
        )

    evidence = getattr(chunks[0], "text", "").strip() if chunks else ""
    next_step = ""
    if needs.suggested_bundle and needs.suggested_bundle in cmap.bundles:
        next_step = " " + cmap.bundles[needs.suggested_bundle].next_step
    elif needs.detected_families and "consulting_and_workflow_audit" in needs.detected_families:
        next_step = " Fikiri would usually start by mapping the workflow before picking a first build."

    return f"{opener}{bundle_text}{capability_text} {evidence}{next_step}".strip()
