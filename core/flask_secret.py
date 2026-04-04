"""Flask session secret resolution (Render uses SECRET_KEY; docs often say FLASK_SECRET_KEY)."""

import os
from typing import Optional


def resolve_flask_secret_key() -> Optional[str]:
    env = os.getenv("FLASK_ENV", "production")
    if env == "development":
        return os.getenv("FLASK_SECRET_KEY", "dev-secret-key")
    return os.getenv("FLASK_SECRET_KEY") or os.getenv("SECRET_KEY") or None
