"""
Rewrite Gmail inline (cid:) image references to API proxy URLs and fix legacy path typos.
Used by live Gmail fetch and sync storage so <img> src points at GET /api/email/.../embedded-image/...
"""

from __future__ import annotations

import re
from typing import Any, Dict


def extract_embedded_image_map(payload: Dict[str, Any]) -> Dict[str, Dict[str, str]]:
    """Map Content-ID (without brackets) -> Gmail attachment id + mime type."""
    embedded: Dict[str, Dict[str, str]] = {}

    def extract_from_part(part: Dict[str, Any]) -> None:
        mime_type = part.get("mimeType", "")
        ph = part.get("headers", [])
        content_id = None
        for header in ph:
            if header.get("name", "").lower() == "content-id":
                content_id = header.get("value", "").strip("<>")
                break
        if content_id and part.get("body", {}).get("attachmentId"):
            embedded[content_id] = {
                "attachment_id": part["body"]["attachmentId"],
                "mime_type": mime_type,
            }
        if "parts" in part:
            for subpart in part["parts"]:
                extract_from_part(subpart)

    if "parts" in payload:
        for part in payload["parts"]:
            extract_from_part(part)
    else:
        extract_from_part(payload)
    return embedded


def rewrite_html_cid_to_proxy_urls(
    body_html: str,
    gmail_message_id: str,
    embedded_images: Dict[str, Dict[str, str]],
) -> str:
    """Replace cid: and bare content-id refs with same-origin API paths (browser loads with session/JWT via client)."""
    if not body_html or not embedded_images:
        return body_html or ""

    body = body_html
    for cid, img_info in embedded_images.items():
        proxy_url = f"/api/email/{gmail_message_id}/embedded-image/{img_info['attachment_id']}"
        cid_escaped = re.escape(cid.strip("<>"))
        body = re.sub(
            rf'src=["\']cid:{cid_escaped}["\']',
            f'src="{proxy_url}"',
            body,
            flags=re.IGNORECASE,
        )
        body = re.sub(rf"cid:{cid_escaped}", proxy_url, body, flags=re.IGNORECASE)
        body = re.sub(
            rf'src=["\']{cid_escaped}["\']',
            f'src="{proxy_url}"',
            body,
            flags=re.IGNORECASE,
        )
    return body


def fix_legacy_embedded_image_api_paths(html: str) -> str:
    """Older builds incorrectly used /api/business/email/...; route is /api/email/..."""
    if not html:
        return html
    return html.replace("/api/business/email/", "/api/email/")
