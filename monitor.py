import time
import threading
from wordpress_api import WordPressClient
from database import Database
from email_utils import send_plugin_notification
from datetime import datetime

class MonitorWorker(threading.Thread):
    def __init__(self, db, site_data, callback=None):
        super().__init__()
        self.db = db
        # Unpack site data based on database schema
        (self.site_id, self.url, self.username, self.password, self.interval,
         smtp_host, smtp_port, smtp_user, smtp_pass, smtp_ssl,
         smtp_sender_name, smtp_receiver, smtp_cc, _, _) = site_data

        # SMTP Data
        self.smtp_config = {
            'host': smtp_host,
            'port': smtp_port,
            'user': smtp_user,
            'pass': smtp_pass,
            'ssl': smtp_ssl,
            'sender_name': smtp_sender_name,
            'receiver': smtp_receiver,
            'cc': smtp_cc
        }

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
            status_code = Database.STATUS_ACTIVE
            should_send_email = False
            reactivation_success = True

            try:
                is_active = self.wp_client.is_plugin_active()
                if not is_active:
                    should_send_email = True
                    activated = self.wp_client.activate_plugin()
                    if activated:
                        was_activated = True
                        status_text = "Reactivated"
                        status_code = Database.STATUS_REACTIVATED
                    else:
                        status_text = "Activation Failed"
                        status_code = Database.STATUS_ACT_FAILED
                        reactivation_success = False
                else:
                    status_text = "Active"
                    status_code = Database.STATUS_ACTIVE
            except Exception as e:
                status_text = f"Error: {str(e)}"
                status_code = Database.STATUS_ERROR
                reactivation_success = False
                print(f"Monitoring error: {e}")

            # Log to DB using status_code for space optimization
            self.db.log_event(self.site_id, status_code, was_activated)

            # Send Email if plugin was inactive
            if should_send_email and self.smtp_config['receiver']:
                try:
                    plugin_details = self.wp_client.get_plugin_details()
                    plugin_data = {
                        'name': plugin_details.get('name', 'tagDiv Composer'),
                        'version': plugin_details.get('version', 'N/A'),
                        'dir': plugin_details.get('plugin', 'td-composer/td-composer.php').split('/')[0],
                        'reason': 'Plugin desativado detectado pelo monitoramento',
                        'timestamp': datetime.now().strftime("%d/%m/%Y às %H:%M"),
                        'wp_admin_url': self.url.rstrip('/') + "/wp-admin/"
                    }
                    send_plugin_notification(self.smtp_config, plugin_data, success=reactivation_success)
                except Exception as e:
                    print(f"Failed to send notification email: {e}")

            # Notify UI if callback exists
            if self.callback:
                self.callback(status_text, was_activated)

            # Wait for configured interval (in seconds), but check stop event frequently
            for _ in range(int(self.interval)):
                if self._stop_event.is_set():
                    break
                time.sleep(1)

        self.running = False
