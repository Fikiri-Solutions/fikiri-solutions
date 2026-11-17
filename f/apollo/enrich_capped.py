"""Apollo people enrichment with a hard credit cap — free-plan guardrails.

People match typically costs ~1 credit per person for email/demographics.
Mobile/dial and waterfall are disabled here to avoid surprise spend.
Docs: https://docs.apollo.io/reference/people-enrichment
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional

APOLLO_MATCH_URL = "https://api.apollo.io/api/v1/people/match"
HARD_MAX_PEOPLE = 5


def _post_json(url: str, api_key: str, payload: Dict[str, Any], timeout_s: float = 30.0) -> Dict[str, Any]:
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Cache-Control": "no-cache",
            "X-Api-Key": api_key,
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout_s) as resp:
            raw = resp.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:800]
        raise RuntimeError(f"Apollo HTTP {exc.code}: {detail}") from exc
    return json.loads(raw) if raw else {}


def _enrich_one(api_key: str, person: Dict[str, Any]) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "reveal_personal_emails": False,
        "reveal_phone_number": False,
    }
    for key in ("id", "first_name", "last_name", "name", "email", "linkedin_url", "domain", "organization_name"):
        val = person.get(key)
        if val:
            payload[key] = val

    # Prefer apollo id when present
    if person.get("apollo_id"):
        payload["id"] = person["apollo_id"]

    data = _post_json(APOLLO_MATCH_URL, api_key, payload)
    matched = data.get("person") or {}
    return {
        "apollo_id": matched.get("id") or person.get("apollo_id") or person.get("id"),
        "name": matched.get("name") or person.get("name"),
        "title": matched.get("title"),
        "email": matched.get("email"),
        "organization_name": (matched.get("organization") or {}).get("name"),
        "linkedin_url": matched.get("linkedin_url"),
        "match_confidence": data.get("match_confidence") or matched.get("match_confidence"),
    }


def main(
    api_key: str,
    people: Optional[List[Dict[str, Any]]] = None,
    confirm: bool = False,
    max_people: int = 3,
) -> Dict[str, Any]:
    """Enrich a tiny approved shortlist. Refuses unless confirm=True."""
    key = (api_key or "").strip()
    if not key:
        raise ValueError("api_key is required")

    if not confirm:
        return {
            "enriched": [],
            "skipped": True,
            "reason": "confirm=False — set confirm=True after reviewing search results",
            "credits_spent_estimate": 0,
        }

    rows = list(people or [])
    cap = max(1, min(int(max_people or 3), HARD_MAX_PEOPLE))
    if len(rows) > cap:
        rows = rows[:cap]

    enriched: List[Dict[str, Any]] = []
    errors: List[Dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            errors.append({"input": row, "error": "not_an_object"})
            continue
        try:
            enriched.append(_enrich_one(key, row))
        except Exception as exc:  # noqa: BLE001 — surface per-row failures in result
            errors.append(
                {
                    "apollo_id": row.get("apollo_id") or row.get("id"),
                    "name": row.get("name"),
                    "error": str(exc)[:400],
                }
            )

    return {
        "enriched": enriched,
        "errors": errors,
        "requested": len(people or []),
        "attempted": len(rows),
        "credits_spent_estimate": len(enriched),  # ~1 credit each when email/demo returned
        "hard_max_people": HARD_MAX_PEOPLE,
        "note": (
            "Estimate only — check Apollo Credits & AI Usage. "
            "Phones/waterfall disabled. Free-plan: keep max_people ≤ 3 per run."
        ),
    }
