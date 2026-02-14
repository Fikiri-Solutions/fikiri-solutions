#!/usr/bin/env python3
"""CRM pipeline API tests."""

import unittest
import json
from unittest.mock import patch
import sys
import os
from flask import Flask

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from crm.completion_api import crm_bp


class TestCRMPipelineAPI(unittest.TestCase):
    def setUp(self):
        self.app = Flask(__name__)
        self.app.config['TESTING'] = True
        self.app.register_blueprint(crm_bp)
        self.client = self.app.test_client()

    @patch("crm.completion_api.db_optimizer")
    def test_pipeline_leads_with_quality_and_pagination(self, mock_db):
        mock_db.execute_query.return_value = [
            {
                "id": 1,
                "user_id": 1,
                "email": "a@b.com",
                "name": "A",
                "phone": None,
                "company": "Co",
                "source": "manual",
                "stage": "new",
                "score": 77,
                "created_at": "2024-01-01T00:00:00",
                "updated_at": "2024-01-01T00:00:00",
                "last_contact": None,
                "notes": None,
                "tags": "[]",
                "metadata": json.dumps({"lead_quality": "B"}),
                "activity_count": 0,
                "last_activity": None,
            }
        ]

        response = self.client.get('/api/crm/pipeline/leads/1?stage=new&limit=10&offset=0')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        pipeline = data.get('pipeline', {})
        self.assertIn('new', pipeline)
        self.assertEqual(pipeline['new'][0].get('lead_quality'), 'B')
        self.assertEqual(data.get('limit'), 10)
        self.assertEqual(data.get('offset'), 0)


if __name__ == '__main__':
    unittest.main()
