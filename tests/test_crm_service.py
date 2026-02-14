#!/usr/bin/env python3
"""
CRM service core tests.
"""

import unittest
from unittest.mock import patch
import sys
import os
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from crm.service import EnhancedCRMService


class TestCRMService(unittest.TestCase):
    def setUp(self):
        self.service = EnhancedCRMService()

    @patch('crm.service.db_optimizer')
    def test_create_lead_requires_fields(self, mock_db):
        result = self.service.create_lead(1, {'email': 'test@example.com'})
        self.assertFalse(result.get('success'))
        self.assertEqual(result.get('error_code'), 'MISSING_FIELD')

    @patch('crm.service.db_optimizer')
    def test_create_lead_duplicate(self, mock_db):
        mock_db.execute_query.side_effect = [
            [{'id': 1}]
        ]
        result = self.service.create_lead(1, {'email': 'test@example.com', 'name': 'Test'})
        self.assertFalse(result.get('success'))
        self.assertEqual(result.get('error_code'), 'LEAD_EXISTS')

    @patch('crm.service.db_optimizer')
    def test_update_lead_no_updates(self, mock_db):
        mock_db.execute_query.return_value = [{'id': 1, 'user_id': 1}]
        result = self.service.update_lead(1, 1, {})
        self.assertFalse(result.get('success'))
        self.assertEqual(result.get('error_code'), 'NO_UPDATES')

    @patch('crm.service.db_optimizer')
    def test_create_lead_sets_score_and_quality(self, mock_db):
        mock_db.execute_query.side_effect = [
            [],   # existing check
            1,    # insert lead id
            1     # add activity
        ]
        result = self.service.create_lead(1, {'email': 'test@example.com', 'name': 'Test'})
        self.assertTrue(result.get('success'))

        insert_call = mock_db.execute_query.call_args_list[1]
        params = insert_call.args[1]
        metadata_json = params[-1]
        metadata = json.loads(metadata_json)
        self.assertIn('lead_quality', metadata)
        self.assertIn('score_breakdown', metadata)

    @patch('crm.service.db_optimizer')
    def test_update_lead_recalculates_score(self, mock_db):
        self.service._get_lead_activity_metrics = lambda _lead_id: (2, None)
        self.service._score_lead_data = lambda _lead, _count, _last: {'score': 77, 'quality': 'B', 'breakdown': {}}

        mock_db.execute_query.side_effect = [
            [{'id': 1, 'user_id': 1, 'stage': 'new'}],  # ownership check
            None,  # update lead
            1,     # add activity
            [{'id': 1, 'user_id': 1, 'email': 'a@b.com', 'name': 'A', 'phone': None, 'company': None, 'source': 'manual', 'stage': 'new', 'score': 0, 'created_at': '2024-01-01T00:00:00', 'updated_at': '2024-01-01T00:00:00', 'last_contact': None, 'notes': None, 'tags': '[]', 'metadata': '{}'}],
            None,  # update score + metadata
        ]
        result = self.service.update_lead(1, 1, {'name': 'A'})
        self.assertTrue(result.get('success'))


if __name__ == '__main__':
    unittest.main()
