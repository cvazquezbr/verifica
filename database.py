import sqlite3
import datetime

class Database:
    def __init__(self, db_name="monitor.db"):
        self.db_name = db_name
        self.init_db()

    def get_connection(self):
        return sqlite3.connect(self.db_name)

    def init_db(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            # Table for WordPress credentials
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS sites (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    url TEXT NOT NULL,
                    username TEXT NOT NULL,
                    app_password TEXT NOT NULL,
                    interval_minutes INTEGER DEFAULT 1,
                    is_active INTEGER DEFAULT 0
                )
            ''')
            # Table for monitoring logs
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    site_id INTEGER,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    status TEXT,
                    was_activated INTEGER,
                    FOREIGN KEY (site_id) REFERENCES sites (id)
                )
            ''')
            conn.commit()
            self.migrate_db()

    def migrate_db(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            # Check if interval_minutes exists
            cursor.execute("PRAGMA table_info(sites)")
            columns = [info[1] for info in cursor.fetchall()]
            if 'interval_minutes' not in columns:
                cursor.execute("ALTER TABLE sites ADD COLUMN interval_minutes INTEGER DEFAULT 1")
                conn.commit()

    def save_site(self, url, username, app_password, interval=1):
        # We only want one active site as per requirements, but let's allow multiple entries
        # and just flag which one is used.
        with self.get_connection() as conn:
            cursor = conn.cursor()
            # Reset all to inactive first if we are setting a new one
            cursor.execute("UPDATE sites SET is_active = 0")
            cursor.execute(
                "INSERT INTO sites (url, username, app_password, interval_minutes, is_active) VALUES (?, ?, ?, ?, 1)",
                (url, username, app_password, interval)
            )
            conn.commit()
            return cursor.lastrowid

    def get_active_site(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, url, username, app_password, interval_minutes FROM sites WHERE is_active = 1 LIMIT 1")
            return cursor.fetchone()

    def log_event(self, site_id, status, was_activated):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO logs (site_id, status, was_activated) VALUES (?, ?, ?)",
                (site_id, status, 1 if was_activated else 0)
            )
            conn.commit()

    def get_stats_hourly(self, site_id, date_str):
        # date_str in YYYY-MM-DD format
        with self.get_connection() as conn:
            cursor = conn.cursor()
            # Availability = (Total checks - Times it needed activation) / Total checks
            # We want it grouped by hour
            cursor.execute('''
                SELECT
                    strftime('%H', timestamp) as hour,
                    COUNT(*) as total_checks,
                    SUM(was_activated) as activations
                FROM logs
                WHERE site_id = ? AND date(timestamp) = ?
                GROUP BY hour
                ORDER BY hour
            ''', (site_id, date_str))
            return cursor.fetchall()

    def get_stats_daily(self, site_id, limit=30):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT
                    date(timestamp) as day,
                    COUNT(*) as total_checks,
                    SUM(was_activated) as activations
                FROM logs
                WHERE site_id = ?
                GROUP BY day
                ORDER BY day DESC
                LIMIT ?
            ''', (site_id, limit))
            return cursor.fetchall()
