#!/usr/bin/env python3
"""Tests for core.request_correlation.get_or_create_correlation_id."""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("FLASK_ENV", "test")

from flask import Flask


class TestRequestCorrelation(unittest.TestCase):
    def test_header_wins_over_body(self):
        app = Flask(__name__)
        with app.test_request_context(
            "/",
            method="POST",
            json={"correlation_id": "from-body"},
            headers={"X-Correlation-ID": "from-header"},
        ):
            from flask import request
            from core.request_correlation import get_or_create_correlation_id

            self.assertEqual(
                get_or_create_correlation_id(request, request.get_json()),
                "from-header",
            )

    def test_body_used_when_no_header(self):
        app = Flask(__name__)
        with app.test_request_context("/", method="POST", json={"correlation_id": " body-val "}):
            from flask import request
            from core.request_correlation import get_or_create_correlation_id

            self.assertEqual(
                get_or_create_correlation_id(request, request.get_json()),
                "body-val",
            )

    def test_generates_uuid_when_missing(self):
        app = Flask(__name__)
        with app.test_request_context("/", method="POST", json={}):
            from flask import request
            from core.request_correlation import get_or_create_correlation_id

            cid = get_or_create_correlation_id(request, request.get_json())
            self.assertGreater(len(cid), 20)
