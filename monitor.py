import time
import threading
from wordpress_api import WordPressClient
from database import Database

class MonitorWorker(threading.Thread):
    def __init__(self, db, site_data, callback=None):
        super().__init__()
        self.db = db
        self.site_id, self.url, self.username, self.password = site_data
        self.wp_client = WordPressClient(self.url, self.username, self.password)
        self.callback = callback
        self.running = False
        self._stop_event = threading.Event()

    def stop(self):
        self._stop_event.set()
        self.running = False

    def run(self):
        self.running = True
        while not self._stop_event.is_set():
            was_activated = False
            status_text = "OK"

            try:
                is_active = self.wp_client.is_plugin_active()
                if not is_active:
                    activated = self.wp_client.activate_plugin()
                    if activated:
                        was_activated = True
                        status_text = "Reactivated"
                    else:
                        status_text = "Activation Failed"
                else:
                    status_text = "Active"
            except Exception as e:
                status_text = f"Error: {str(e)}"
                print(f"Monitoring error: {e}")

            # Log to DB
            self.db.log_event(self.site_id, status_text, was_activated)

            # Notify UI if callback exists
            if self.callback:
                self.callback(status_text, was_activated)

            # Wait for 60 seconds, but check stop event frequently for quick shutdown
            for _ in range(60):
                if self._stop_event.is_set():
                    break
                time.sleep(1)

        self.running = False
