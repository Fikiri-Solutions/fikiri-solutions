"""Service-family taxonomy and pain-language navigation for the site bot."""

from __future__ import annotations

import re
from typing import Dict, List, Sequence, Set, Tuple

# Client pain → service area (not rigid product SKUs).
FAMILY_INBOX_EMAIL = "inbox_email"
FAMILY_LEAD_FOLLOWUP = "lead_followup"
FAMILY_CRM_TRACKING = "crm_tracking"
FAMILY_WORKFLOW_AUDIT = "workflow_audit"
FAMILY_WEBSITES_INTAKE = "websites_intake"
FAMILY_SITE_CHATBOT = "site_chatbot"
FAMILY_CONSULTING = "consulting"
FAMILY_PRICING = "pricing"
FAMILY_COMPANY = "company"
FAMILY_CONTACT = "contact"
FAMILY_INDUSTRIES = "industries"
FAMILY_BOUNDARIES = "boundaries"

FAMILY_LABELS: Dict[str, str] = {
    FAMILY_INBOX_EMAIL: "inbox and email workflow automation",
    FAMILY_LEAD_FOLLOWUP: "lead capture and follow-up",
    FAMILY_CRM_TRACKING: "CRM and customer tracking",
    FAMILY_WORKFLOW_AUDIT: "workflow audit and process discovery",
    FAMILY_WEBSITES_INTAKE: "intake forms and workflow review paths",
    FAMILY_SITE_CHATBOT: "site chat and knowledge assistant",
    FAMILY_CONSULTING: "business automation consulting",
    FAMILY_PRICING: "pricing and plans",
    FAMILY_COMPANY: "what Fikiri does for small teams",
    FAMILY_CONTACT: "contact and next steps",
    FAMILY_INDUSTRIES: "industry-specific workflow fit",
    FAMILY_BOUNDARIES: "scope boundaries",
}

_PAIN_FAMILY_RULES: Tuple[Tuple[str, re.Pattern[str], float], ...] = (
    (
        FAMILY_INBOX_EMAIL,
        re.compile(
            r"drowning in emails|too many emails|sort my inbox|automate my inbox|"
            r"reply to emails|manually replying|help with gmail|gmail stuff|"
            r"outlook automation|missed emails|inbox assistant|email assistant|"
            r"can you automate my inbox|tired of manually replying|"
            r"messages sitting in gmail|messages sitting in outlook",
            re.I,
        ),
        1.0,
    ),
    (
        FAMILY_LEAD_FOLLOWUP,
        re.compile(
            r"slipping through the cracks|stop missing leads|missing leads|"
            r"incoming leads|follow up automatically|follow ups|follow-ups|"
            r"need something that follows up|appointment requests|website form|"
            r"nobody follows up|quotes without follow|system for incoming leads|"
            r"leads leak|missed leads",
            re.I,
        ),
        1.0,
    ),
    (
        FAMILY_CRM_TRACKING,
        re.compile(
            r"managing customers|help managing customers|track customers|"
            r"keep track of customers|stop losing leads|customer list|lead tracker|"
            r"sales pipeline|where are my clients|something like a crm|"
            r"build something like a crm|following up with customers|"
            r"customer tracking|lead tracking",
            re.I,
        ),
        0.95,
    ),
    (
        FAMILY_WORKFLOW_AUDIT,
        re.compile(
            r"not sure where to start|map (?:this|our) workflow|process discovery|"
            r"where (?:time|leads) leak|workflow audit|operations audit|"
            r"general workflow automation|not sure yet",
            re.I,
        ),
        0.9,
    ),
    (
        FAMILY_WEBSITES_INTAKE,
        re.compile(
            r"website form|intake form|build websites|wordpress|web design",
            re.I,
        ),
        0.85,
    ),
    (
        FAMILY_CONSULTING,
        re.compile(
            r"cleaning business|small business|florida smb|done for you|"
            r"implementation help|need a quote|help automate",
            re.I,
        ),
        0.8,
    ),
    (
        FAMILY_PRICING,
        re.compile(r"\b(price|pricing|cost|plan|trial|starter|how much)\b", re.I),
        0.75,
    ),
)

_CHUNK_DEFAULT_FAMILIES: Dict[str, Tuple[str, ...]] = {
    "product_ai_email_assistant": (FAMILY_INBOX_EMAIL, FAMILY_LEAD_FOLLOWUP),
    "product_email_overview": (FAMILY_INBOX_EMAIL,),
    "product_email_classify": (FAMILY_INBOX_EMAIL,),
    "product_email_draft": (FAMILY_INBOX_EMAIL,),
    "product_email_assistant_goal": (FAMILY_INBOX_EMAIL, FAMILY_LEAD_FOLLOWUP),
    "integration_gmail": (FAMILY_INBOX_EMAIL,),
    "integration_outlook": (FAMILY_INBOX_EMAIL,),
    "product_crm_overview": (FAMILY_CRM_TRACKING, FAMILY_LEAD_FOLLOWUP),
    "product_crm_activity": (FAMILY_CRM_TRACKING, FAMILY_LEAD_FOLLOWUP),
    "product_crm_practical": (FAMILY_CRM_TRACKING,),
    "workflow_inquiry_leak": (FAMILY_LEAD_FOLLOWUP, FAMILY_WORKFLOW_AUDIT),
    "service_workflow_audit": (FAMILY_WORKFLOW_AUDIT,),
    "service_workflow_audit_focus": (FAMILY_WORKFLOW_AUDIT,),
    "contact_intake_path": (FAMILY_WORKFLOW_AUDIT, FAMILY_WEBSITES_INTAKE),
    "service_consulting": (FAMILY_CONSULTING,),
    "site_chat_widget": (FAMILY_SITE_CHATBOT,),
}

_BRIDGE_HINTS: Dict[str, str] = {
    FAMILY_INBOX_EMAIL: "If messages are piling up in Gmail or Outlook, that usually fits email automation.",
    FAMILY_CRM_TRACKING: "If the issue is tracking leads and customers after first contact, that fits CRM work.",
    FAMILY_LEAD_FOLLOWUP: "If follow-ups are getting missed after inquiries come in, that fits lead follow-up automation.",
    FAMILY_WORKFLOW_AUDIT: "If you are not sure which part is breaking, a workflow audit maps that out first.",
}

_DISAMBIGUATION = (
    "That could fall under a few Fikiri areas. Are you mainly trying to fix email replies, "
    "lead tracking, customer follow-up, or map the overall workflow?"
)


def infer_service_families(normalized_query: str) -> List[Tuple[str, float]]:
    hits: List[Tuple[str, float]] = []
    for family, pattern, weight in _PAIN_FAMILY_RULES:
        if pattern.search(normalized_query):
            hits.append((family, weight))
    return hits


def chunk_service_families(chunk: object) -> Set[str]:
    families = getattr(chunk, "service_families", None) or []
    if families:
        return set(families)
    return set(_CHUNK_DEFAULT_FAMILIES.get(getattr(chunk, "id", ""), ()))


def family_match_boost(inferred: List[Tuple[str, float]], chunk: object) -> float:
    if not inferred:
        return 0.0
    chunk_families = chunk_service_families(chunk)
    if not chunk_families:
        return 0.0
    inferred_set = {family for family, _ in inferred}
    overlap = chunk_families & inferred_set
    if not overlap:
        return 0.0
    best = max(score for family, score in inferred if family in overlap)
    if best >= 0.95:
        return 0.32
    if best >= 0.85:
        return 0.22
    return 0.12


def families_in_chunks(chunks: Sequence[object]) -> List[str]:
    ordered: List[str] = []
    seen: Set[str] = set()
    for chunk in chunks:
        for family in chunk_service_families(chunk):
            if family not in seen:
                seen.add(family)
                ordered.append(family)
    return ordered


def is_ambiguous_families(inferred: List[Tuple[str, float]], scores: Sequence[float]) -> bool:
    if len(inferred) < 2:
        return False
    strong = [family for family, weight in inferred if weight >= 0.9]
    if len(strong) < 2:
        return False
    if len(scores) < 2:
        return False
    return abs(scores[0] - scores[1]) <= 0.18


def compose_bridge_response(query: str, chunks: Sequence[object], families: Sequence[str]) -> str:
  # Use verified KB text only; add navigation hints between families.
    primary = chunks[0].text.strip() if chunks else ""
    family_labels = [FAMILY_LABELS.get(f, f.replace("_", " ")) for f in families[:3]]
    if not family_labels:
        return primary or (
            "I can help map your workflow to the right Fikiri services. "
            "Tell me more about what you're trying to fix."
        )
    opener = (
        f"That sounds closest to Fikiri's {family_labels[0]}"
        + (f" and {family_labels[1]}" if len(family_labels) > 1 else "")
        + " work."
    )
    hints = " ".join(_BRIDGE_HINTS[f] for f in families[:3] if f in _BRIDGE_HINTS)
    audit = _BRIDGE_HINTS[FAMILY_WORKFLOW_AUDIT]
    if FAMILY_WORKFLOW_AUDIT not in families and len(families) > 1:
        hints = f"{hints} {audit}".strip()
    return f"{opener} {primary} {hints}".strip()


def compose_disambiguation() -> str:
    return _DISAMBIGUATION
