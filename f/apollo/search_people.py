"""Apollo people search for Windmill — free-plan safe (0 credit search).

Does NOT reveal emails or phones. Use enrich_capped for that, manually.
Apollo People API Search: https://docs.apollo.io/reference/people-api-search
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional

APOLLO_SEARCH_URL = "https://api.apollo.io/api/v1/mixed_people/api_search"
HARD_MAX_PER_PAGE = 25


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


def _slim_person(person: Dict[str, Any]) -> Dict[str, Any]:
    org = person.get("organization") or {}
    return {
        "apollo_id": person.get("id"),
        "name": person.get("name"),
        "title": person.get("title"),
        "linkedin_url": person.get("linkedin_url"),
        "city": person.get("city"),
        "state": person.get("state"),
        "country": person.get("country"),
        "organization_name": org.get("name") or person.get("organization_name"),
        "organization_domain": org.get("primary_domain") or org.get("website_url"),
        "has_email": bool(person.get("has_email") or person.get("email")),
        # Never include revealed email/phone from search path.
    }


def main(
    api_key: str,
    person_titles: Optional[List[str]] = None,
    person_locations: Optional[List[str]] = None,
    organization_locations: Optional[List[str]] = None,
    organization_num_employees_ranges: Optional[List[str]] = None,
    q_organization_keyword_tags: Optional[List[str]] = None,
    per_page: int = 10,
    page: int = 1,
) -> Dict[str, Any]:
    """Search Apollo people. Costs 0 credits. Returns slim candidate cards only."""
    key = (api_key or "").strip()
    if not key:
        raise ValueError("api_key is required (Apollo master/API key; free-plan limited)")

    size = max(1, min(int(per_page or 10), HARD_MAX_PER_PAGE))
    page_n = max(1, int(page or 1))

    payload: Dict[str, Any] = {
        "page": page_n,
        "per_page": size,
    }
    if person_titles:
        payload["person_titles"] = list(person_titles)
    if person_locations:
        payload["person_locations"] = list(person_locations)
    if organization_locations:
        payload["organization_locations"] = list(organization_locations)
    if organization_num_employees_ranges:
        payload["organization_num_employees_ranges"] = list(
            organization_num_employees_ranges
        )
    if q_organization_keyword_tags:
        payload["q_organization_keyword_tags"] = list(q_organization_keyword_tags)

    data = _post_json(APOLLO_SEARCH_URL, key, payload)
    people = data.get("people") or data.get("contacts") or []
    candidates = [_slim_person(p) for p in people if isinstance(p, dict)]

    return {
        "credits_spent_estimate": 0,
        "page": page_n,
        "per_page": size,
        "returned": len(candidates),
        "candidates": candidates,
        "note": (
            "Search only — no emails/phones. Review candidates, then run "
            "f/apollo/enrich_capped with confirm=True and a small max_people."
        ),
    }
