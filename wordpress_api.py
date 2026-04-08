import requests
from requests.auth import HTTPBasicAuth
import urllib.parse

class WordPressClient:
    def __init__(self, url, username, app_password):
        self.url = url.rstrip('/')
        self.auth = HTTPBasicAuth(username, app_password)
        self.plugin_slug = urllib.parse.quote("td-composer/td-composer.php", safe='')
        self.api_url = f"{self.url}/wp-json/wp/v2/plugins"

    def is_plugin_active(self):
        """Checks if the tagDiv Composer plugin is active."""
        try:
            # The REST API uses the slug as the identifier.
            # We must URL-encode it because it contains a slash.
            response = requests.get(f"{self.api_url}/{self.plugin_slug}", auth=self.auth, timeout=10)

            if response.status_code == 200:
                data = response.json()
                return data.get('status') == 'active'
            elif response.status_code == 404:
                raise Exception("Plugin 'tagDiv Composer' not found on the site.")
            else:
                response.raise_for_status()
        except requests.exceptions.RequestException as e:
            raise Exception(f"Connection error: {e}")

    def activate_plugin(self):
        """Activates the tagDiv Composer plugin."""
        try:
            payload = {'status': 'active'}
            response = requests.post(
                f"{self.api_url}/{self.plugin_slug}",
                auth=self.auth,
                json=payload,
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                return data.get('status') == 'active'
            else:
                # Log the error response if possible
                try:
                    err_msg = response.json().get('message', response.text)
                except:
                    err_msg = response.text
                raise Exception(f"Failed to activate plugin: {err_msg}")
        except requests.exceptions.RequestException as e:
            raise Exception(f"Connection error during activation: {e}")

    def test_connection(self):
        """Tests if the credentials and URL are valid."""
        try:
            # Just try to fetch the site index or a simple API call
            response = requests.get(f"{self.url}/wp-json/", auth=self.auth, timeout=10)
            return response.status_code == 200
        except:
            return False
