"""CRM automation action handler."""

from __future__ import annotations

import logging
from typing import Any, Dict
from uuid import uuid4

from core.database_optimization import db_optimizer
from crm.service import enhanced_crm_service

logger = logging.getLogger(__name__)

# update_crm_field preset: merge stage/tags after inbound workflow (legacy slug: gmail_crm).
INBOUND_CRM_SYNC_SLUG = "inbound_crm_sync"
_LEGACY_INBOUND_CRM_SYNC_SLUGS = frozenset(("gmail_crm",))


def is_inbound_crm_sync_slug(slug: Any) -> bool:
    if not slug or not isinstance(slug, str):
        return False
    return slug.strip() == INBOUND_CRM_SYNC_SLUG or slug in _LEGACY_INBOUND_CRM_SYNC_SLUGS


class CrmActionHandler:
    """Owns CRM-related action execution details for automation rules."""

    def __init__(self, logger_instance):
        self.logger = logger_instance

    def execute_update_lead_stage(
        self, parameters: Dict[str, Any], trigger_data: Dict[str, Any], user_id: int
    ) -> Dict[str, Any]:
        """Execute update lead stage action."""
        try:
            new_stage = parameters.get("stage")
            lead_id = trigger_data.get("lead_id")

            if not lead_id or not new_stage:
                return {"success": False, "error": "Missing lead_id or stage parameter"}

            return enhanced_crm_service.update_lead(lead_id, user_id, {"stage": new_stage})
        except Exception as e:
            return {"success": False, "error": str(e)}

    def execute_add_lead_activity(
        self, parameters: Dict[str, Any], trigger_data: Dict[str, Any], user_id: int
    ) -> Dict[str, Any]:
        """Execute add lead activity action."""
        try:
            activity_type = parameters.get("activity_type", "note_added")
            description = parameters.get("description", "Automated activity")
            lead_id = trigger_data.get("lead_id")

            if not lead_id:
                return {"success": False, "error": "Missing lead_id parameter"}

            return enhanced_crm_service.add_lead_activity(lead_id, user_id, activity_type, description)
        except Exception as e:
            return {"success": False, "error": str(e)}

    def execute_update_crm_field(
        self, action_data: Dict[str, Any], trigger_data: Dict[str, Any], user_id: int
    ) -> Dict[str, Any]:
        """Update a CRM field. Handles lead_scoring preset: set stage when score >= min_score."""
        try:
            if action_data.get("slug") == "lead_scoring":
                lead_id = trigger_data.get("lead_id") or action_data.get("lead_id")
                if not lead_id:
                    return {"success": False, "error": "lead_id required for lead_scoring"}
                row = db_optimizer.execute_query(
                    "SELECT id, score FROM leads WHERE id = ? AND user_id = ?",
                    (lead_id, user_id),
                )
                if not row:
                    return {"success": False, "error": "Lead not found"}
                score = row[0].get("score") or 0
                min_score = (
                    int(action_data.get("min_score", 60))
                    if action_data.get("min_score") is not None
                    else 60
                )
                if score >= min_score:
                    target_stage = action_data.get("target_stage", "qualified")
                    db_optimizer.execute_query(
                        "UPDATE leads SET stage = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ? AND user_id = ?",
                        (target_stage, lead_id, user_id),
                        fetch=False,
                    )
                    enhanced_crm_service.add_lead_activity(
                        lead_id,
                        user_id,
                        "note_added",
                        f"Lead scored {score} (≥{min_score}); stage set to {target_stage}",
                    )
                return {"success": True, "data": {"lead_id": lead_id, "score": score, "min_score": min_score}}

            slug = action_data.get("slug")
            pre_lead_id = trigger_data.get("lead_id") or action_data.get("lead_id")

            # Inbound workflow already upserted the lead; apply preset stage/tags only.
            if is_inbound_crm_sync_slug(slug) and pre_lead_id:
                lead_id = int(pre_lead_id)
                row = db_optimizer.execute_query(
                    "SELECT id FROM leads WHERE id = ? AND user_id = ?",
                    (lead_id, user_id),
                )
                if not row:
                    return {"success": False, "error": "Lead not found", "error_code": "LEAD_NOT_FOUND"}
                target_stage = action_data.get("target_stage", "new")
                tags = action_data.get("tags")
                updates: Dict[str, Any] = {}
                if target_stage:
                    updates["stage"] = target_stage
                if tags is not None:
                    updates["tags"] = tags
                if updates:
                    cid = trigger_data.get("correlation_id")
                    if cid:
                        updates["correlation_id"] = cid
                    ur = enhanced_crm_service.update_lead(lead_id, user_id, updates)
                    if not ur.get("success"):
                        return {
                            "success": False,
                            "error": ur.get("error", "CRM update failed"),
                            "error_code": ur.get("error_code", "CRM_UPDATE_ERROR"),
                        }
                else:
                    enhanced_crm_service.add_lead_activity(
                        lead_id,
                        user_id,
                        "note_added",
                        "Inbound CRM sync: rule active (no stage/tags to merge)",
                    )
                return {
                    "success": True,
                    "data": {
                        "lead_id": lead_id,
                        "action": "lead_updated",
                        "message": "Lead updated via inbound workflow + preset",
                    },
                }

            # Legacy path when inbound workflow did not set lead_id (API tests, manual triggers).
            if trigger_data.get("sender_email") and not pre_lead_id and not action_data.get("lead_id"):
                sender_hdr = trigger_data.get("sender_raw") or trigger_data.get("sender_email")
                subj = trigger_data.get("subject", "")
                provider = trigger_data.get("provider") or "inbound"
                corr = trigger_data.get("correlation_id")
                merged = enhanced_crm_service.upsert_lead_from_inbound_email(
                    user_id,
                    sender_header=str(sender_hdr or ""),
                    subject=str(subj or ""),
                    provider=str(provider),
                    correlation_id=str(corr or uuid4()),
                    default_source=str(provider),
                )
                if not merged.get("success"):
                    return {
                        "success": False,
                        "error": merged.get("error", "Inbound lead upsert failed"),
                        "error_code": merged.get("error_code", "CRM_UPSERT_FAILED"),
                    }
                if merged.get("skipped"):
                    return {
                        "success": True,
                        "data": {
                            "lead_id": None,
                            "skipped": True,
                            "reason": merged.get("reason"),
                        },
                    }
                lead_id_merge = merged["data"]["lead_id"]
                target_stage = action_data.get("target_stage", "new")
                tags = action_data.get("tags")
                updates2: Dict[str, Any] = {}
                if target_stage:
                    updates2["stage"] = target_stage
                if tags is not None:
                    updates2["tags"] = tags
                if updates2:
                    updates2["correlation_id"] = trigger_data.get("correlation_id")
                    ur2 = enhanced_crm_service.update_lead(int(lead_id_merge), user_id, updates2)
                    if not ur2.get("success"):
                        return {
                            "success": False,
                            "error": ur2.get("error", "CRM update failed"),
                            "error_code": ur2.get("error_code", "CRM_UPDATE_ERROR"),
                        }
                else:
                    enhanced_crm_service.add_lead_activity(
                        int(lead_id_merge),
                        user_id,
                        "note_added",
                        f"Inbound CRM sync preset: inbound upsert ({target_stage})",
                    )
                return {
                    "success": True,
                    "data": {
                        "lead_id": int(lead_id_merge),
                        "action": "lead_created_or_updated",
                        "message": "Inbound lead upsert + preset merge",
                    },
                }

            lead_id = action_data.get("lead_id") or trigger_data.get("lead_id")
            field_name = action_data.get("field_name")
            field_value = action_data.get("field_value")
            if not lead_id or not field_name:
                return {"success": False, "error": "Missing lead_id or field_name"}
            db_optimizer.execute_query(
                """UPDATE leads SET {} = ? WHERE id = ? AND user_id = ?""".format(field_name),
                (field_value, lead_id, user_id),
                fetch=False,
            )
            self.logger.info("Updated CRM field %s for lead %s", field_name, lead_id)
            return {"success": True, "data": {"lead_id": int(lead_id)}}
        except Exception as e:
            logger.error("Error updating CRM field: %s", e)
            return {"success": False, "error": str(e)}
