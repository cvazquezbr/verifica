import unittest
from unittest.mock import MagicMock, patch
from database import Database
from wordpress_api import WordPressClient
import os

class TestAppLogic(unittest.TestCase):
    def setUp(self):
        self.db = Database("test_monitor.db")

    def tearDown(self):
        if hasattr(self, 'db') and os.path.exists(self.db.db_path):
            os.remove(self.db.db_path)

    def test_database_site_save_and_get(self):
        smtp_data = {
            'host': 'smtp.test.com',
            'port': 587,
            'user': 'smtpuser',
            'pass': 'smtppass',
            'ssl': 0,
            'sender_name': 'Tester',
            'receiver': 'dest@test.com',
            'cc': 'cc@test.com'
        }
        self.db.save_site("http://test.com", "user", "pass", 60, smtp_data, 0, 0)
        site = self.db.get_active_site()
        self.assertIsNotNone(site)
        self.assertEqual(site[1], "http://test.com")
        self.assertEqual(site[2], "user")
        self.assertEqual(site[5], "smtp.test.com")
        self.assertEqual(site[11], "dest@test.com")

    @patch('requests.get')
    def test_wp_client_is_active(self, mock_get):
        # Mock successful active status
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'status': 'active'}
        mock_get.return_value = mock_response

        client = WordPressClient("http://test.com", "user", "pass")
        self.assertTrue(client.is_plugin_active())

    @patch('requests.post')
    def test_wp_client_activate(self, mock_post):
        # Mock successful activation
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'status': 'active'}
        mock_post.return_value = mock_response

        client = WordPressClient("http://test.com", "user", "pass")
        self.assertTrue(client.activate_plugin())

    @patch('smtplib.SMTP_SSL')
    @patch('smtplib.SMTP')
    def test_send_email(self, mock_smtp, mock_smtp_ssl):
        from email_utils import send_plugin_notification

        smtp_config = {
            'host': 'smtp.test.com',
            'port': 465,
            'user': 'user@test.com',
            'pass': 'pass',
            'ssl': 1,
            'sender_name': 'Sender',
            'receiver': 'receiver@test.com',
            'cc': 'cc@test.com'
        }
        plugin_data = {
            'name': 'Test Plugin',
            'version': '1.0.0',
            'dir': 'test-plugin',
            'reason': 'Test reason',
            'wp_admin_url': 'http://test.com/wp-admin/'
        }

        # Test successful send
        success = send_plugin_notification(smtp_config, plugin_data)
        self.assertTrue(success)
        mock_smtp_ssl.assert_called()

if __name__ == '__main__':
    unittest.main()
