"""Tests for IMAP attachment extraction and provider routing."""

import email
import os
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from unittest.mock import MagicMock, patch

import pytest

os.environ.setdefault("FIKIRI_TEST_MODE", "1")

from core.email_attachments import normalize_mail_provider
from core.imap_mail_helpers import extract_attachments_from_imap_message, infer_provider_from_imap_settings


def _build_cv_message() -> email.message.Message:
    msg = MIMEMultipart()
    msg["Subject"] = "Please review my CV"
    msg["From"] = "candidate@example.test"
    msg.attach(MIMEText("Please see attached.", "plain"))
    attachment = MIMEApplication(b"%PDF-1.4 cv bytes", _subtype="pdf")
    attachment.add_header("Content-Disposition", "attachment", filename="Michael_Bryan_CV.pdf")
    msg.attach(attachment)
    return msg


def test_extract_attachments_from_imap_message_finds_cv():
    msg = _build_cv_message()
    attachments = extract_attachments_from_imap_message(msg)
    assert len(attachments) == 1
    assert attachments[0]["filename"] == "Michael_Bryan_CV.pdf"
    assert attachments[0]["attachment_id"].startswith("part:")


@pytest.mark.parametrize(
    "server,name,expected",
    [
        ("imap.mail.yahoo.com", "Yahoo Mail", "yahoo"),
        ("imap.mail.me.com", "Apple iCloud Mail", "icloud"),
        ("imap.example.com", "Custom IMAP", "imap"),
    ],
)
def test_infer_provider_from_imap_settings(server, name, expected):
    assert infer_provider_from_imap_settings({"imap_server": server, "service_name": name}) == expected


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("microsoft365", "outlook"),
        ("office365", "outlook"),
        ("apple", "icloud"),
        ("yahoo", "yahoo"),
        ("gmail", "gmail"),
    ],
)
def test_normalize_mail_provider_aliases(raw, expected):
    assert normalize_mail_provider(raw) == expected


def test_synced_email_needs_attachment_backfill():
    from core.email_attachments import synced_email_needs_attachment_backfill

    assert synced_email_needs_attachment_backfill(None) is True
    assert synced_email_needs_attachment_backfill("[]") is True
    assert synced_email_needs_attachment_backfill('[{"attachment_id":"a1"}]') is False


def test_fetch_imap_rfc822_uses_uid_fetch():
    from core.imap_mail_helpers import fetch_imap_rfc822

    mock_imap = MagicMock()
    mock_imap.uid.return_value = ("OK", [(b"1 (RFC822)", b"raw-bytes")])
    assert fetch_imap_rfc822(mock_imap, "42") == b"raw-bytes"
    mock_imap.uid.assert_called_once_with("fetch", "42", "(RFC822)")


def test_fetch_attachments_routes_yahoo_to_imap():
    from core import email_attachments

    with patch.object(email_attachments, "list_cached_attachments", side_effect=[[], [{"id": 1}]]):
        with patch.object(email_attachments, "resolve_email_provider", return_value="yahoo"):
            with patch.object(email_attachments, "fetch_imap_attachments") as mock_imap:
                mock_imap.return_value = [{"attachment_id": "part:2", "filename": "a.pdf"}]
                result = email_attachments.list_email_attachments(1, "42")
    mock_imap.assert_called_once_with(1, "42", "yahoo", cache=True)
    assert len(result) == 1
