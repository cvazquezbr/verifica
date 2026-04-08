import requests
from requests.auth import HTTPBasicAuth
import urllib.parse

class WordPressClient:
    def __init__(self, url, username, app_password):
        self.url = url.rstrip('/')
        self.auth = HTTPBasicAuth(username, app_password)
        # Based on user's successful curl: td-composer/td-composer (without .php sometimes)
        self.target_slugs = ["td-composer/td-composer", "td-composer/td-composer.php"]

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
            for slug in self.target_slugs:
                # Try both encoded and unencoded slash
                ids_to_try = [slug, urllib.parse.quote(slug, safe='')]
                for pid in ids_to_try:
                    try:
                        url = self._get_api_url(api_url, pid)
                        print(f"DEBUG: Checking plugin status at: {url}")
                        response = requests.get(url, auth=self.auth, timeout=10)
                        print(f"DEBUG: Response Code: {response.status_code}")

                        if response.status_code == 200:
                            data = response.json()
                            return data.get('status') == 'active'
                    except Exception as e:
                        errors.append(f"Error checking {url}: {str(e)}")

            # Fallback: list all plugins from this endpoint
            try:
                print(f"DEBUG: Direct access failed for {api_url}. Trying list...")
                list_response = requests.get(api_url, auth=self.auth, timeout=10)
                print(f"DEBUG: List Response Code: {list_response.status_code}")

                if list_response.status_code == 200:
                    plugins = list_response.json()
                    for p in plugins:
                        if p.get('plugin') in self.target_slugs:
                            return p.get('status') == 'active'
                    errors.append(f"List OK at {api_url} but plugin not found.")
                elif list_response.status_code == 401:
                    errors.append(f"401 Unauthorized at {api_url}. Check Application Password.")
                else:
                    errors.append(f"Endpoint {api_url} returned {list_response.status_code}")
            except Exception as e:
                errors.append(f"Error listing {api_url}: {str(e)}")

        raise Exception(f"Plugin not found. Details: {' | '.join(list(set(errors))[:3])}")

    def activate_plugin(self):
        """Activates the tagDiv Composer plugin."""
        errors = []
        for api_url in self.api_endpoints:
            for slug in self.target_slugs:
                ids_to_try = [slug, urllib.parse.quote(slug, safe='')]
                for pid in ids_to_try:
                    url = self._get_api_url(api_url, pid)
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

        raise Exception(f"Failed to activate plugin. Details: {' | '.join(list(set(errors))[:3])}")

    def get_plugin_details(self):
        """Gets details for the tagDiv Composer plugin."""
        for api_url in self.api_endpoints:
            for slug in self.target_slugs:
                ids_to_try = [slug, urllib.parse.quote(slug, safe='')]
                for pid in ids_to_try:
                    try:
                        url = self._get_api_url(api_url, pid)
                        response = requests.get(url, auth=self.auth, timeout=10)
                        if response.status_code == 200:
                            data = response.json()
                            return {
                                'name': data.get('name', 'tagDiv Composer'),
                                'version': data.get('version', 'N/A'),
                                'plugin': data.get('plugin', 'td-composer/td-composer.php')
                            }
                    except:
                        pass
        return {
            'name': 'tagDiv Composer',
            'version': 'N/A',
            'plugin': 'td-composer/td-composer.php'
        }

    def test_connection(self):
        """Tests if the credentials and URL are valid."""
        try:
            # Just try to fetch the site index or a simple API call
            response = requests.get(f"{self.url}/wp-json/", auth=self.auth, timeout=10)
            return response.status_code == 200
        except:
            return False
