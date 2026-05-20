"""
Heuristic rules for automated operational / vendor notifications (Command Center triage).

Runs before generic intent hints to keep noreply@ alerts out of business_lead.
"""

from __future__ import annotations

import re
from typing import Any, Dict, Optional, Tuple

# Local-part and full-address automated senders
_AUTOMATED_LOCAL_RE = re.compile(
    r"(noreply|no-reply|donotreply|do-not-reply|notifications?|sc-noreply|mailer-daemon|bounce|alert)",
    re.I,
)

_HUMAN_SALES_INTENT_RE = re.compile(
    r"\b("
    r"interested in (your|a)|need help|looking for|would like (a )?quote|"
    r"request(ing)? (a )?quote|pricing for|send (me )?pricing|consultation|"
    r"automating my|help automating|can you help|how much (does|do|would)|"
    r"schedule a (call|demo)|speak with someone"
    r")\b",
    re.I,
)

_LEAD_KEYWORDS_RE = re.compile(
    r"\b(quote|estimate|consultation|interested in|pricing|rfp|proposal|demo)\b",
    re.I,
)

# Operational / product alert language (not inbound sales)
_OPERATIONAL_ALERT_RE = re.compile(
    r"\b("
    r"api usage|usage (has )?reached|notification threshold|threshold|"
    r"load balancer|ip address|upcoming change|will be enabled|"
    r"smart disputes|security alert|password reset|"
    r"congrats on reaching|\d+\s+clicks in|search console|"
    r"welcome to|join us (tomorrow|today)|entrepreneurs['’]? xchange|"
    r"kickoff|resources\s*&\s*upcoming events|vc fund"
    r")\b",
    re.I,
)

_EVENT_MARKETING_RE = re.compile(
    r"\b(join us|webinar|event|kickoff|newsletter|unsubscribe|rsvp|register now)\b",
    re.I,
)


def _sender_parts(sender_email: str) -> Tuple[str, str]:
    email = (sender_email or "").strip().lower()
    if "@" not in email:
        return email, ""
    local, domain = email.split("@", 1)
    return local, domain


def is_automated_sender(sender_email: str) -> bool:
    local, domain = _sender_parts(sender_email)
    if _AUTOMATED_LOCAL_RE.search(local):
        return True
    if domain and _AUTOMATED_LOCAL_RE.search(sender_email.lower()):
        return True
    return False


def has_human_sales_intent(subject: str, body: str) -> bool:
    text = f"{subject}\n{body}".strip()
    return bool(_HUMAN_SALES_INTENT_RE.search(text))


def has_strong_lead_keywords(subject: str, body: str) -> bool:
    text = f"{subject}\n{body}".strip()
    return bool(_LEAD_KEYWORDS_RE.search(text))


def match_operational_notification(
    *,
    subject: str,
    body: str,
    sender_email: str = "",
    sender_name: str = "",
) -> Optional[Dict[str, Any]]:
    """
    Return triage fields when message is a known automated notification pattern.
    None → continue with generic rules.
    """
    text = f"{subject}\n{body}".strip()
    lower = text.lower()
    local, domain = _sender_parts(sender_email)
    sender_l = (sender_email or "").lower()
    automated = is_automated_sender(sender_email)

    # Real inbound inquiry always wins (even from noreply domains — rare)
    if has_human_sales_intent(subject, body):
        return None

    # --- Domain / sender-specific (observed false positives) ---
    if "stripe.com" in domain or "notifications@stripe" in sender_l:
        if re.search(r"smart disputes|disputes will be enabled|billing|invoice|payment", lower):
            return _pack(
                "action_needed",
                15,
                35,
                55,
                0.88,
                "Stripe product/billing notification (operational).",
            )

    if "sentry.io" in domain or "noreply@sentry" in sender_l:
        if re.search(r"load balancer|ip address|upcoming change", lower):
            return _pack(
                "action_needed",
                10,
                30,
                60,
                0.88,
                "Sentry infrastructure change notice (operational).",
            )

    if "openai.com" in domain or "tm.openai.com" in domain:
        if re.search(r"api usage|usage has reached|notification threshold|threshold", lower):
            return _pack(
                "action_needed",
                10,
                25,
                55,
                0.9,
                "OpenAI API usage alert (operational).",
            )

    if "google.com" in domain or "sc-noreply" in local or "search-console" in lower:
        if re.search(r"search console|clicks in \d+ days|congrats on reaching", lower):
            return _pack(
                "newsletter_marketing",
                5,
                15,
                15,
                0.87,
                "Google Search Console performance notification.",
            )

    if "fau.edu" in domain or "innovatefau" in sender_l:
        if _EVENT_MARKETING_RE.search(lower) or re.search(
            r"vc fund|entrepreneurs|kickoff|resources.*upcoming", lower
        ):
            return _pack(
                "newsletter_marketing",
                8,
                20,
                20,
                0.85,
                "FAU entrepreneurship event/newsletter (not a direct sales inquiry).",
            )

    if "hihello.com" in domain or "hihello" in sender_l:
        if re.search(r"welcome to", lower):
            return _pack(
                "newsletter_marketing",
                5,
                10,
                10,
                0.86,
                "SaaS onboarding/welcome email.",
            )

    # --- Generic automated sender guard ---
    if not automated and not _OPERATIONAL_ALERT_RE.search(lower):
        return None

    if _OPERATIONAL_ALERT_RE.search(lower):
        if _EVENT_MARKETING_RE.search(lower) or re.search(
            r"welcome to|clicks in|search console|kickoff|join us", lower
        ):
            return _pack(
                "newsletter_marketing",
                8,
                18,
                18,
                0.84,
                "Automated event or product marketing notification.",
            )
        return _pack(
            "action_needed",
            12,
            28,
            50,
            0.83,
            "Automated operational alert (noreply/notification sender).",
        )

    if automated and has_strong_lead_keywords(subject, body):
        # Keyword overlap (e.g. "pricing" in marketing) without human intent
        return _pack(
            "review_needed",
            18,
            28,
            30,
            0.72,
            "Automated sender with lead-like keywords; needs human review.",
        )

    if automated:
        return _pack(
            "review_needed",
            15,
            25,
            28,
            0.7,
            "Automated sender without clear sales inquiry.",
        )

    return None


def cap_lead_if_automated(
    *,
    category: str,
    subject: str,
    body: str,
    sender_email: str,
) -> str:
    """Downgrade business_lead when sender is automated and lacks human sales intent."""
    if category != "business_lead":
        return category
    if has_human_sales_intent(subject, body):
        return category
    if not is_automated_sender(sender_email):
        return category
    lower = f"{subject}\n{body}".lower()
    if _EVENT_MARKETING_RE.search(lower) or re.search(
        r"welcome to|unsubscribe|search console|clicks in", lower
    ):
        return "newsletter_marketing"
    if _OPERATIONAL_ALERT_RE.search(lower):
        return "action_needed"
    return "review_needed"


def _pack(
    category: str,
    lead_score: int,
    biz_score: int,
    urgency: int,
    confidence: float,
    reason: str,
) -> Dict[str, Any]:
    return {
        "category": category,
        "lead_score": lead_score,
        "business_relevance_score": biz_score,
        "urgency_score": urgency,
        "confidence": confidence,
        "reason": reason,
        "classification_source": "rules",
        "signal": "operational_notification",
    }
