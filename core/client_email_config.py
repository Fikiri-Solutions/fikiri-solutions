"""
Per-tenant email assistant configuration (client/business-specific).

Loaded from users row + user_services ai-assistant settings + optional
data/business_profile.json defaults. Keeps AI prompts adaptable without
hardcoding one company's assumptions.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

DEFAULT_CLIENT_EMAIL_CONFIG: Dict[str, Any] = {
    "business_type": "",
    "company_name": "Fikiri Solutions",
    "services_offered": [],
    "target_customer_types": [],
    "high_value_keywords": [],
    "low_value_keywords": [],
    "geographic_service_area": "",
    "preferred_tone": "professional_warm",
    "escalation_rules": {
        "complaint_always_review": True,
        "legal_always_review": True,
        "min_confidence_auto_send": 0.85,
    },
    "lead_scoring_weights": {
        "pricing_signal": 15,
        "timeline_signal": 10,
        "partnership_signal": 12,
    },
    "custom_intent_labels": [],
    "custom_reply_templates": {},
    "do_not_reply_conditions": ["unsubscribe", "noreply"],
    "required_crm_fields": ["email"],
}


def _parse_json_list(value: Any) -> List[str]:
    if isinstance(value, list):
        return [str(v).strip() for v in value if str(v).strip()]
    if isinstance(value, str) and value.strip():
        try:
            parsed = json.loads(value)
            if isinstance(parsed, list):
                return [str(v).strip() for v in parsed if str(v).strip()]
        except json.JSONDecodeError:
            return [s.strip() for s in value.split(",") if s.strip()]
    return []


def _load_file_defaults() -> Dict[str, Any]:
    try:
        path = Path("data/business_profile.json")
        if path.exists():
            with open(path, encoding="utf-8") as fh:
                data = json.load(fh)
                if isinstance(data, dict):
                    return data
    except Exception as exc:
        logger.debug("business_profile.json not loaded: %s", exc)
    return {}


def load_client_email_config(
    user_id: Optional[int] = None,
    *,
    db=None,
) -> Dict[str, Any]:
    """
    Merge global defaults, file profile, user record, and ai-assistant service settings.
    """
    cfg: Dict[str, Any] = {**DEFAULT_CLIENT_EMAIL_CONFIG, **_load_file_defaults()}

    if not user_id:
        return cfg

    try:
        if db is None:
            from core.database_optimization import db_optimizer

            db = db_optimizer

        rows = db.execute_query(
            """
            SELECT business_name, business_email, industry, team_size, metadata
            FROM users WHERE id = ? LIMIT 1
            """,
            (user_id,),
        )
        if rows:
            row = rows[0] if isinstance(rows[0], dict) else {}
            if row.get("business_name"):
                cfg["company_name"] = row["business_name"]
            if row.get("industry"):
                cfg["business_type"] = row["industry"]
            meta = row.get("metadata")
            if isinstance(meta, str) and meta.strip():
                try:
                    meta = json.loads(meta)
                except json.JSONDecodeError:
                    meta = {}
            if isinstance(meta, dict):
                email_cfg = meta.get("email_assistant") or meta.get("email_config") or {}
                if isinstance(email_cfg, dict):
                    cfg.update({k: v for k, v in email_cfg.items() if v is not None})

        from core.user_services import get_service_settings

        svc = get_service_settings(user_id, "ai-assistant")
        if svc:
            if svc.get("responseTone"):
                cfg["preferred_tone"] = svc["responseTone"]
            if svc.get("servicesOffered"):
                cfg["services_offered"] = _parse_json_list(svc["servicesOffered"])
            if svc.get("highValueKeywords"):
                cfg["high_value_keywords"] = _parse_json_list(svc["highValueKeywords"])
            if svc.get("lowValueKeywords"):
                cfg["low_value_keywords"] = _parse_json_list(svc["lowValueKeywords"])
            if svc.get("customIntentLabels"):
                cfg["custom_intent_labels"] = _parse_json_list(svc["customIntentLabels"])
            if isinstance(svc.get("escalationRules"), dict):
                cfg["escalation_rules"] = {**cfg.get("escalation_rules", {}), **svc["escalationRules"]}
            if isinstance(svc.get("leadScoringWeights"), dict):
                cfg["lead_scoring_weights"] = {**cfg.get("lead_scoring_weights", {}), **svc["leadScoringWeights"]}
    except Exception as exc:
        logger.warning("load_client_email_config failed for user %s: %s", user_id, exc)

    return cfg
