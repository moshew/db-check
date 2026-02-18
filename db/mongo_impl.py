"""
MongoDB implementation for benchmarking.
Uses document-based schema with embedded documents and arrays.
"""

from pymongo import MongoClient, ASCENDING, DESCENDING
from pymongo.collection import Collection
from pymongo.database import Database
from typing import List, Dict, Any, Optional
from datetime import datetime


class MongoDB:
    """MongoDB database implementation with optimized operations."""

    def __init__(self, connection_string: str = "mongodb://admin:password123@localhost:27017/",
                 database_name: str = "benchmark"):
        """
        Initialize MongoDB connection.

        Args:
            connection_string: MongoDB connection string
            database_name: Name of the database to use
        """
        self.connection_string = connection_string
        self.database_name = database_name
        self.client: Optional[MongoClient] = None
        self.db: Optional[Database] = None

    def connect(self):
        """Establish connection to MongoDB."""
        self.client = MongoClient(self.connection_string, serverSelectionTimeoutMS=5000)
        self.db = self.client[self.database_name]
        # Test connection
        self.client.admin.command('ping')

    def disconnect(self):
        """Close MongoDB connection."""
        if self.client:
            self.client.close()
            self.client = None
            self.db = None

    def reset(self):
        """Drop all collections in the database."""
        if self.db is not None:
            collection_names = self.db.list_collection_names()
            for collection_name in collection_names:
                self.db[collection_name].drop()

    def create_schema(self):
        """
        Create collections. In MongoDB, collections are created automatically,
        but we can ensure they exist and set up validation if needed.
        """
        # Collections will be created automatically on first insert
        # We just ensure the database exists
        collection_names = ['users', 'products', 'orders', 'events',
                           'sessions', 'tickets', 'logs', 'payments']

        for name in collection_names:
            if name not in self.db.list_collection_names():
                self.db.create_collection(name)

    def create_indexes(self):
        """Create indexes for common query patterns."""
        # Users indexes
        self.db.users.create_index([("email", ASCENDING)])
        self.db.users.create_index([("country", ASCENDING)])
        self.db.users.create_index([("registration_date", ASCENDING)])
        self.db.users.create_index([("is_active", ASCENDING)])
        self.db.users.create_index([("country", ASCENDING), ("is_active", ASCENDING)])

        # Products indexes
        self.db.products.create_index([("category", ASCENDING)])
        self.db.products.create_index([("price", ASCENDING)])
        self.db.products.create_index([("rating", DESCENDING)])
        self.db.products.create_index([("created_at", ASCENDING)])
        self.db.products.create_index([("category", ASCENDING), ("price", ASCENDING)])

        # Orders indexes
        self.db.orders.create_index([("user_id", ASCENDING)])
        self.db.orders.create_index([("order_date", ASCENDING)])
        self.db.orders.create_index([("status", ASCENDING)])
        self.db.orders.create_index([("total_amount", ASCENDING)])
        self.db.orders.create_index([("user_id", ASCENDING), ("order_date", DESCENDING)])

        # Events indexes
        self.db.events.create_index([("event_type", ASCENDING)])
        self.db.events.create_index([("user_id", ASCENDING)])
        self.db.events.create_index([("timestamp", ASCENDING)])
        self.db.events.create_index([("session_id", ASCENDING)])
        self.db.events.create_index([("event_type", ASCENDING), ("timestamp", DESCENDING)])

        # Sessions indexes
        self.db.sessions.create_index([("user_id", ASCENDING)])
        self.db.sessions.create_index([("start_time", ASCENDING)])
        self.db.sessions.create_index([("duration_seconds", ASCENDING)])
        self.db.sessions.create_index([("user_id", ASCENDING), ("start_time", DESCENDING)])

        # Tickets indexes
        self.db.tickets.create_index([("user_id", ASCENDING)])
        self.db.tickets.create_index([("status", ASCENDING)])
        self.db.tickets.create_index([("priority", ASCENDING)])
        self.db.tickets.create_index([("created_at", ASCENDING)])
        self.db.tickets.create_index([("status", ASCENDING), ("priority", ASCENDING)])

        # Logs indexes
        self.db.logs.create_index([("timestamp", ASCENDING)])
        self.db.logs.create_index([("level", ASCENDING)])
        self.db.logs.create_index([("logger_name", ASCENDING)])
        self.db.logs.create_index([("level", ASCENDING), ("timestamp", DESCENDING)])

        # Payments indexes
        self.db.payments.create_index([("order_id", ASCENDING)])
        self.db.payments.create_index([("user_id", ASCENDING)])
        self.db.payments.create_index([("status", ASCENDING)])
        self.db.payments.create_index([("processed_at", ASCENDING)])
        self.db.payments.create_index([("user_id", ASCENDING), ("processed_at", DESCENDING)])

    def drop_indexes(self):
        """Drop all non-_id indexes."""
        collection_names = ['users', 'products', 'orders', 'events',
                           'sessions', 'tickets', 'logs', 'payments']

        for collection_name in collection_names:
            collection = self.db[collection_name]
            # Drop all indexes except _id
            indexes = collection.list_indexes()
            for index in indexes:
                if index['name'] != '_id_':
                    collection.drop_index(index['name'])

    def bulk_insert(self, collection_name: str, records: List[Dict[str, Any]], batch_size: int = 1000):
        """
        Bulk insert records into a collection with batching.

        Args:
            collection_name: Name of the collection
            records: List of document dictionaries
            batch_size: Number of documents per batch
        """
        if not records:
            return

        collection = self.db[collection_name]

        # Batch insert
        for i in range(0, len(records), batch_size):
            batch = records[i:i + batch_size]
            # Convert datetime objects if needed
            batch_prepared = [self._prepare_document(doc) for doc in batch]
            collection.insert_many(batch_prepared, ordered=False)

    def _prepare_document(self, doc: Dict[str, Any]) -> Dict[str, Any]:
        """
        Prepare a document for insertion.
        MongoDB handles most Python types natively, including datetime.
        We use '_id' field for our custom IDs if 'id' is present.
        """
        prepared = doc.copy()

        # Use 'id' as '_id' if present
        if 'id' in prepared:
            prepared['_id'] = prepared.pop('id')

        return prepared

    def execute_query(self, collection_name: str, filter_query: Dict[str, Any],
                     projection: Optional[Dict[str, Any]] = None,
                     sort: Optional[List[tuple]] = None,
                     limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Execute a find query and return results.

        Args:
            collection_name: Name of the collection
            filter_query: MongoDB filter query
            projection: Fields to include/exclude
            sort: Sort specification
            limit: Maximum number of documents to return

        Returns:
            List of result dictionaries
        """
        collection = self.db[collection_name]
        cursor = collection.find(filter_query, projection)

        if sort:
            cursor = cursor.sort(sort)

        if limit:
            cursor = cursor.limit(limit)

        results = list(cursor)

        # Convert _id back to id for consistency
        for result in results:
            if '_id' in result:
                result['id'] = result.pop('_id')

        return results

    def execute_aggregation(self, collection_name: str, pipeline: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Execute an aggregation pipeline.

        Args:
            collection_name: Name of the collection
            pipeline: Aggregation pipeline stages

        Returns:
            List of result dictionaries
        """
        collection = self.db[collection_name]
        results = list(collection.aggregate(pipeline, allowDiskUse=True))
        return results

    def execute_write(self, collection_name: str, operation: str, *args, **kwargs):
        """
        Execute a write operation (insert, update, delete).

        Args:
            collection_name: Name of the collection
            operation: Operation name (insert_one, update_many, etc.)
            *args, **kwargs: Operation arguments
        """
        collection = self.db[collection_name]
        method = getattr(collection, operation)
        return method(*args, **kwargs)

    def get_collection_count(self, collection_name: str) -> int:
        """Get the number of documents in a collection."""
        return self.db[collection_name].count_documents({})

    def get_database_size(self) -> int:
        """Get the size of the database in bytes."""
        stats = self.db.command("dbStats")
        return stats.get("dataSize", 0) + stats.get("indexSize", 0)

    def get_collection(self, collection_name: str) -> Collection:
        """Get a collection object."""
        return self.db[collection_name]
