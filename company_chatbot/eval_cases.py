"""Normalize golden YAML cases (legacy + rich schema) into a stable contract."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence


@dataclass
class RetrievalContract:
    required: List[str] = field(default_factory=list)
    acceptable: List[str] = field(default_factory=list)
    forbidden: List[str] = field(default_factory=list)

    @property
    def positive_ids(self) -> List[str]:
        """IDs that count as a hit for Hit@k / MRR (required ∪ acceptable)."""
        seen = set()
        out: List[str] = []
        for chunk_id in self.required + self.acceptable:
            if chunk_id not in seen:
                seen.add(chunk_id)
                out.append(chunk_id)
        return out


@dataclass
class ModeContract:
    expected: Optional[str] = None
    forbidden: List[str] = field(default_factory=list)


@dataclass
class ActionContract:
    allowed: List[str] = field(default_factory=list)
    forbidden: List[str] = field(default_factory=list)


@dataclass
class FamilyContract:
    required: List[str] = field(default_factory=list)
    forbidden: List[str] = field(default_factory=list)


@dataclass
class PhraseContract:
    required: List[str] = field(default_factory=list)
    forbidden: List[str] = field(default_factory=list)


@dataclass
class GoldenCase:
    name: str
    query: str
    previous_query: Optional[str] = None
    topic: Optional[str] = None
    context_dependency: Optional[str] = None
    retrieval: RetrievalContract = field(default_factory=RetrievalContract)
    mode: ModeContract = field(default_factory=ModeContract)
    actions: ActionContract = field(default_factory=ActionContract)
    families: FamilyContract = field(default_factory=FamilyContract)
    phrases: PhraseContract = field(default_factory=PhraseContract)
    tags: List[str] = field(default_factory=list)
    provenance: Dict[str, Any] = field(default_factory=dict)
    raw: Dict[str, Any] = field(default_factory=dict)

    @property
    def expected_ids(self) -> List[str]:
        return self.retrieval.positive_ids


def _as_str_list(value: Any) -> List[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    return [str(item) for item in value if item is not None and str(item).strip()]


def normalize_golden_case(raw: Dict[str, Any]) -> GoldenCase:
    """Accept legacy expected_ids / expected_families and the richer contract schema."""
    expected = raw.get("expected") if isinstance(raw.get("expected"), dict) else {}
    retrieval_raw = raw.get("retrieval") if isinstance(raw.get("retrieval"), dict) else {}
    if not retrieval_raw and isinstance(expected.get("ids"), dict):
        retrieval_raw = expected["ids"]
    if not retrieval_raw and isinstance(expected.get("retrieval"), dict):
        retrieval_raw = expected["retrieval"]

    required = _as_str_list(retrieval_raw.get("required"))
    acceptable = _as_str_list(retrieval_raw.get("acceptable"))
    forbidden = _as_str_list(retrieval_raw.get("forbidden"))
    legacy_ids = _as_str_list(raw.get("expected_ids") or expected.get("ids"))
    if not required and not acceptable and legacy_ids:
        required = list(legacy_ids)

    must_not = raw.get("must_not") if isinstance(raw.get("must_not"), dict) else {}
    forbidden.extend(_as_str_list(must_not.get("chunks") or must_not.get("ids")))

    mode_raw = raw.get("mode") if isinstance(raw.get("mode"), dict) else {}
    expected_mode = (
        mode_raw.get("expected")
        or raw.get("expected_mode")
        or expected.get("mode")
    )
    forbidden_modes = _as_str_list(
        mode_raw.get("forbidden")
        or raw.get("forbidden_modes")
        or expected.get("forbidden_modes")
        or must_not.get("modes")
    )

    families_raw = raw.get("families") if isinstance(raw.get("families"), dict) else {}
    if not families_raw and isinstance(expected.get("families"), dict):
        families_raw = expected["families"]
    family_required = _as_str_list(families_raw.get("required"))
    if not family_required:
        legacy_families = raw.get("expected_families")
        if legacy_families is None and isinstance(expected.get("families"), list):
            legacy_families = expected.get("families")
        family_required = _as_str_list(legacy_families)
    family_forbidden = _as_str_list(
        families_raw.get("forbidden") or must_not.get("families") or expected.get("forbidden_families")
    )

    actions_raw = raw.get("actions") if isinstance(raw.get("actions"), dict) else {}
    if not actions_raw and isinstance(expected.get("actions"), dict):
        actions_raw = expected["actions"]
    action_forbidden = _as_str_list(
        actions_raw.get("forbidden")
        or raw.get("forbidden_actions")
        or expected.get("forbidden_actions")
        or must_not.get("actions")
    )
    action_allowed = _as_str_list(actions_raw.get("allowed") or expected.get("allowed_actions"))

    phrases_raw = raw.get("phrases") if isinstance(raw.get("phrases"), dict) else {}
    phrase_required = _as_str_list(phrases_raw.get("required") or raw.get("required_phrases"))
    phrase_forbidden = _as_str_list(
        phrases_raw.get("forbidden") or must_not.get("phrases") or raw.get("forbidden_phrases")
    )

    context_dependency = raw.get("context_dependency")
    if not context_dependency and isinstance(expected, dict):
        context_dependency = expected.get("context_dependency")

    topic = raw.get("topic")
    if not topic and isinstance(expected, dict):
        topic = expected.get("topic")

    return GoldenCase(
        name=str(raw.get("name") or raw.get("id") or "unnamed"),
        query=str(raw.get("query") or ""),
        previous_query=(raw.get("previous_query") or None),
        topic=str(topic) if topic else None,
        context_dependency=str(context_dependency).lower() if context_dependency else None,
        retrieval=RetrievalContract(
            required=required,
            acceptable=acceptable,
            forbidden=list(dict.fromkeys(forbidden)),
        ),
        mode=ModeContract(
            expected=str(expected_mode) if expected_mode else None,
            forbidden=forbidden_modes,
        ),
        actions=ActionContract(allowed=action_allowed, forbidden=action_forbidden),
        families=FamilyContract(required=_as_str_list(family_required), forbidden=family_forbidden),
        phrases=PhraseContract(required=phrase_required, forbidden=phrase_forbidden),
        tags=_as_str_list(raw.get("tags")),
        provenance=dict(raw.get("provenance") or {}),
        raw=raw,
    )


def load_golden_cases(raw_cases: Sequence[Dict[str, Any]]) -> List[GoldenCase]:
    return [normalize_golden_case(case) for case in raw_cases]
