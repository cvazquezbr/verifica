import sqlite3
import datetime

class Database:
    # Status Mapping
    STATUS_ERROR = 0
    STATUS_ACTIVE = 1
    STATUS_REACTIVATED = 2
    STATUS_ACT_FAILED = 3

    def __init__(self, db_name="monitor.db"):
        self.db_name = db_name
        self.init_db()

    def get_connection(self):
        return sqlite3.connect(self.db_name)

    def init_db(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            # Table for WordPress credentials - Enforce single record with id=1
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS sites (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    url TEXT NOT NULL,
                    username TEXT NOT NULL,
                    app_password TEXT NOT NULL,
                    interval_seconds INTEGER DEFAULT 60,
                    is_active INTEGER DEFAULT 1,
                    smtp_host TEXT,
                    smtp_port INTEGER,
                    smtp_user TEXT,
                    smtp_pass TEXT,
                    smtp_ssl INTEGER DEFAULT 1,
                    smtp_sender_name TEXT,
                    smtp_receiver TEXT,
                    smtp_cc TEXT,
                    auto_start_monitoring INTEGER DEFAULT 0,
                    start_with_windows INTEGER DEFAULT 0
                )
            ''')
            # Table for monitoring logs - status is now INTEGER
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    site_id INTEGER DEFAULT 1,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    status INTEGER,
                    was_activated INTEGER,
                    FOREIGN KEY (site_id) REFERENCES sites (id)
                )
            ''')
            conn.commit()
            self.migrate_db()

    def migrate_db(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # 1. Handle sites table migration to single record
            cursor.execute("SELECT COUNT(*) FROM sites")
            count = cursor.fetchone()[0]
            if count > 0:
                cursor.execute("SELECT id FROM sites WHERE is_active = 1 ORDER BY id DESC LIMIT 1")
                active_id = cursor.fetchone()
                if not active_id:
                    cursor.execute("SELECT id FROM sites ORDER BY id DESC LIMIT 1")
                    active_id = cursor.fetchone()

                if active_id and active_id[0] != 1:
                    # Move the selected site to ID 1
                    cursor.execute("SELECT * FROM sites WHERE id = ?", (active_id[0],))
                    row = cursor.fetchone()
                    # We need to be careful with column order.
                    # PRAGMA table_info gives us the order.
                    cursor.execute("PRAGMA table_info(sites)")
                    cols = [info[1] for info in cursor.fetchall()]

                    # Delete all and insert the chosen one as id=1
                    cursor.execute("DELETE FROM sites")
                    placeholders = ", ".join(["?" for _ in range(len(cols))])
                    # Update row to have id=1
                    new_row = list(row)
                    new_row[0] = 1
                    cursor.execute(f"INSERT INTO sites ({', '.join(cols)}) VALUES ({placeholders})", new_row)

                    # Update existing logs to point to site_id 1
                    cursor.execute("UPDATE logs SET site_id = 1")
                    conn.commit()

            # 2. Check for missing columns (from previous versions)
            cursor.execute("PRAGMA table_info(sites)")
            columns = [info[1] for info in cursor.fetchall()]

            if 'interval_seconds' not in columns:
                if 'interval_minutes' in columns:
                    cursor.execute("ALTER TABLE sites RENAME COLUMN interval_minutes TO interval_seconds")
                    cursor.execute("UPDATE sites SET interval_seconds = interval_seconds * 60")
                else:
                    cursor.execute("ALTER TABLE sites ADD COLUMN interval_seconds INTEGER DEFAULT 60")
                conn.commit()

            new_columns = [
                ('smtp_host', 'TEXT'),
                ('smtp_port', 'INTEGER'),
                ('smtp_user', 'TEXT'),
                ('smtp_pass', 'TEXT'),
                ('smtp_ssl', 'INTEGER DEFAULT 1'),
                ('smtp_sender_name', 'TEXT'),
                ('smtp_receiver', 'TEXT'),
                ('smtp_cc', 'TEXT'),
                ('auto_start_monitoring', 'INTEGER DEFAULT 0'),
                ('start_with_windows', 'INTEGER DEFAULT 0')
            ]

            changed = False
            for col_name, col_type in new_columns:
                if col_name not in columns:
                    cursor.execute(f"ALTER TABLE sites ADD COLUMN {col_name} {col_type}")
                    changed = True

            if changed:
                conn.commit()

            # 3. Migrate logs status from TEXT to INTEGER if needed
            cursor.execute("PRAGMA table_info(logs)")
            log_columns = cursor.fetchall()
            status_type = [info[2] for info in log_columns if info[1] == 'status'][0]

            if status_type.upper() == 'TEXT':
                # Convert existing data
                cursor.execute("UPDATE logs SET status = ? WHERE status = 'Active' OR status = 'OK'", (self.STATUS_ACTIVE,))
                cursor.execute("UPDATE logs SET status = ? WHERE status = 'Reactivated'", (self.STATUS_REACTIVATED,))
                cursor.execute("UPDATE logs SET status = ? WHERE status = 'Activation Failed'", (self.STATUS_ACT_FAILED,))
                cursor.execute("UPDATE logs SET status = ? WHERE status LIKE 'Error%'", (self.STATUS_ERROR,))

                # SQLite doesn't support easy ALTER COLUMN.
                # But it's dynamic typing, so we can just leave it as is for now or recreate.
                # Given we want to minimize space, recreating is better but risky if many logs.
                # However, the user said they don't mind losing data if they use the "Clear" button.
                pass

    def save_site(self, url, username, app_password, interval=60, smtp_data=None, auto_start=0, start_windows=0):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if smtp_data:
                cursor.execute(
                    """INSERT OR REPLACE INTO sites (
                        id, url, username, app_password, interval_seconds, is_active,
                        smtp_host, smtp_port, smtp_user, smtp_pass, smtp_ssl,
                        smtp_sender_name, smtp_receiver, smtp_cc,
                        auto_start_monitoring, start_with_windows
                    ) VALUES (1, ?, ?, ?, ?, 1, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (url, username, app_password, interval,
                     smtp_data.get('host'), smtp_data.get('port'), smtp_data.get('user'),
                     smtp_data.get('pass'), smtp_data.get('ssl'), smtp_data.get('sender_name'),
                     smtp_data.get('receiver'), smtp_data.get('cc'),
                     auto_start, start_windows)
                )
            else:
                cursor.execute(
                    """INSERT OR REPLACE INTO sites (
                        id, url, username, app_password, interval_seconds, is_active,
                        auto_start_monitoring, start_with_windows
                    ) VALUES (1, ?, ?, ?, ?, 1, ?, ?)""",
                    (url, username, app_password, interval, auto_start, start_windows)
                )
            conn.commit()
            return 1

    def get_active_site(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, url, username, app_password, interval_seconds,
                       smtp_host, smtp_port, smtp_user, smtp_pass, smtp_ssl,
                       smtp_sender_name, smtp_receiver, smtp_cc,
                       auto_start_monitoring, start_with_windows
                FROM sites WHERE id = 1
            """)
            return cursor.fetchone()

    def log_event(self, site_id, status_code, was_activated):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO logs (site_id, status, was_activated) VALUES (?, ?, ?)",
                (1, status_code, 1 if was_activated else 0)
            )
            conn.commit()

    def clear_logs_and_optimize(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM logs")
            conn.commit()
            cursor.execute("VACUUM")

    def get_stats_hourly(self, site_id, date_str):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT
                    strftime('%H', timestamp) as hour,
                    COUNT(*) as total_checks,
                    SUM(was_activated) as activations
                FROM logs
                WHERE date(timestamp) = ?
                GROUP BY hour
                ORDER BY hour
            ''', (date_str,))
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
                GROUP BY day
                ORDER BY day DESC
                LIMIT ?
            ''', (limit,))
            return cursor.fetchall()
