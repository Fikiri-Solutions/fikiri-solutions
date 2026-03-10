import json
import logging
from typing import Any, Dict, Optional

from flask import Request

from core.database_optimization import db_optimizer

logger = logging.getLogger(__name__)


def log_activity_event(
    user_id: int,
    event_type: str,
    message: Optional[str] = None,
    status: str = "success",
    metadata: Optional[Dict[str, Any]] = None,
    request: Optional[Request] = None,
) -> None:
    """Persist a user-level activity event for dashboard activity feed."""
    try:
        event_data = {"status": status}
        if message:
            event_data["message"] = message
        if metadata:
            event_data.update(metadata)

        ip_address = None
        user_agent = None
        session_id = None
        if request is not None:
            ip_address = request.headers.get("X-Forwarded-For", request.remote_addr)
            user_agent = request.headers.get("User-Agent")
            session_id = request.cookies.get("session_id")

        db_optimizer.execute_query(
            """
            INSERT INTO analytics_events
                (user_id, event_type, event_data, ip_address, user_agent, session_id)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                event_type,
                json.dumps(event_data),
                ip_address,
                user_agent,
                session_id,
            ),
            fetch=False,
        )
    except Exception as exc:
        logger.debug("Failed to log activity event: %s", exc)
