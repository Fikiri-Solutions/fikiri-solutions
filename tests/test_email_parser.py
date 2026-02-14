#!/usr/bin/env python3
"""
Email Parser Unit Tests
Tests for email_automation/parser.py
"""

import unittest
import os
import sys
import base64

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("FLASK_ENV", "test")


class TestMinimalEmailParser(unittest.TestCase):
    def setUp(self):
        from email_automation.parser import MinimalEmailParser
        self.parser = MinimalEmailParser()

    def test_parse_text_plain_body(self):
        body = "Hello world"
        encoded = base64.urlsafe_b64encode(body.encode("utf-8")).decode("utf-8").rstrip("=")
        message = {
            "id": "m1",
            "threadId": "t1",
            "snippet": "Hello",
            "labelIds": ["UNREAD"],
            "payload": {
                "mimeType": "text/plain",
                "headers": [
                    {"name": "From", "value": "a@b.com"},
                    {"name": "To", "value": "x@y.com"},
                    {"name": "Subject", "value": "Test"},
                ],
                "body": {"data": encoded},
            },
        }
        parsed = self.parser.parse_message(message)
        self.assertEqual(parsed["message_id"], "m1")
        self.assertEqual(self.parser.get_sender(parsed), "a@b.com")
        self.assertEqual(self.parser.get_subject(parsed), "Test")
        self.assertIn("Hello", self.parser.get_body_text(parsed))
        self.assertTrue(self.parser.is_unread(parsed))

    def test_parse_html_body_fallback(self):
        html = "<p>Hello <b>World</b></p>"
        encoded = base64.urlsafe_b64encode(html.encode("utf-8")).decode("utf-8").rstrip("=")
        message = {
            "id": "m2",
            "payload": {
                "mimeType": "text/html",
                "headers": [{"name": "From", "value": "c@d.com"}],
                "body": {"data": encoded},
            },
        }
        parsed = self.parser.parse_message(message)
        self.assertEqual(self.parser.get_sender(parsed), "c@d.com")
        self.assertEqual(self.parser.get_body_text(parsed), "Hello World")

    def test_parse_missing_subject_and_from(self):
        body = "Hello"
        encoded = base64.urlsafe_b64encode(body.encode("utf-8")).decode("utf-8").rstrip("=")
        message = {
            "id": "m4",
            "payload": {
                "mimeType": "text/plain",
                "headers": [],
                "body": {"data": encoded},
            },
        }
        parsed = self.parser.parse_message(message)
        self.assertEqual(self.parser.get_sender(parsed), "")
        self.assertEqual(self.parser.get_subject(parsed), "")

    def test_parse_multipart_with_attachment(self):
        body = "Part text"
        encoded = base64.urlsafe_b64encode(body.encode("utf-8")).decode("utf-8").rstrip("=")
        message = {
            "id": "m3",
            "payload": {
                "mimeType": "multipart/mixed",
                "parts": [
                    {"mimeType": "text/plain", "body": {"data": encoded}},
                    {
                        "filename": "file.txt",
                        "mimeType": "text/plain",
                        "body": {"attachmentId": "att1", "size": 10},
                    },
                ],
            },
        }
        parsed = self.parser.parse_message(message)
        self.assertEqual(self.parser.get_body_text(parsed), "Part text")
        self.assertTrue(self.parser.has_attachments(parsed))
        self.assertEqual(self.parser.get_attachment_count(parsed), 1)

    def test_recipients_parsing(self):
        message = {
            "payload": {
                "headers": [
                    {"name": "To", "value": "a@b.com, c@d.com"},
                    {"name": "Cc", "value": "e@f.com"},
                ]
            }
        }
        parsed = self.parser.parse_message(message)
        recipients = self.parser.get_recipients(parsed)
        self.assertEqual(recipients, ["a@b.com", "c@d.com", "e@f.com"])


if __name__ == "__main__":
    unittest.main()
