"""
Deterministic text chunking for chatbot knowledge vector ingestion.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List

_SENTENCE_BOUNDARY = re.compile(r"(?<=[.!?])\s+")


@dataclass(frozen=True)
class TextChunk:
    text: str
    chunk_index: int
    total_chunks: int


def chunk_text(text: str, max_chars: int = 1200, overlap_chars: int = 150) -> List[TextChunk]:
    """
    Split text into overlapping chunks for vector indexing.

    Prefers paragraph boundaries, then sentence boundaries, then hard character splits.
    """
    normalized = (text or "").strip()
    if not normalized:
        return []

    if max_chars <= 0:
        max_chars = 1200
    if overlap_chars < 0:
        overlap_chars = 0
    if overlap_chars >= max_chars:
        overlap_chars = max(0, max_chars // 4)

    if len(normalized) <= max_chars:
        return [TextChunk(text=normalized, chunk_index=0, total_chunks=1)]

    raw_chunks = _pack_paragraphs(_split_paragraphs(normalized, max_chars), max_chars)
    if overlap_chars > 0 and len(raw_chunks) > 1:
        raw_chunks = _apply_overlap(raw_chunks, overlap_chars, max_chars)

    total = len(raw_chunks)
    return [
        TextChunk(text=chunk, chunk_index=index, total_chunks=total)
        for index, chunk in enumerate(raw_chunks)
    ]


def chunk_vector_id(parent_doc_id: str, chunk_index: int, total_chunks: int) -> str:
    if total_chunks <= 1:
        return parent_doc_id
    return f"{parent_doc_id}__chunk_{chunk_index}"


def _split_paragraphs(text: str, max_chars: int) -> List[str]:
    parts = re.split(r"\n\s*\n", text)
    blocks: List[str] = []
    for part in parts:
        block = part.strip()
        if not block:
            continue
        if len(block) <= max_chars:
            blocks.append(block)
            continue
        blocks.extend(_split_long_block(block, max_chars))
    return blocks


def _split_long_block(block: str, max_chars: int) -> List[str]:
    if len(block) <= max_chars:
        return [block]

    sentences = _SENTENCE_BOUNDARY.split(block)
    sentences = [s.strip() for s in sentences if s.strip()]
    if len(sentences) <= 1:
        return _split_by_chars(block, max_chars)

    pieces: List[str] = []
    current = ""
    for sentence in sentences:
        candidate = sentence if not current else f"{current} {sentence}"
        if len(candidate) <= max_chars:
            current = candidate
            continue
        if current:
            pieces.append(current)
        if len(sentence) <= max_chars:
            current = sentence
        else:
            pieces.extend(_split_by_chars(sentence, max_chars))
            current = ""
    if current:
        pieces.append(current)
    return pieces


def _split_by_chars(text: str, max_chars: int) -> List[str]:
    if len(text) <= max_chars:
        return [text]
    parts: List[str] = []
    start = 0
    while start < len(text):
        parts.append(text[start : start + max_chars])
        start += max_chars
    return parts


def _pack_paragraphs(paragraphs: List[str], max_chars: int) -> List[str]:
    if not paragraphs:
        return []

    chunks: List[str] = []
    current = ""
    for paragraph in paragraphs:
        if len(paragraph) > max_chars:
            if current:
                chunks.append(current)
                current = ""
            chunks.extend(_split_long_block(paragraph, max_chars))
            continue

        candidate = paragraph if not current else f"{current}\n\n{paragraph}"
        if len(candidate) <= max_chars:
            current = candidate
            continue

        if current:
            chunks.append(current)
        current = paragraph

    if current:
        chunks.append(current)
    return chunks


def _apply_overlap(chunks: List[str], overlap_chars: int, max_chars: int) -> List[str]:
    if overlap_chars <= 0 or len(chunks) <= 1:
        return chunks

    overlapped = [chunks[0]]
    for index in range(1, len(chunks)):
        previous = chunks[index - 1]
        prefix = previous[-overlap_chars:] if len(previous) > overlap_chars else previous
        combined = f"{prefix}\n\n{chunks[index]}" if prefix else chunks[index]
        if len(combined) > max_chars:
            combined = combined[-max_chars:]
        overlapped.append(combined)
    return overlapped
