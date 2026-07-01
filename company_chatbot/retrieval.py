"""Deterministic KB retrieval for the Fikiri site bot (no vectors, no LLM)."""

from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple

from company_chatbot import config
from company_chatbot.service_families import (
    families_in_chunks,
    family_match_boost,
    infer_service_families,
    is_ambiguous_families,
)

_TOKEN_RE = re.compile(r"[a-z0-9]+")
_HYPHEN_AI_ASSISTANT_RE = re.compile(r"ai-assistant", re.I)

STOPWORDS = frozenset(
    {
        "i",
        "me",
        "my",
        "need",
        "want",
        "find",
        "out",
        "about",
        "the",
        "a",
        "an",
        "to",
        "for",
        "of",
        "one",
        "some",
        "can",
        "you",
        "tell",
        "explain",
        "help",
        "with",
        "is",
        "are",
        "do",
        "does",
        "what",
        "how",
        "much",
        "im",
        "your",
        "our",
        "we",
        "it",
        "that",
        "this",
        "be",
        "or",
        "and",
        "in",
        "on",
        "at",
        "if",
        "any",
        "have",
        "has",
        "get",
        "got",
    }
)

_TYPO_REPLACEMENTS = (
    ("assisant", "assistant"),
    ("assitant", "assistant"),
    ("assit", "assist"),
    ("producsts", "products"),
    ("producst", "product"),
    ("automations", "automation"),
)

_TOPIC_RULES: Tuple[Tuple[str, re.Pattern[str], float], ...] = (
    ("pricing", re.compile(r"\b(price|pricing|cost|plan|trial|starter|growth|business|enterprise|\$?\d{2,3}|how much|free trial|sign up|signup)\b", re.I), 1.0),
    ("product_email", re.compile(r"\b(email assistant|ai email|email automation|inbox assistant|inbox|draft repl|classify|triage)\b", re.I), 1.0),
    ("product_crm", re.compile(r"\b(crm|leads?|pipeline|contacts?|lead management)\b", re.I), 1.0),
    ("workflow_audit", re.compile(r"\b(workflow audit|process audit|intake|operations audit|audit our)\b", re.I), 1.0),
    ("integrations", re.compile(r"\b(gmail|outlook|google workspace|microsoft 365|integration)\b", re.I), 0.85),
    ("services", re.compile(r"\b(consulting|implementation|done[- ]for[- ]you|system fixers|custom build)\b", re.I), 0.9),
    ("industries", re.compile(r"\b(landscap|restaurant|dental|medical|clinic|hvac|trades|contractor|hospitality|lawn)\b", re.I), 0.95),
    ("boundaries", re.compile(r"\b(hipaa|soc\s*2|soc2|case stud|certified|compliance|guarantee|website design|web design|wordpress|build websites)\b", re.I), 1.0),
    ("company", re.compile(r"\b(what do you do|what does fikiri|who is fikiri|what is fikiri|florida smb|capabilities|offerings?)\b", re.I), 0.9),
    ("contact", re.compile(r"\b(contact|reach|talk to|get in touch|info@|email me|support team)\b", re.I), 0.85),
)

_PHRASE_CHUNK_BOOSTS: Tuple[Tuple[str, Tuple[str, ...]], ...] = (
    ("ai email assistant", ("product_ai_email_assistant", "product_email_assistant_goal")),
    ("email assistant", ("product_ai_email_assistant", "product_email_assistant_goal", "product_email_overview")),
    ("email automation", ("product_email_overview", "product_ai_email_assistant", "product_email_classify")),
    ("workflow audit", ("service_workflow_audit", "service_workflow_audit_focus", "contact_intake_path")),
    ("starter plan", ("pricing_starter",)),
    ("free trial", ("faq_free_trial", "signup_trial")),
    ("lead management", ("product_crm_overview", "product_crm_activity")),
    ("gmail", ("integration_gmail", "product_ai_email_assistant")),
    ("outlook", ("integration_outlook", "product_ai_email_assistant")),
    ("crm", ("product_crm_overview", "product_crm_activity", "product_crm_practical")),
    ("what do you do", ("company_about", "company_three_capabilities")),
    ("what does fikiri", ("company_about", "company_three_capabilities")),
    ("who is fikiri", ("company_about",)),
    ("how much is starter", ("pricing_starter",)),
    ("starter price", ("pricing_starter",)),
    ("florida smb", ("company_florida_smb", "service_consulting")),
    ("help me", ("site_chat_widget",)),
    ("drowning in emails", ("product_ai_email_assistant", "product_email_classify")),
    ("too many emails", ("product_ai_email_assistant", "product_email_overview")),
    ("automate my inbox", ("product_ai_email_assistant", "product_email_overview")),
    ("missing leads", ("product_email_assistant_goal", "workflow_inquiry_leak", "product_crm_overview")),
    ("stop missing leads", ("product_email_assistant_goal", "workflow_inquiry_leak", "product_crm_overview")),
    ("slipping through the cracks", ("workflow_inquiry_leak", "product_crm_overview", "product_email_assistant_goal")),
    ("follow up automatically", ("product_email_draft", "product_crm_activity", "product_ai_email_assistant")),
    ("managing customers", ("product_crm_overview", "product_crm_practical")),
    ("track customers", ("product_crm_overview", "product_crm_activity")),
    ("gmail stuff", ("integration_gmail", "product_ai_email_assistant")),
    ("reply to emails", ("product_email_draft", "product_ai_email_assistant")),
    ("incoming leads", ("workflow_inquiry_leak", "product_crm_overview", "product_email_assistant_goal")),
    ("something like a crm", ("product_crm_overview", "product_crm_practical")),
    ("website form", ("workflow_inquiry_leak", "contact_intake_path")),
    ("appointment requests", ("workflow_inquiry_leak", "industry_dental_medical")),
)

_CHUNK_TOPIC_FROM_INTENT: Dict[str, str] = {
    "pricing_starter": "pricing",
    "pricing_growth": "pricing",
    "pricing_business": "pricing",
    "pricing_enterprise": "pricing",
    "pricing_trial": "pricing",
    "product_email_assistant": "product_email",
    "product_email": "product_email",
    "product_crm": "product_crm",
    "workflow_audit": "workflow_audit",
    "integration": "integrations",
    "industry": "industries",
    "boundary": "boundaries",
    "company": "company",
    "contact": "contact",
    "service": "services",
}


@dataclass
class KBChunk:
    id: str
    text: str
    topic: str
    source_url: str
    keywords: List[str] = field(default_factory=list)
    intent: str = ""
    aliases: List[str] = field(default_factory=list)
    negative_keywords: List[str] = field(default_factory=list)
    service_families: List[str] = field(default_factory=list)

    def to_source_dict(self, score: float) -> Dict[str, object]:
        return {
            "id": self.id,
            "topic": self.topic,
            "source_url": self.source_url,
            "score": round(score, 4),
        }


@dataclass
class RetrievalResult:
    query: str
    chunks: List[KBChunk] = field(default_factory=list)
    scores: List[float] = field(default_factory=list)
    service_families: List[str] = field(default_factory=list)
    ambiguous_families: bool = False
    needs: Dict[str, Any] = field(default_factory=dict)

    @property
    def best_score(self) -> float:
        return self.scores[0] if self.scores else 0.0

    def source_dicts(self) -> List[Dict[str, object]]:
        return [chunk.to_source_dict(score) for chunk, score in zip(self.chunks, self.scores)]


@dataclass(frozen=True)
class _CorpusIndex:
    chunks: Tuple[KBChunk, ...]
    idf: Dict[str, float]
    chunk_body_tokens: Dict[str, Set[str]]
    chunk_keyword_tokens: Dict[str, Set[str]]


def normalize_query_text(text: str) -> str:
    lowered = (text or "").lower()
    lowered = _HYPHEN_AI_ASSISTANT_RE.sub("ai assistant", lowered)
    for old, new in _TYPO_REPLACEMENTS:
        lowered = lowered.replace(old, new)
    return lowered


def tokenize(text: str) -> Set[str]:
    return set(_TOKEN_RE.findall(normalize_query_text(text)))


def _retrieval_tokens(text: str) -> Set[str]:
    return {token for token in tokenize(text) if token not in STOPWORDS}


_STANDALONE_TOPIC_RE = re.compile(
    r"\b(how much|price|pricing|starter plan|growth plan|business plan|enterprise plan|"
    r"free trial|\$\d{2,3}|talk to|contact|hipaa|soc\s*2)\b",
    re.I,
)


def is_standalone_topic_query(query: str) -> bool:
    return bool(_STANDALONE_TOPIC_RE.search(normalize_query_text(query)))


def effective_query_for_retrieval(query: str, previous_query: str | None = None) -> str:
    current = (query or "").strip()
    previous = (previous_query or "").strip()
    if not current or not previous:
        return current
    if is_standalone_topic_query(current):
        return current
    content_tokens = _retrieval_tokens(current)
    if len(content_tokens) <= 3 or len(current) <= 32:
        return f"{previous} {current}"
    return current


def _infer_router_topics(normalized_query: str) -> List[Tuple[str, float]]:
    hits: List[Tuple[str, float]] = []
    for topic, pattern, weight in _TOPIC_RULES:
        if pattern.search(normalized_query):
            hits.append((topic, weight))
    return hits


def _chunk_router_topic(chunk: KBChunk) -> str:
    intent = (chunk.intent or "").lower()
    if intent:
        for prefix, topic in _CHUNK_TOPIC_FROM_INTENT.items():
            if intent.startswith(prefix) or prefix in intent:
                return topic
    chunk_id = chunk.id.lower()
    topic = chunk.topic.lower()
    if topic == "pricing":
        return "pricing"
    if topic == "integrations":
        return "integrations"
    if topic == "services":
        return "workflow_audit" if "audit" in chunk_id else "services"
    if topic == "industries":
        return "industries"
    if topic == "boundaries":
        return "boundaries"
    if topic == "contact":
        return "contact"
    if topic == "company":
        return "company"
    if "crm" in chunk_id:
        return "product_crm"
    if "email" in chunk_id or "gmail" in chunk_id or "outlook" in chunk_id:
        return "product_email" if topic == "product" else "integrations"
    if topic == "product":
        return "product_email"
    return topic or "company"


def _topic_adjustment(router_topics: List[Tuple[str, float]], chunk: KBChunk) -> float:
    if not router_topics:
        return 0.0
    chunk_topic = _chunk_router_topic(chunk)
    matching = [score for topic, score in router_topics if topic == chunk_topic]
    if matching:
        best_match = max(matching)
        if best_match >= 0.85:
            return 0.28
        if best_match >= 0.7:
            return 0.18
    best_mismatch = max((score for topic, score in router_topics if topic != chunk_topic), default=0.0)
    primary_topic = router_topics[0][0]
    if best_mismatch >= 0.95 and chunk_topic != primary_topic:
        return -0.12
    return 0.0


def _phrase_boost(normalized_query: str, chunk: KBChunk) -> float:
    boost = 0.0
    for alias in chunk.aliases:
        alias_norm = normalize_query_text(alias)
        if alias_norm and alias_norm in normalized_query:
            boost = max(boost, 0.55)
    for phrase, chunk_ids in _PHRASE_CHUNK_BOOSTS:
        if phrase in normalized_query and chunk.id in chunk_ids:
            boost = max(boost, 0.5)
    return boost


def _negative_penalty(normalized_query: str, chunk: KBChunk) -> float:
    penalty = 0.0
    for term in chunk.negative_keywords:
        term_norm = normalize_query_text(term)
        if term_norm and term_norm in normalized_query:
            penalty += 0.35
    return min(penalty, 0.7)


def _build_corpus_index(chunks: List[KBChunk]) -> _CorpusIndex:
    doc_count = max(len(chunks), 1)
    df: Dict[str, int] = {}
    body_tokens: Dict[str, Set[str]] = {}
    keyword_tokens: Dict[str, Set[str]] = {}

    for chunk in chunks:
        body = _retrieval_tokens(chunk.text)
        keywords = _retrieval_tokens(" ".join(chunk.keywords + chunk.aliases))
        body_tokens[chunk.id] = body
        keyword_tokens[chunk.id] = keywords
        for token in body | keywords:
            df[token] = df.get(token, 0) + 1

    idf = {token: math.log((doc_count + 1) / (count + 1)) + 1.0 for token, count in df.items()}
    return _CorpusIndex(
        chunks=tuple(chunks),
        idf=idf,
        chunk_body_tokens=body_tokens,
        chunk_keyword_tokens=keyword_tokens,
    )


def score_chunk(
    query_tokens: Set[str],
    chunk: KBChunk,
    *,
    index: _CorpusIndex | None = None,
    normalized_query: str = "",
) -> float:
    corpus = index or _get_corpus_index()
    normalized = normalized_query or normalize_query_text(" ".join(query_tokens))
    tokens = {token for token in query_tokens if token not in STOPWORDS}
    if not tokens:
        tokens = set(query_tokens)

    phrase = _phrase_boost(normalized, chunk)
    topic = _topic_adjustment(_infer_router_topics(normalized), chunk)
    penalty = _negative_penalty(normalized, chunk)
    family = family_match_boost(infer_service_families(normalized), chunk)

    if not tokens:
        return max(0.0, min(1.5, phrase + topic + family - penalty))

    body = corpus.chunk_body_tokens.get(chunk.id, set())
    keywords = corpus.chunk_keyword_tokens.get(chunk.id, set())
    idf = corpus.idf

    body_hits = tokens & body
    keyword_hits = tokens & keywords
    query_weight = sum(idf.get(token, 1.0) for token in tokens) or 1.0
    body_score = sum(idf.get(token, 1.0) for token in body_hits) / query_weight
    keyword_score = sum(idf.get(token, 1.0) * 1.8 for token in keyword_hits) / query_weight

    score = body_score * 0.55 + keyword_score * 0.45
    score += phrase + topic + family - penalty
    return max(0.0, min(1.5, score))


def load_kb_chunks(path: Path | None = None) -> List[KBChunk]:
    kb_path = path or (config.kb_data_dir() / "fikiri_kb_chunks.jsonl")
    if not kb_path.is_file():
        return []

    chunks: List[KBChunk] = []
    for line in kb_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        row = json.loads(line)
        chunks.append(
            KBChunk(
                id=str(row["id"]),
                text=str(row["text"]),
                topic=str(row.get("topic", "general")),
                source_url=str(row.get("source_url", "")),
                keywords=[str(k) for k in row.get("keywords", [])],
                intent=str(row.get("intent", "") or ""),
                aliases=[str(a) for a in row.get("aliases", [])],
                negative_keywords=[str(n) for n in row.get("negative_keywords", [])],
                service_families=[str(f) for f in row.get("service_families", [])],
            )
        )
    return chunks


@lru_cache(maxsize=1)
def _get_corpus_index() -> _CorpusIndex:
    return _build_corpus_index(load_kb_chunks())


def clear_kb_cache_for_tests() -> None:
    _get_corpus_index.cache_clear()
    from company_chatbot.capabilities import clear_capability_map_cache_for_tests

    clear_capability_map_cache_for_tests()


def retrieve(
    query: str,
    top_k: int | None = None,
    *,
    previous_query: str | None = None,
) -> RetrievalResult:
    limit = top_k or config.retrieval_top_k()
    effective = effective_query_for_retrieval(query, previous_query)
    normalized = normalize_query_text(effective)
    query_tokens = _retrieval_tokens(effective)
    if not query_tokens:
        query_tokens = tokenize(effective)

    from company_chatbot.capabilities import (
        capability_chunk_boost,
        detect_needs,
        legacy_families_from_needs,
    )

    needs = detect_needs(query, previous_query=previous_query, effective_query=effective)

    corpus = _get_corpus_index()
    ranked: List[Tuple[float, KBChunk]] = []
    for chunk in corpus.chunks:
        score = score_chunk(query_tokens, chunk, index=corpus, normalized_query=normalized)
        score += capability_chunk_boost(chunk.id, needs)
        if score > 0:
            ranked.append((score, chunk))

    ranked.sort(key=lambda item: (-item[0], item[1].id))
    top = ranked[:limit]
    top_chunks = [chunk for _, chunk in top]
    top_scores = [score for score, _ in top]
    inferred = infer_service_families(normalized)
    legacy = legacy_families_from_needs(needs)
    service_fams = list(
        dict.fromkeys(families_in_chunks(top_chunks) or legacy or [f for f, _ in inferred[:3]])
    )
    return RetrievalResult(
        query=effective,
        chunks=top_chunks,
        scores=top_scores,
        service_families=service_fams,
        ambiguous_families=is_ambiguous_families(inferred, top_scores)
        or len(needs.detected_families) >= 2,
        needs=needs.to_dict(),
    )
