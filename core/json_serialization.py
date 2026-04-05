"""JSON helpers for API/session payloads that may include datetimes (e.g. UserProfile)."""

import json
from datetime import datetime
from typing import Any


def json_dumps_user_payload(obj: Any) -> str:
    """Serialize dicts for Redis/SQLite; UserProfile includes datetime (e.g. created_at)."""
    def _default(o: Any) -> Any:
        if isinstance(o, datetime):
            return o.isoformat()
        return str(o)

    return json.dumps(obj, default=_default)
