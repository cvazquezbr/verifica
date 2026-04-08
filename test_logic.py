import unittest
from unittest.mock import MagicMock, patch
from database import Database
from wordpress_api import WordPressClient
import os

class TestAppLogic(unittest.TestCase):
    def setUp(self):
        self.db = Database("test_monitor.db")

    def tearDown(self):
        if os.path.exists("test_monitor.db"):
            os.remove("test_monitor.db")

    def test_database_site_save_and_get(self):
        self.db.save_site("http://test.com", "user", "pass", 60)
        site = self.db.get_active_site()
        self.assertIsNotNone(site)
        self.assertEqual(site[1], "http://test.com")
        self.assertEqual(site[2], "user")

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

if __name__ == '__main__':
    unittest.main()
