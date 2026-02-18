"""
SQLite implementation for benchmarking.
Uses normalized schema with JSON fields for complex nested data.
"""

import sqlite3
import json
from typing import List, Dict, Any, Optional
from datetime import datetime
import os


class SQLiteDB:
    """SQLite database implementation with optimized schema and operations."""

    def __init__(self, db_path: str = "benchmark.db"):
        """
        Initialize SQLite database connection.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self.conn: Optional[sqlite3.Connection] = None

    def connect(self):
        """Establish connection to SQLite database."""
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        # Enable WAL mode for better concurrent performance
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA synchronous=NORMAL")
        self.conn.execute("PRAGMA cache_size=-64000")  # 64MB cache

    def disconnect(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()
            self.conn = None

    def reset(self):
        """Delete the database file and reconnect."""
        self.disconnect()
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
            # Also remove WAL files
            for suffix in ['-wal', '-shm']:
                wal_file = self.db_path + suffix
                if os.path.exists(wal_file):
                    os.remove(wal_file)
        self.connect()

    def create_schema(self):
        """Create all tables with appropriate schema."""
        cursor = self.conn.cursor()

        # Users table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                username TEXT NOT NULL,
                email TEXT NOT NULL,
                full_name TEXT NOT NULL,
                age INTEGER,
                country TEXT,
                city TEXT,
                registration_date TEXT,
                last_login TEXT,
                is_active INTEGER,
                preferences TEXT,  -- JSON
                tags TEXT  -- JSON array
            )
        """)

        # Products table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                category TEXT,
                price REAL,
                cost REAL,
                stock_quantity INTEGER,
                rating REAL,
                review_count INTEGER,
                is_featured INTEGER,
                specifications TEXT,  -- JSON
                tags TEXT,  -- JSON array
                created_at TEXT
            )
        """)

        # Orders table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY,
                user_id INTEGER,
                order_date TEXT,
                status TEXT,
                total_amount REAL,
                discount REAL,
                tax REAL,
                shipping_address TEXT,  -- JSON
                items TEXT,  -- JSON array
                payment_method TEXT,
                notes TEXT,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)

        # Events table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY,
                event_type TEXT NOT NULL,
                user_id INTEGER,
                timestamp TEXT,
                session_id TEXT,
                page_url TEXT,
                metadata TEXT,  -- JSON
                duration_ms INTEGER,
                ip_address TEXT,
                user_agent TEXT,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)

        # Sessions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY,
                user_id INTEGER,
                start_time TEXT,
                end_time TEXT,
                duration_seconds INTEGER,
                page_views INTEGER,
                actions TEXT,  -- JSON array
                device_info TEXT,  -- JSON
                location TEXT,  -- JSON
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)

        # Tickets table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tickets (
                id INTEGER PRIMARY KEY,
                user_id INTEGER,
                subject TEXT,
                description TEXT,
                priority TEXT,
                status TEXT,
                created_at TEXT,
                updated_at TEXT,
                resolved_at TEXT,
                assignee TEXT,
                comments TEXT,  -- JSON array
                tags TEXT,  -- JSON array
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)

        # Logs table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS logs (
                id INTEGER PRIMARY KEY,
                timestamp TEXT,
                level TEXT,
                logger_name TEXT,
                message TEXT,
                exception TEXT,  -- JSON
                context TEXT,  -- JSON
                hostname TEXT,
                process_id INTEGER
            )
        """)

        # Payments table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS payments (
                id INTEGER PRIMARY KEY,
                order_id INTEGER,
                user_id INTEGER,
                amount REAL,
                currency TEXT,
                payment_method TEXT,
                status TEXT,
                transaction_id TEXT,
                processed_at TEXT,
                card_details TEXT,  -- JSON
                billing_address TEXT,  -- JSON
                metadata TEXT,  -- JSON
                FOREIGN KEY (order_id) REFERENCES orders(id),
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)

        self.conn.commit()

    def create_indexes(self):
        """Create indexes for common query patterns."""
        cursor = self.conn.cursor()

        indexes = [
            # Users indexes
            "CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)",
            "CREATE INDEX IF NOT EXISTS idx_users_country ON users(country)",
            "CREATE INDEX IF NOT EXISTS idx_users_registration_date ON users(registration_date)",
            "CREATE INDEX IF NOT EXISTS idx_users_is_active ON users(is_active)",

            # Products indexes
            "CREATE INDEX IF NOT EXISTS idx_products_category ON products(category)",
            "CREATE INDEX IF NOT EXISTS idx_products_price ON products(price)",
            "CREATE INDEX IF NOT EXISTS idx_products_rating ON products(rating)",
            "CREATE INDEX IF NOT EXISTS idx_products_created_at ON products(created_at)",

            # Orders indexes
            "CREATE INDEX IF NOT EXISTS idx_orders_user_id ON orders(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_orders_order_date ON orders(order_date)",
            "CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status)",
            "CREATE INDEX IF NOT EXISTS idx_orders_total_amount ON orders(total_amount)",

            # Events indexes
            "CREATE INDEX IF NOT EXISTS idx_events_event_type ON events(event_type)",
            "CREATE INDEX IF NOT EXISTS idx_events_user_id ON events(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_events_timestamp ON events(timestamp)",
            "CREATE INDEX IF NOT EXISTS idx_events_session_id ON events(session_id)",

            # Sessions indexes
            "CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON sessions(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_sessions_start_time ON sessions(start_time)",
            "CREATE INDEX IF NOT EXISTS idx_sessions_duration ON sessions(duration_seconds)",

            # Tickets indexes
            "CREATE INDEX IF NOT EXISTS idx_tickets_user_id ON tickets(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_tickets_status ON tickets(status)",
            "CREATE INDEX IF NOT EXISTS idx_tickets_priority ON tickets(priority)",
            "CREATE INDEX IF NOT EXISTS idx_tickets_created_at ON tickets(created_at)",

            # Logs indexes
            "CREATE INDEX IF NOT EXISTS idx_logs_timestamp ON logs(timestamp)",
            "CREATE INDEX IF NOT EXISTS idx_logs_level ON logs(level)",
            "CREATE INDEX IF NOT EXISTS idx_logs_logger_name ON logs(logger_name)",

            # Payments indexes
            "CREATE INDEX IF NOT EXISTS idx_payments_order_id ON payments(order_id)",
            "CREATE INDEX IF NOT EXISTS idx_payments_user_id ON payments(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_payments_status ON payments(status)",
            "CREATE INDEX IF NOT EXISTS idx_payments_processed_at ON payments(processed_at)",
        ]

        for index_sql in indexes:
            cursor.execute(index_sql)

        self.conn.commit()

    def drop_indexes(self):
        """Drop all indexes (except implicit PRIMARY KEY indexes)."""
        cursor = self.conn.cursor()

        # Get all index names
        cursor.execute("""
            SELECT name FROM sqlite_master
            WHERE type='index' AND name LIKE 'idx_%'
        """)

        indexes = [row[0] for row in cursor.fetchall()]

        for index_name in indexes:
            cursor.execute(f"DROP INDEX IF EXISTS {index_name}")

        self.conn.commit()

    def _serialize_datetime(self, obj: Any) -> Any:
        """Convert datetime objects to ISO format strings recursively."""
        if isinstance(obj, datetime):
            return obj.isoformat()
        elif isinstance(obj, dict):
            return {key: self._serialize_datetime(val) for key, val in obj.items()}
        elif isinstance(obj, list):
            return [self._serialize_datetime(item) for item in obj]
        return obj

    def _prepare_record(self, record: Dict[str, Any], json_fields: List[str]) -> Dict[str, Any]:
        """Prepare a record for insertion by serializing JSON fields."""
        prepared = {}
        for key, value in record.items():
            if key in json_fields:
                # Serialize datetime objects before JSON encoding
                serialized_value = self._serialize_datetime(value)
                prepared[key] = json.dumps(serialized_value) if serialized_value is not None else None
            else:
                prepared[key] = self._serialize_datetime(value)
        return prepared

    def bulk_insert(self, table_name: str, records: List[Dict[str, Any]], batch_size: int = 1000):
        """
        Bulk insert records into a table with batching and transactions.

        Args:
            table_name: Name of the table
            records: List of record dictionaries
            batch_size: Number of records per batch
        """
        if not records:
            return

        # Define which fields should be JSON-encoded for each table
        json_fields_map = {
            'users': ['preferences', 'tags'],
            'products': ['specifications', 'tags'],
            'orders': ['shipping_address', 'items'],
            'events': ['metadata'],
            'sessions': ['actions', 'device_info', 'location'],
            'tickets': ['comments', 'tags'],
            'logs': ['exception', 'context'],
            'payments': ['card_details', 'billing_address', 'metadata']
        }

        json_fields = json_fields_map.get(table_name, [])

        cursor = self.conn.cursor()

        # Prepare placeholders
        first_record = records[0]
        columns = list(first_record.keys())
        placeholders = ','.join(['?' for _ in columns])
        column_names = ','.join(columns)

        insert_sql = f"INSERT INTO {table_name} ({column_names}) VALUES ({placeholders})"

        # Batch insert with transactions
        for i in range(0, len(records), batch_size):
            batch = records[i:i + batch_size]

            # Prepare batch data
            batch_data = []
            for record in batch:
                prepared = self._prepare_record(record, json_fields)
                batch_data.append([prepared[col] for col in columns])

            # Insert batch within transaction
            cursor.execute("BEGIN")
            try:
                cursor.executemany(insert_sql, batch_data)
                cursor.execute("COMMIT")
            except Exception as e:
                cursor.execute("ROLLBACK")
                raise e

    def execute_query(self, sql: str, params: tuple = ()) -> List[Dict[str, Any]]:
        """
        Execute a SELECT query and return results as list of dictionaries.

        Args:
            sql: SQL query string
            params: Query parameters

        Returns:
            List of result dictionaries
        """
        cursor = self.conn.cursor()
        cursor.execute(sql, params)
        rows = cursor.fetchall()

        # Convert Row objects to dictionaries
        results = []
        for row in rows:
            results.append(dict(row))

        return results

    def execute_write(self, sql: str, params: tuple = ()):
        """
        Execute an INSERT/UPDATE/DELETE query.

        Args:
            sql: SQL query string
            params: Query parameters
        """
        cursor = self.conn.cursor()
        cursor.execute(sql, params)
        self.conn.commit()

    def get_table_count(self, table_name: str) -> int:
        """Get the number of rows in a table."""
        cursor = self.conn.cursor()
        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        return cursor.fetchone()[0]

    def get_database_size(self) -> int:
        """Get the size of the database file in bytes."""
        if os.path.exists(self.db_path):
            size = os.path.getsize(self.db_path)
            # Add WAL file size if exists
            wal_file = self.db_path + '-wal'
            if os.path.exists(wal_file):
                size += os.path.getsize(wal_file)
            return size
        return 0

    def vacuum(self):
        """Run VACUUM to optimize database."""
        self.conn.execute("VACUUM")

    def analyze(self):
        """Run ANALYZE to update query planner statistics."""
        self.conn.execute("ANALYZE")
