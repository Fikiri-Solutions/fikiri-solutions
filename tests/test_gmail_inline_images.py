"""Tests for core.gmail_inline_images."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.gmail_inline_images import (  # noqa: E402
    fix_legacy_embedded_image_api_paths,
    rewrite_html_cid_to_proxy_urls,
)


def test_fix_legacy_path():
    html = '<img src="/api/business/email/msg1/embedded-image/att1">'
    out = fix_legacy_embedded_image_api_paths(html)
    assert "/api/business/email/" not in out
    assert "/api/email/msg1/embedded-image/att1" in out


def test_rewrite_cid():
    emb = {"logo": {"attachment_id": "ATT", "mime_type": "image/png"}}
    html = '<html><body><img src="cid:logo"></body></html>'
    out = rewrite_html_cid_to_proxy_urls(html, "msg1", emb)
    assert 'src="/api/email/msg1/embedded-image/ATT"' in out
    assert "cid:" not in out
