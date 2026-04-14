"""
HTTPS endpoint for Google Cross-Account Protection (RISC) security event tokens.
"""

import logging

from flask import Blueprint, request

from core.google_risc import is_risc_enabled, process_security_event_token_string

logger = logging.getLogger(__name__)

google_risc_bp = Blueprint("google_risc", __name__, url_prefix="/api/webhooks/google")


@google_risc_bp.route("/risc", methods=["POST"])
def receive_google_risc_event():
    """
    Google POSTs a signed JWT (security event token). Validate and return 202 on success.
    """
    if not is_risc_enabled():
        return "", 404

    raw = request.get_data(as_text=True)
    ok, err = process_security_event_token_string(raw)
    if not ok:
        return {"error": err or "bad_request"}, 400
    return "", 202
