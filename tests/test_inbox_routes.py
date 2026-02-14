#!/usr/bin/env python3
"""Inbox email routes tests."""

import unittest
import json
from unittest.mock import patch, MagicMock
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app


class TestInboxRoutes(unittest.TestCase):
    def setUp(self):
        self.app = app
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()

    def test_get_emails_requires_auth(self):
        response = self.client.get('/api/email/messages')
        self.assertEqual(response.status_code, 401)
        data = json.loads(response.data)
        self.assertFalse(data.get('success'))
        self.assertEqual(data.get('code'), 'AUTHENTICATION_REQUIRED')

    @patch('routes.business.db_optimizer')
    @patch('routes.business.get_current_user_id')
    def test_get_emails_invalid_user_id_param(self, mock_get_user, mock_db):
        mock_get_user.return_value = None
        mock_db.execute_query.return_value = []

        response = self.client.get('/api/email/messages?user_id=999')
        self.assertEqual(response.status_code, 401)
        data = json.loads(response.data)
        self.assertFalse(data.get('success'))
        self.assertEqual(data.get('code'), 'INVALID_USER_ID')

    @patch('routes.business.db_optimizer')
    @patch('routes.business.get_current_user_id')
    def test_get_emails_from_synced(self, mock_get_user, mock_db):
        mock_get_user.return_value = 1
        mock_db.execute_query.side_effect = [
            [
                {
                    'email_id': 'abc',
                    'provider': 'gmail',
                    'subject': 'Hello',
                    'sender': 'Sender <s@example.com>',
                    'recipient': 'me@example.com',
                    'date': '2025-01-01',
                    'body': 'Body',
                    'labels': '["UNREAD"]'
                }
            ],
            [{'total': 1}]
        ]

        response = self.client.get('/api/email/messages')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data.get('success'))
        self.assertEqual(data.get('data', {}).get('source'), 'synced')
        self.assertEqual(len(data.get('data', {}).get('emails', [])), 1)

    @patch('integrations.gmail.gmail_client.gmail_client')
    @patch('routes.business.db_optimizer')
    @patch('routes.business.get_current_user_id')
    def test_get_emails_gmail_not_connected(self, mock_get_user, mock_db, mock_gmail):
        mock_get_user.return_value = 1
        mock_db.execute_query.return_value = []
        mock_gmail.get_gmail_service_for_user.side_effect = RuntimeError('No tokens')

        response = self.client.get('/api/email/messages?use_synced=false')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data.get('success'))
        self.assertEqual(data.get('data', {}).get('emails'), [])


if __name__ == '__main__':
    unittest.main()
