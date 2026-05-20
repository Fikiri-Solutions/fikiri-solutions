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

    @patch('routes.business.resolve_request_user_id', return_value=None)
    @patch('routes.business.db_optimizer')
    def test_get_emails_invalid_user_id_param(self, mock_db, mock_resolve):
        mock_db.execute_query.return_value = []

        response = self.client.get('/api/email/messages?user_id=999')
        self.assertEqual(response.status_code, 401)
        data = json.loads(response.data)
        self.assertFalse(data.get('success'))
        self.assertEqual(data.get('code'), 'AUTHENTICATION_REQUIRED')

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

    @patch('integrations.gmail.gmail_client.gmail_client')
    @patch('routes.business.db_optimizer')
    @patch('routes.business.get_current_user_id')
    def test_get_emails_gmail_query_unread_plus_search(self, mock_get_user, mock_db, mock_gmail):
        mock_get_user.return_value = 1
        mock_db.execute_query.return_value = []
        mock_service = MagicMock()
        mock_gmail.get_gmail_service_for_user.return_value = mock_service
        list_execute = mock_service.users.return_value.messages.return_value.list.return_value.execute
        list_execute.return_value = {
            'messages': [{'id': 'msg-1'}],
            'nextPageToken': 'page-2',
        }
        get_execute = mock_service.users.return_value.messages.return_value.get.return_value.execute
        get_execute.return_value = {
            'id': 'msg-1',
            'labelIds': ['INBOX', 'UNREAD'],
            'snippet': 'Hello FAU',
            'payload': {
                'headers': [
                    {'name': 'Subject', 'value': 'FAU notice'},
                    {'name': 'From', 'value': 'noreply@fau.edu'},
                    {'name': 'Date', 'value': 'Mon, 1 Jan 2025 12:00:00 +0000'},
                ]
            },
        }

        response = self.client.get(
            '/api/email/messages?use_synced=false&filter=unread'
            '&q=Florida+Atlantic+University'
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data.get('success'))
        self.assertEqual(data.get('data', {}).get('source'), 'gmail_api')
        pagination = data.get('data', {}).get('pagination', {})
        self.assertTrue(pagination.get('has_more'))
        self.assertEqual(pagination.get('next_page_token'), 'page-2')

        list_call = mock_service.users.return_value.messages.return_value.list
        list_call.assert_called_once()
        list_kwargs = list_call.call_args.kwargs
        self.assertEqual(
            list_kwargs.get('q'),
            'in:inbox is:unread Florida Atlantic University',
        )
        self.assertEqual(list_kwargs.get('maxResults'), 50)
        self.assertNotIn('pageToken', list_kwargs)

    @patch('integrations.gmail.gmail_client.gmail_client')
    @patch('routes.business.db_optimizer')
    @patch('routes.business.get_current_user_id')
    def test_get_emails_gmail_page_token_not_limit_bump(self, mock_get_user, mock_db, mock_gmail):
        mock_get_user.return_value = 1
        mock_db.execute_query.return_value = []
        mock_service = MagicMock()
        mock_gmail.get_gmail_service_for_user.return_value = mock_service
        list_execute = mock_service.users.return_value.messages.return_value.list.return_value.execute
        list_execute.return_value = {'messages': [], 'nextPageToken': None}
        get_execute = mock_service.users.return_value.messages.return_value.get.return_value.execute

        response = self.client.get(
            '/api/email/messages?use_synced=false&page_token=abc-token&q=FAU'
        )
        self.assertEqual(response.status_code, 200)
        list_kwargs = mock_service.users.return_value.messages.return_value.list.call_args.kwargs
        self.assertEqual(list_kwargs.get('pageToken'), 'abc-token')
        self.assertEqual(list_kwargs.get('q'), 'in:inbox FAU')
        self.assertEqual(list_kwargs.get('maxResults'), 50)
        get_execute.assert_not_called()

    @patch('routes.business.db_optimizer')
    @patch('routes.business.get_current_user_id')
    def test_get_emails_synced_search_degrades_safely(self, mock_get_user, mock_db):
        mock_get_user.return_value = 1
        captured = []

        def fake_query(sql, params=None, fetch=True):
            captured.append((sql, params))
            if 'COUNT' in sql.upper():
                return [{'total': 1}]
            return [
                {
                    'email_id': 'sync-1',
                    'provider': 'gmail',
                    'subject': 'Florida Atlantic University',
                    'sender': 'noreply@fau.edu',
                    'recipient': 'me@example.com',
                    'date': '2025-01-01',
                    'body_preview': 'Campus update',
                    'labels': '[]',
                    'is_read': 1,
                }
            ]

        mock_db.execute_query.side_effect = fake_query

        response = self.client.get(
            '/api/email/messages?use_synced=true&q=Florida+Atlantic'
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data.get('success'))
        self.assertEqual(data.get('data', {}).get('source'), 'synced')
        list_sql, list_params = captured[0]
        self.assertIn('LIKE', list_sql)
        self.assertIn('%Florida Atlantic%', list_params)


if __name__ == '__main__':
    unittest.main()
