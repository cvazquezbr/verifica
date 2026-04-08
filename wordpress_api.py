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
            url = f"{self.api_url}/{self.plugin_slug}"
            print(f"DEBUG: Checking plugin status at: {url}")
            response = requests.get(url, auth=self.auth, timeout=10)

            print(f"DEBUG: Response Code: {response.status_code}")

            if response.status_code == 200:
                data = response.json()
                return data.get('status') == 'active'
            elif response.status_code == 404:
                # Fallback: list all plugins and search by slug
                print("DEBUG: Direct access 404. Fetching all plugins...")
                list_response = requests.get(self.api_url, auth=self.auth, timeout=10)
                if list_response.status_code == 200:
                    plugins = list_response.json()
                    # The actual slug might differ slightly in how WP reports it
                    target = "td-composer/td-composer.php"
                    for p in plugins:
                        if p.get('plugin') == target:
                            return p.get('status') == 'active'

                raise Exception(f"Plugin 'tagDiv Composer' not found. URL: {url} | Resp: {response.text[:100]}")
            else:
                response.raise_for_status()
        except requests.exceptions.RequestException as e:
            raise Exception(f"Connection error: {e}")

    def activate_plugin(self):
        """Activates the tagDiv Composer plugin."""
        url = f"{self.api_url}/{self.plugin_slug}"
        try:
            payload = {'status': 'active'}
            print(f"DEBUG: Activating plugin at: {url}")
            response = requests.post(
                url,
                auth=self.auth,
                json=payload,
                timeout=10
            )

            print(f"DEBUG: Activation Response Code: {response.status_code}")

            if response.status_code == 200:
                data = response.json()
                return data.get('status') == 'active'
            else:
                # Log the error response if possible
                try:
                    err_msg = response.json().get('message', response.text)
                except:
                    err_msg = response.text
                raise Exception(f"Activation Failed (Code {response.status_code}). URL: {url} | Resp: {err_msg[:100]}")
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
