"""Workflow document generation helpers."""

import io
import json
from datetime import datetime
from typing import Dict, Any

from core.document_templates_system import get_document_templates, TemplateFormat


def _escape_pdf_text(text: str) -> str:
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _simple_pdf_bytes(text: str) -> bytes:
    # Minimal single-page PDF with Helvetica font
    escaped = _escape_pdf_text(text)
    content_stream = f"BT /F1 12 Tf 72 720 Td ({escaped}) Tj ET"
    content_bytes = content_stream.encode("latin-1", errors="ignore")

    objects = []
    objects.append(b"1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n")
    objects.append(b"2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj\n")
    objects.append(b"3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >> endobj\n")
    objects.append(f"4 0 obj << /Length {len(content_bytes)} >> stream\n".encode("latin-1"))
    objects.append(content_bytes + b"\nendstream endobj\n")
    objects.append(b"5 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj\n")

    xref = [b"0000000000 65535 f \n"]
    offset = 9  # length of header below
    offsets = [offset]
    for obj in objects:
        offsets.append(offset)
        offset += len(obj)

    xref_entries = [b"0000000000 65535 f \n"]
    for off in offsets[1:]:
        xref_entries.append(f"{off:010d} 00000 n \n".encode("latin-1"))

    xref_start = offset
    trailer = f"trailer << /Size {len(xref_entries)} /Root 1 0 R >>\nstartxref\n{xref_start}\n%%EOF\n".encode("latin-1")

    pdf = b"%PDF-1.4\n" + b"".join(objects) + b"xref\n0 " + str(len(xref_entries)).encode("latin-1") + b"\n" + b"".join(xref_entries) + trailer
    return pdf


def generate_document(template_id: str, variables: Dict[str, Any], user_id: int, output_format: str) -> Dict[str, Any]:
    doc_templates = get_document_templates()
    document = doc_templates.generate_document(template_id, variables, user_id)

    content = document.content
    fmt = output_format.lower()

    if fmt == TemplateFormat.PDF.value:
        pdf_bytes = _simple_pdf_bytes(content)
        return {
            "document": document,
            "content_bytes": pdf_bytes,
            "content_type": "application/pdf",
            "filename": f"{template_id}_{document.id}.pdf",
            "format": fmt
        }

    if fmt in {TemplateFormat.HTML.value, TemplateFormat.MARKDOWN.value, TemplateFormat.TXT.value}:
        content_type = "text/plain" if fmt == TemplateFormat.TXT.value else "text/markdown"
        if fmt == TemplateFormat.HTML.value:
            content_type = "text/html"
        return {
            "document": document,
            "content_bytes": content.encode("utf-8"),
            "content_type": content_type,
            "filename": f"{template_id}_{document.id}.{fmt}",
            "format": fmt
        }

    # Default fallback
    return {
        "document": document,
        "content_bytes": content.encode("utf-8"),
        "content_type": "text/plain",
        "filename": f"{template_id}_{document.id}.txt",
        "format": "txt"
    }
