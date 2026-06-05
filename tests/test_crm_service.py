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
    def test_get_pipeline_alias_delegates_to_lead_pipeline(self, mock_db):
        mock_db.execute_query.side_effect = [
            [{'stage': 'new', 'count': 1, 'avg_score': 42}],
            [{'count': 1}],
            [{'count': 0}],
        ]
        result = self.service.get_pipeline(1)
        self.assertTrue(result.get('success'), msg=result)
        self.assertIn('pipeline', result.get('data', {}))

    @patch('crm.service.record_crm_event')
    @patch('crm.service.db_optimizer')
    def test_create_lead_normalizes_email_before_lookup_and_insert(self, mock_db, _mock_events):
        mock_db.execute_insert_returning_id.return_value = 101
        mock_db.execute_query.side_effect = [
            [],
            101,
            [{'id': 101}],
        ]
        result = self.service.create_lead(1, {'email': '  Lead@Example.COM  ', 'name': ' Lead Name '})
        self.assertTrue(result.get('success'), msg=result)
        lookup_params = mock_db.execute_query.call_args_list[0].args[1]
        self.assertEqual(lookup_params, (1, 'lead@example.com'))
        insert_params = mock_db.execute_query.call_args_list[1].args[1]
        self.assertEqual(insert_params[1], 'lead@example.com')
        self.assertEqual(insert_params[2], 'Lead Name')

    @patch('crm.service.record_crm_event')
    @patch('crm.service.db_optimizer')
    def test_create_lead_sets_score_and_quality(self, mock_db, _mock_events):
        mock_db.execute_insert_returning_id.return_value = 1
        mock_db.execute_query.side_effect = [
            [],
            1,
            [{'id': 101}],
        ]
        result = self.service.create_lead(1, {'email': 'test@example.com', 'name': 'Test'})
        self.assertTrue(result.get('success'))
        self.assertIn('correlation_id', (result.get('data') or {}))

        insert_call = mock_db.execute_query.call_args_list[1]
        params = insert_call.args[1]
        metadata_json = params[-1]
        metadata = json.loads(metadata_json)
        self.assertIn('lead_quality', metadata)
        self.assertIn('score_breakdown', metadata)

    @patch('crm.service.record_crm_event')
    @patch('crm.service.db_optimizer')
    def test_update_lead_recalculates_score(self, mock_db, _mock_events):
        self.service._get_lead_activity_metrics = lambda _lead_id: (2, None)
        self.service._score_lead_data = lambda _lead, _count, _last: {'score': 77, 'quality': 'B', 'breakdown': {}}

        mock_db.execute_insert_returning_id.return_value = 1
        row = {
            'id': 1, 'user_id': 1, 'email': 'a@b.com', 'name': 'A', 'phone': None, 'company': None,
            'source': 'manual', 'stage': 'new', 'score': 0, 'created_at': '2024-01-01T00:00:00',
            'updated_at': '2024-01-01T00:00:00', 'last_contact': None, 'notes': None, 'tags': '[]', 'metadata': '{}',
        }
        mock_db.execute_query.side_effect = [
            [dict(row)],
            None,
            [dict(row)],
            None,
        ]
        result = self.service.update_lead(1, 1, {'name': 'A'})
        self.assertTrue(result.get('success'))


    def _lead_row(self):
        return {
            'id': 1,
            'user_id': 1,
            'email': 'lead@example.com',
            'name': 'Lead Example',
            'phone': '555-0100',
            'company': 'Acme Co',
            'source': 'manual',
            'stage': 'new',
            'score': 50,
            'created_at': '2024-01-01T00:00:00',
            'updated_at': '2024-01-02T00:00:00',
            'last_contact': None,
            'notes': None,
            'tags': '[]',
            'metadata': '{}',
        }

    def _mock_leads_summary_queries(self, mock_db, total=1):
        mock_db.execute_query.side_effect = [
            [self._lead_row()] if total else [],
            [{'total': total}],
            [{'stage': 'new', 'cnt': total}] if total else [],
            [{'source': 'manual', 'cnt': total}] if total else [],
            [{'avg_score': 50}] if total else [],
            [{'cnt': 0}] if total else [],
        ]

    @patch('crm.service.db_optimizer')
    def test_get_leads_summary_q_search_is_parameterized_across_supported_fields(self, mock_db):
        self._mock_leads_summary_queries(mock_db)

        result = self.service.get_leads_summary(1, filters={'q': 'Acme'}, limit=10, offset=0)

        self.assertTrue(result.get('success'), msg=result)
        list_query, list_params = mock_db.execute_query.call_args_list[0].args
        self.assertIn("LOWER(COALESCE(name, '')) LIKE ?", list_query)
        self.assertIn("LOWER(COALESCE(email, '')) LIKE ?", list_query)
        self.assertIn("LOWER(COALESCE(company, '')) LIKE ?", list_query)
        self.assertIn("LOWER(COALESCE(phone, '')) LIKE ?", list_query)
        self.assertNotIn('Acme', list_query)
        self.assertEqual(list_params[:5], (1, '%acme%', '%acme%', '%acme%', '%acme%'))
        self.assertEqual(list_params[-2:], (10, 0))

    @patch('crm.service.db_optimizer')
    def test_get_leads_summary_q_and_stage_combine_with_and(self, mock_db):
        self._mock_leads_summary_queries(mock_db)

        self.service.get_leads_summary(1, filters={'stage': 'qualified', 'q': 'Acme'}, limit=25, offset=50)

        list_query, list_params = mock_db.execute_query.call_args_list[0].args
        self.assertIn('stage = ?', list_query)
        self.assertIn("LOWER(COALESCE(name, '')) LIKE ?", list_query)
        self.assertIn(' AND ', list_query)
        self.assertEqual(list_params[:6], (1, 'qualified', '%acme%', '%acme%', '%acme%', '%acme%'))
        self.assertEqual(list_params[-2:], (25, 50))

    @patch('crm.service.db_optimizer')
    def test_get_leads_summary_sort_allowlist_applies_safe_sort(self, mock_db):
        self._mock_leads_summary_queries(mock_db)

        self.service.get_leads_summary(1, sort='score', direction='asc')

        list_query = mock_db.execute_query.call_args_list[0].args[0]
        self.assertIn('ORDER BY score ASC, id DESC', list_query)

    @patch('crm.service.db_optimizer')
    def test_get_leads_summary_invalid_sort_and_direction_fall_back_safely(self, mock_db):
        self._mock_leads_summary_queries(mock_db)

        self.service.get_leads_summary(1, sort='email; DROP TABLE leads', direction='sideways')

        list_query = mock_db.execute_query.call_args_list[0].args[0]
        self.assertIn('ORDER BY created_at DESC, id DESC', list_query)
        self.assertNotIn('DROP TABLE', list_query)
        self.assertNotIn('sideways', list_query)

    @patch('crm.service.db_optimizer')
    def test_get_leads_summary_count_query_uses_same_filters_as_list_query(self, mock_db):
        self._mock_leads_summary_queries(mock_db)

        self.service.get_leads_summary(
            1,
            filters={'stage': 'new', 'company': 'Acme', 'q': 'Jones'},
            limit=10,
            offset=20,
        )

        _list_query, list_params = mock_db.execute_query.call_args_list[0].args
        count_query, count_params = mock_db.execute_query.call_args_list[1].args
        self.assertIn('COUNT(*) as total', count_query)
        self.assertEqual(count_params, list_params[:-2])


if __name__ == '__main__':
    unittest.main()
