"""
Shared HTML branding for outbound emails (transactional SMTP, contact form, etc.).
Logo is served from the frontend public/ path so the URL stays stable across builds.
"""

from __future__ import annotations

import html
import os

from config import config as app_config

DEFAULT_BRAND_TAGLINE = "Stop losing time and high-value leads"


def get_email_logo_url() -> str:
    override = (os.getenv("EMAIL_LOGO_URL") or "").strip()
    if override:
        return override
    base = app_config.get_frontend_url().rstrip("/")
    return f"{base}/fikiri-email-logo.png"


def get_email_brand_tagline() -> str:
    return (os.getenv("EMAIL_BRAND_TAGLINE") or DEFAULT_BRAND_TAGLINE).strip() or DEFAULT_BRAND_TAGLINE


def get_email_home_url() -> str:
    return app_config.get_frontend_url().rstrip("/")


def wrap_html_email_body(inner_html: str) -> str:
    """
    Wrap inner HTML (no outer document) with header (logo + tagline) and footer.
    inner_html must be safe HTML from our own templates; do not pass raw user input unescaped.
    """
    logo_url = html.escape(get_email_logo_url(), quote=True)
    home_url = html.escape(get_email_home_url(), quote=True)
    tagline = html.escape(get_email_brand_tagline())
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Fikiri Solutions</title>
</head>
<body style="font-family: Arial, Helvetica, sans-serif; line-height: 1.6; color: #333333; margin: 0; padding: 0; background-color: #f8fafc;">
<div style="max-width: 600px; margin: 0 auto; padding: 24px 20px;">
<div style="background-color: #ffffff; border-radius: 8px; overflow: hidden; box-shadow: 0 1px 3px rgba(15, 23, 42, 0.08);">
<div style="text-align: center; padding: 28px 24px 20px; border-bottom: 1px solid #e2e8f0;">
<a href="{home_url}" style="text-decoration: none; display: inline-block;">
<img src="{logo_url}" alt="Fikiri Solutions" width="220" style="max-width: 220px; height: auto; border: 0; display: block; margin: 0 auto;" />
</a>
<p style="margin: 14px 0 0; font-size: 15px; color: #64748b; font-weight: 500;">{tagline}</p>
</div>
<div style="padding: 24px;">
{inner_html}
</div>
<div style="padding: 16px 24px 24px; border-top: 1px solid #e2e8f0; font-size: 12px; color: #94a3b8; text-align: center;">
<p style="margin: 0;">© Fikiri Solutions · <a href="{home_url}" style="color: #2563eb; text-decoration: none;">fikirisolutions.com</a></p>
</div>
</div>
</div>
</body>
</html>"""
