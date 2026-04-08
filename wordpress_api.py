import requests
from requests.auth import HTTPBasicAuth
import urllib.parse

class WordPressClient:
    def __init__(self, url, username, app_password):
        self.url = url.rstrip('/')
        self.auth = HTTPBasicAuth(username, app_password)
        self.target_slug = "td-composer/td-composer.php"
        self.plugin_id = urllib.parse.quote(self.target_slug, safe='')
        # Try both permalink and plain styles
        self.api_endpoints = [
            f"{self.url}/wp-json/wp/v2/plugins",
            f"{self.url}/?rest_route=/wp/v2/plugins"
        ]

    def _get_api_url(self, endpoint, resource=""):
        if "?" in endpoint:
            # If it's a query param style, we still need a slash before the resource ID
            # e.g. ?rest_route=/wp/v2/plugins/slug
            return f"{endpoint}/{resource}"
        return f"{endpoint}/{resource}".rstrip('/')

    def is_plugin_active(self):
        """Checks if the tagDiv Composer plugin is active."""
        errors = []
        for api_url in self.api_endpoints:
            try:
                url = self._get_api_url(api_url, self.plugin_id)
                print(f"DEBUG: Checking plugin status at: {url}")
                response = requests.get(url, auth=self.auth, timeout=10)
                print(f"DEBUG: Response Code: {response.status_code}")

                if response.status_code == 200:
                    data = response.json()
                    return data.get('status') == 'active'

                # If 404, try listing all plugins from this endpoint
                print(f"DEBUG: Direct access failed ({response.status_code}) for {url}. Trying list...")
                list_response = requests.get(api_url, auth=self.auth, timeout=10)
                print(f"DEBUG: List Response Code: {list_response.status_code}")

                if list_response.status_code == 200:
                    plugins = list_response.json()
                    for p in plugins:
                        if p.get('plugin') == self.target_slug:
                            return p.get('status') == 'active'
                    errors.append(f"List OK at {api_url} but plugin not found.")
                elif list_response.status_code == 401:
                    errors.append(f"401 Unauthorized at {api_url}. Check Application Password.")
                else:
                    errors.append(f"Endpoint {api_url} returned {list_response.status_code}")
            except Exception as e:
                errors.append(f"Error with {api_url}: {str(e)}")

        raise Exception(f"Plugin not found. Details: {' | '.join(errors)}")

    def activate_plugin(self):
        """Activates the tagDiv Composer plugin."""
        errors = []
        for api_url in self.api_endpoints:
            url = self._get_api_url(api_url, self.plugin_id)
            try:
                payload = {'status': 'active'}
                print(f"DEBUG: Activating plugin at: {url}")
                response = requests.post(url, auth=self.auth, json=payload, timeout=10)
                print(f"DEBUG: Activation Response Code: {response.status_code}")

                if response.status_code == 200:
                    data = response.json()
                    return data.get('status') == 'active'
                else:
                    errors.append(f"Activation failed at {url} (Code {response.status_code})")
            except Exception as e:
                errors.append(f"Error at {url}: {str(e)}")

        raise Exception(f"Failed to activate plugin. Details: {' | '.join(errors)}")

    def test_connection(self):
        """Tests if the credentials and URL are valid."""
        try:
            # Just try to fetch the site index or a simple API call
            response = requests.get(f"{self.url}/wp-json/", auth=self.auth, timeout=10)
            return response.status_code == 200
        except:
            return False
