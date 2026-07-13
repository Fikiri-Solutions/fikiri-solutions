"""Tests for Gmail attachment extraction and inbox attachment API."""

import base64
import json
import os
from unittest.mock import MagicMock, patch

import pytest

os.environ.setdefault("FIKIRI_TEST_MODE", "1")

from core.email_attachments import extract_attachments_from_gmail_payload


def test_extract_attachments_from_payload_finds_cv():
    payload = {
        "mimeType": "multipart/mixed",
        "parts": [
            {
                "mimeType": "text/plain",
                "body": {"data": "cGxlYXNlIHJldmlldyBteSBjdg=="},
            },
            {
                "mimeType": "application/pdf",
                "filename": "Michael_Bryan_CV.pdf",
                "body": {"attachmentId": "ANGjdJ_cv", "size": 12000},
            },
        ],
    }
    attachments = extract_attachments_from_gmail_payload(payload)
    assert len(attachments) == 1
    assert attachments[0]["filename"] == "Michael_Bryan_CV.pdf"
    assert attachments[0]["attachment_id"] == "ANGjdJ_cv"


def test_extract_attachments_from_outlook_items():
    from core.email_attachments import extract_attachments_from_outlook_items

    items = [
        {
            "@odata.type": "#microsoft.graph.fileAttachment",
            "id": "outlook-att-1",
            "name": "resume.pdf",
            "contentType": "application/pdf",
            "size": 9000,
        }
    ]
    attachments = extract_attachments_from_outlook_items(items)
    assert len(attachments) == 1
    assert attachments[0]["filename"] == "resume.pdf"
    assert attachments[0]["attachment_id"] == "outlook-att-1"


def test_list_email_attachments_uses_outlook_provider():
    from core import email_attachments

    cached_after = [{"id": 1, "attachment_id": "o1", "filename": "a.pdf", "mime_type": "application/pdf", "size": 1}]
    with patch.object(email_attachments, "list_cached_attachments", side_effect=[[], cached_after]):
        with patch.object(email_attachments, "resolve_email_provider", return_value="outlook"):
            with patch.object(email_attachments, "fetch_attachments_for_provider") as mock_fetch:
                mock_fetch.return_value = [{"attachment_id": "o1", "filename": "a.pdf", "mime_type": "application/pdf", "size": 1}]
                result = email_attachments.list_email_attachments(1, "outlook-msg")
    mock_fetch.assert_called_once_with(1, "outlook-msg", "outlook", cache=True)
    assert len(result) == 1


    payload = {
        "mimeType": "multipart/alternative",
        "parts": [
            {"mimeType": "text/plain", "body": {"data": "aGk="}},
            {"mimeType": "text/html", "body": {"data": "aGk="}},
        ],
    }
    assert extract_attachments_from_gmail_payload(payload) == []


@pytest.mark.parametrize(
    "cached_rows,expected_len",
    [
        ([{"id": 1, "attachment_id": "a1", "filename": "x.pdf", "mime_type": "application/pdf", "size": 1}], 1),
        ([], 1),
    ],
)
def test_list_email_attachments_cache_or_fetch(cached_rows, expected_len):
    from core import email_attachments

    fetch_result = [{"attachment_id": "a1", "filename": "x.pdf", "mime_type": "application/pdf", "size": 1}]
    after_cache = cached_rows or [
        {"id": 1, "attachment_id": "a1", "filename": "x.pdf", "mime_type": "application/pdf", "size": 1}
    ]

    with patch.object(email_attachments, "list_cached_attachments", side_effect=[cached_rows, after_cache]):
        with patch.object(email_attachments, "resolve_email_provider", return_value="gmail"):
            with patch.object(email_attachments, "fetch_attachments_for_provider", return_value=fetch_result):
                result = email_attachments.list_email_attachments(1, "msg123")
    assert len(result) == expected_len
