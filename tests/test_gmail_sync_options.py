#!/usr/bin/env python3
"""Tests for core.gmail_sync_options."""

import unittest

from core.gmail_sync_options import (
    clamp_max_messages,
    lookback_days_from_oauth_metadata,
    lookback_from_start_params,
    parse_lookback_days,
    parse_sync_params_from_body,
    lookback_presets_for_api,
)


class TestGmailSyncOptions(unittest.TestCase):
    def test_parse_lookback_presets(self):
        self.assertEqual(parse_lookback_days("60d"), 60)
        self.assertEqual(parse_lookback_days("1y"), 365)
        self.assertEqual(parse_lookback_days("5y"), 1825)
        self.assertEqual(parse_lookback_days(90), 90)
        self.assertEqual(parse_lookback_days("999"), 90)

    def test_clamp_max_messages(self):
        self.assertEqual(clamp_max_messages(50), 50)
        self.assertEqual(clamp_max_messages(9999), 500)
        self.assertEqual(clamp_max_messages("bad"), 200)

    def test_continue_reuses_cursor(self):
        params = parse_sync_params_from_body(
            {"continue_sync": True},
            cursor_metadata={
                "lookback_days": 365,
                "next_page_token": "tok123",
                "has_more": True,
            },
        )
        self.assertEqual(params.lookback_days, 365)
        self.assertEqual(params.page_token, "tok123")

    def test_lookback_presets_for_api(self):
        presets = lookback_presets_for_api()
        self.assertEqual(len(presets), 5)
        self.assertEqual(presets[0]["id"], "60d")

    def test_lookback_from_start_params(self):
        days, preset = lookback_from_start_params(lookback="1y")
        self.assertEqual(days, 365)
        self.assertEqual(preset, "1y")
        days2, preset2 = lookback_from_start_params(lookback="bogus")
        self.assertEqual(days2, 90)
        self.assertEqual(preset2, "90d")

    def test_lookback_days_from_oauth_metadata(self):
        self.assertEqual(
            lookback_days_from_oauth_metadata({"lookback_days": 365, "lookback_preset": "1y"}),
            365,
        )
        self.assertEqual(lookback_days_from_oauth_metadata({}), 90)
        self.assertEqual(lookback_days_from_oauth_metadata(None), 90)


if __name__ == "__main__":
    unittest.main()
