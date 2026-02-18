"""
Query definitions for benchmarking.
Each query has both SQLite and MongoDB implementations.
"""

from typing import Dict, Any, Callable, List
from datetime import datetime, timedelta


class QueryDefinitions:
    """Define all benchmark queries for both databases."""

    @staticmethod
    def get_all_queries() -> List[Dict[str, Any]]:
        """
        Get all query definitions.

        Returns:
            List of query dictionaries with metadata and implementations
        """
        return [
            {
                'id': 'Q1',
                'name': 'Active Users by Country',
                'description': 'Find all active users in a specific country',
                'expected_size': 'medium',
                'sqlite': QueryDefinitions.q1_sqlite,
                'mongo': QueryDefinitions.q1_mongo
            },
            {
                'id': 'Q2',
                'name': 'High-Value Orders',
                'description': 'Find orders above $500 with status filter',
                'expected_size': 'large',
                'sqlite': QueryDefinitions.q2_sqlite,
                'mongo': QueryDefinitions.q2_mongo
            },
            {
                'id': 'Q3',
                'name': 'Recent Events by Type',
                'description': 'Get all purchase events from last 7 days',
                'expected_size': 'medium',
                'sqlite': QueryDefinitions.q3_sqlite,
                'mongo': QueryDefinitions.q3_mongo
            },
            {
                'id': 'Q4',
                'name': 'Product Search with Multiple Filters',
                'description': 'Find featured products in category with rating > 4.0',
                'expected_size': 'small',
                'sqlite': QueryDefinitions.q4_sqlite,
                'mongo': QueryDefinitions.q4_mongo
            },
            {
                'id': 'Q5',
                'name': 'User Order History with Join',
                'description': 'Get user info with their order count and total spent',
                'expected_size': 'large',
                'sqlite': QueryDefinitions.q5_sqlite,
                'mongo': QueryDefinitions.q5_mongo
            },
            {
                'id': 'Q6',
                'name': 'Session Duration Analysis',
                'description': 'Find sessions longer than 30 minutes with high page views',
                'expected_size': 'medium',
                'sqlite': QueryDefinitions.q6_sqlite,
                'mongo': QueryDefinitions.q6_mongo
            },
            {
                'id': 'Q7',
                'name': 'Ticket Status Aggregation',
                'description': 'Count tickets by status and priority',
                'expected_size': 'small',
                'sqlite': QueryDefinitions.q7_sqlite,
                'mongo': QueryDefinitions.q7_mongo
            },
            {
                'id': 'Q8',
                'name': 'Error Log Analysis',
                'description': 'Find ERROR/CRITICAL logs with exception details',
                'expected_size': 'large',
                'sqlite': QueryDefinitions.q8_sqlite,
                'mongo': QueryDefinitions.q8_mongo
            },
            {
                'id': 'Q9',
                'name': 'Payment Method Statistics',
                'description': 'Aggregate payment amounts by method and status',
                'expected_size': 'small',
                'sqlite': QueryDefinitions.q9_sqlite,
                'mongo': QueryDefinitions.q9_mongo
            },
            {
                'id': 'Q10',
                'name': 'Top Selling Products',
                'description': 'Find top 20 products by order frequency with revenue',
                'expected_size': 'small',
                'sqlite': QueryDefinitions.q10_sqlite,
                'mongo': QueryDefinitions.q10_mongo
            },
            {
                'id': 'Q11',
                'name': 'User Registration Trends',
                'description': 'Count users registered per month',
                'expected_size': 'small',
                'sqlite': QueryDefinitions.q11_sqlite,
                'mongo': QueryDefinitions.q11_mongo
            },
            {
                'id': 'Q12',
                'name': 'Complex Multi-Table Join',
                'description': 'Join users, orders, and payments with filters',
                'expected_size': 'medium',
                'sqlite': QueryDefinitions.q12_sqlite,
                'mongo': QueryDefinitions.q12_mongo
            },
            {
                'id': 'Q13',
                'name': 'Time Range with Aggregation',
                'description': 'Average order value by status for last 6 months',
                'expected_size': 'small',
                'sqlite': QueryDefinitions.q13_sqlite,
                'mongo': QueryDefinitions.q13_mongo
            },
            {
                'id': 'Q14',
                'name': 'Text Pattern Search',
                'description': 'Search products with name pattern and price range',
                'expected_size': 'medium',
                'sqlite': QueryDefinitions.q14_sqlite,
                'mongo': QueryDefinitions.q14_mongo
            },
            {
                'id': 'Q15',
                'name': 'User Activity Summary',
                'description': 'Complex aggregation: users with orders, events, and sessions',
                'expected_size': 'large',
                'sqlite': QueryDefinitions.q15_sqlite,
                'mongo': QueryDefinitions.q15_mongo
            }
        ]

    @staticmethod
    def get_query_complexity_profiles() -> Dict[str, Dict[str, Any]]:
        """
        Return per-query complexity metadata for reporting.

        Levels:
          - low
          - medium
          - high
          - very_high
        """
        return {
            'Q1': {
                'level': 'low',
                'why': 'Simple selective filter + single sort',
                'features': ['single collection/table filter', 'single sort key']
            },
            'Q2': {
                'level': 'medium',
                'why': 'Range + IN filter with sorting',
                'features': ['range predicate', 'set membership predicate', 'sort']
            },
            'Q3': {
                'level': 'medium',
                'why': 'Time-window filtering + sort',
                'features': ['time-range predicate', 'single sort key']
            },
            'Q4': {
                'level': 'medium',
                'why': 'Multiple predicates and compound ordering with limit',
                'features': ['multi-filter predicate', 'multi-column sort', 'top-k limit']
            },
            'Q5': {
                'level': 'high',
                'why': 'Join/lookup + aggregate metrics + HAVING-style filter',
                'features': ['join/lookup', 'group aggregation', 'derived metrics', 'post-aggregation filtering']
            },
            'Q6': {
                'level': 'low',
                'why': 'Simple two-threshold filter and sort',
                'features': ['range predicates', 'single sort key']
            },
            'Q7': {
                'level': 'high',
                'why': 'Conditional aggregation over grouped dimensions',
                'features': ['group by multiple dimensions', 'conditional aggregate']
            },
            'Q8': {
                'level': 'medium',
                'why': 'Selective logging filter with high result cap',
                'features': ['set membership predicate', 'null-check predicate', 'limit']
            },
            'Q9': {
                'level': 'high',
                'why': 'Multi-metric aggregation over grouped dimensions',
                'features': ['group aggregation', 'min/max/avg/sum metrics']
            },
            'Q10': {
                'level': 'very_high',
                'why': 'Array expansion + join/lookup + aggregate + ranking',
                'features': ['array unnest/unwind', 'join/lookup', 'group aggregation', 'top-k ranking']
            },
            'Q11': {
                'level': 'medium',
                'why': 'Time bucketing with grouped counts',
                'features': ['date bucketing', 'group aggregation']
            },
            'Q12': {
                'level': 'very_high',
                'why': 'Multi-join query across users/orders/payments with filtering and projection',
                'features': ['multiple joins/lookups', 'time filter', 'status filter', 'sort + limit']
            },
            'Q13': {
                'level': 'high',
                'why': 'Time-window aggregate statistics by status',
                'features': ['time-range predicate', 'group aggregation', 'multi-metric rollup']
            },
            'Q14': {
                'level': 'high',
                'why': 'Text-pattern search + numeric range + ordering',
                'features': ['regex/LIKE pattern', 'numeric range', 'sort + limit']
            },
            'Q15': {
                'level': 'very_high',
                'why': 'Correlated multi-source activity summary with three joins/lookups and derived aggregates',
                'features': ['multiple correlated lookups', 'derived counters', 'multi-source aggregation', 'post-aggregation filtering', 'sort + large limit']
            }
        }

    # Query implementations

    @staticmethod
    def q1_sqlite(db) -> List[Dict]:
        """Q1: Active users in USA"""
        sql = """
            SELECT id, username, email, full_name, city, registration_date
            FROM users
            WHERE country = 'United States' AND is_active = 1
            ORDER BY registration_date DESC
        """
        return db.execute_query(sql)

    @staticmethod
    def q1_mongo(db) -> List[Dict]:
        """Q1: Active users in USA"""
        return db.execute_query(
            'users',
            {'country': 'United States', 'is_active': True},
            projection={'username': 1, 'email': 1, 'full_name': 1, 'city': 1, 'registration_date': 1},
            sort=[('registration_date', -1)]
        )

    @staticmethod
    def q2_sqlite(db) -> List[Dict]:
        """Q2: High-value orders"""
        sql = """
            SELECT id, user_id, order_date, status, total_amount, payment_method
            FROM orders
            WHERE total_amount > 500 AND status IN ('confirmed', 'processing', 'shipped')
            ORDER BY total_amount DESC
        """
        return db.execute_query(sql)

    @staticmethod
    def q2_mongo(db) -> List[Dict]:
        """Q2: High-value orders"""
        return db.execute_query(
            'orders',
            {
                'total_amount': {'$gt': 500},
                'status': {'$in': ['confirmed', 'processing', 'shipped']}
            },
            projection={'user_id': 1, 'order_date': 1, 'status': 1, 'total_amount': 1, 'payment_method': 1},
            sort=[('total_amount', -1)]
        )

    @staticmethod
    def q3_sqlite(db) -> List[Dict]:
        """Q3: Recent purchase events"""
        cutoff_date = (datetime.now() - timedelta(days=7)).isoformat()
        sql = """
            SELECT id, event_type, user_id, timestamp, page_url, duration_ms
            FROM events
            WHERE event_type = 'purchase' AND timestamp > ?
            ORDER BY timestamp DESC
        """
        return db.execute_query(sql, (cutoff_date,))

    @staticmethod
    def q3_mongo(db) -> List[Dict]:
        """Q3: Recent purchase events"""
        cutoff_date = datetime.now() - timedelta(days=7)
        return db.execute_query(
            'events',
            {
                'event_type': 'purchase',
                'timestamp': {'$gt': cutoff_date}
            },
            projection={'event_type': 1, 'user_id': 1, 'timestamp': 1, 'page_url': 1, 'duration_ms': 1},
            sort=[('timestamp', -1)]
        )

    @staticmethod
    def q4_sqlite(db) -> List[Dict]:
        """Q4: Featured products in Electronics with high rating"""
        sql = """
            SELECT id, name, category, price, rating, review_count
            FROM products
            WHERE category = 'Electronics' AND is_featured = 1 AND rating > 4.0
            ORDER BY rating DESC, review_count DESC
            LIMIT 50
        """
        return db.execute_query(sql)

    @staticmethod
    def q4_mongo(db) -> List[Dict]:
        """Q4: Featured products in Electronics with high rating"""
        return db.execute_query(
            'products',
            {
                'category': 'Electronics',
                'is_featured': True,
                'rating': {'$gt': 4.0}
            },
            projection={'name': 1, 'category': 1, 'price': 1, 'rating': 1, 'review_count': 1},
            sort=[('rating', -1), ('review_count', -1)],
            limit=50
        )

    @staticmethod
    def q5_sqlite(db) -> List[Dict]:
        """Q5: User order statistics"""
        sql = """
            SELECT
                u.id,
                u.username,
                u.email,
                COUNT(o.id) as order_count,
                COALESCE(SUM(o.total_amount), 0) as total_spent,
                COALESCE(AVG(o.total_amount), 0) as avg_order_value
            FROM users u
            LEFT JOIN orders o ON u.id = o.user_id
            GROUP BY u.id, u.username, u.email
            HAVING order_count > 0
            ORDER BY total_spent DESC
            LIMIT 100
        """
        return db.execute_query(sql)

    @staticmethod
    def q5_mongo(db) -> List[Dict]:
        """Q5: User order statistics"""
        pipeline = [
            {
                '$lookup': {
                    'from': 'orders',
                    'localField': '_id',
                    'foreignField': 'user_id',
                    'as': 'orders'
                }
            },
            {
                '$addFields': {
                    'order_count': {'$size': '$orders'},
                    'total_spent': {'$sum': '$orders.total_amount'},
                    'avg_order_value': {'$avg': '$orders.total_amount'}
                }
            },
            {
                '$match': {
                    'order_count': {'$gt': 0}
                }
            },
            {
                '$project': {
                    'username': 1,
                    'email': 1,
                    'order_count': 1,
                    'total_spent': 1,
                    'avg_order_value': 1
                }
            },
            {'$sort': {'total_spent': -1}},
            {'$limit': 100}
        ]
        return db.execute_aggregation('users', pipeline)

    @staticmethod
    def q6_sqlite(db) -> List[Dict]:
        """Q6: Long sessions with high engagement"""
        sql = """
            SELECT id, user_id, start_time, duration_seconds, page_views
            FROM sessions
            WHERE duration_seconds > 1800 AND page_views > 10
            ORDER BY duration_seconds DESC
        """
        return db.execute_query(sql)

    @staticmethod
    def q6_mongo(db) -> List[Dict]:
        """Q6: Long sessions with high engagement"""
        return db.execute_query(
            'sessions',
            {
                'duration_seconds': {'$gt': 1800},
                'page_views': {'$gt': 10}
            },
            projection={'user_id': 1, 'start_time': 1, 'duration_seconds': 1, 'page_views': 1},
            sort=[('duration_seconds', -1)]
        )

    @staticmethod
    def q7_sqlite(db) -> List[Dict]:
        """Q7: Ticket statistics by status and priority"""
        sql = """
            SELECT
                status,
                priority,
                COUNT(*) as ticket_count,
                AVG(CASE
                    WHEN resolved_at IS NOT NULL
                    THEN (julianday(resolved_at) - julianday(created_at))
                    ELSE NULL
                END) as avg_resolution_days
            FROM tickets
            GROUP BY status, priority
            ORDER BY status, priority
        """
        return db.execute_query(sql)

    @staticmethod
    def q7_mongo(db) -> List[Dict]:
        """Q7: Ticket statistics by status and priority"""
        pipeline = [
            {
                '$group': {
                    '_id': {
                        'status': '$status',
                        'priority': '$priority'
                    },
                    'ticket_count': {'$sum': 1},
                    'avg_resolution_days': {
                        '$avg': {
                            '$cond': [
                                {'$ne': ['$resolved_at', None]},
                                {
                                    '$divide': [
                                        {'$subtract': ['$resolved_at', '$created_at']},
                                        86400000  # milliseconds in a day
                                    ]
                                },
                                None
                            ]
                        }
                    }
                }
            },
            {
                '$project': {
                    '_id': 0,
                    'status': '$_id.status',
                    'priority': '$_id.priority',
                    'ticket_count': 1,
                    'avg_resolution_days': 1
                }
            },
            {'$sort': {'status': 1, 'priority': 1}}
        ]
        return db.execute_aggregation('tickets', pipeline)

    @staticmethod
    def q8_sqlite(db) -> List[Dict]:
        """Q8: Error logs with exceptions"""
        sql = """
            SELECT id, timestamp, level, logger_name, message, exception, hostname
            FROM logs
            WHERE level IN ('ERROR', 'CRITICAL') AND exception IS NOT NULL
            ORDER BY timestamp DESC
            LIMIT 1000
        """
        return db.execute_query(sql)

    @staticmethod
    def q8_mongo(db) -> List[Dict]:
        """Q8: Error logs with exceptions"""
        return db.execute_query(
            'logs',
            {
                'level': {'$in': ['ERROR', 'CRITICAL']},
                'exception': {'$ne': None}
            },
            projection={'timestamp': 1, 'level': 1, 'logger_name': 1, 'message': 1, 'exception': 1, 'hostname': 1},
            sort=[('timestamp', -1)],
            limit=1000
        )

    @staticmethod
    def q9_sqlite(db) -> List[Dict]:
        """Q9: Payment statistics by method"""
        sql = """
            SELECT
                payment_method,
                status,
                COUNT(*) as transaction_count,
                SUM(amount) as total_amount,
                AVG(amount) as avg_amount,
                MIN(amount) as min_amount,
                MAX(amount) as max_amount
            FROM payments
            GROUP BY payment_method, status
            ORDER BY payment_method, status
        """
        return db.execute_query(sql)

    @staticmethod
    def q9_mongo(db) -> List[Dict]:
        """Q9: Payment statistics by method"""
        pipeline = [
            {
                '$group': {
                    '_id': {
                        'payment_method': '$payment_method',
                        'status': '$status'
                    },
                    'transaction_count': {'$sum': 1},
                    'total_amount': {'$sum': '$amount'},
                    'avg_amount': {'$avg': '$amount'},
                    'min_amount': {'$min': '$amount'},
                    'max_amount': {'$max': '$amount'}
                }
            },
            {
                '$project': {
                    '_id': 0,
                    'payment_method': '$_id.payment_method',
                    'status': '$_id.status',
                    'transaction_count': 1,
                    'total_amount': 1,
                    'avg_amount': 1,
                    'min_amount': 1,
                    'max_amount': 1
                }
            },
            {'$sort': {'payment_method': 1, 'status': 1}}
        ]
        return db.execute_aggregation('payments', pipeline)

    @staticmethod
    def q10_sqlite(db) -> List[Dict]:
        """Q10: Top products by order frequency"""
        sql = """
            SELECT
                p.id,
                p.name,
                p.category,
                p.price,
                COUNT(o.id) as order_count,
                SUM(o.total_amount) as total_revenue
            FROM products p
            INNER JOIN orders o ON json_extract(o.items, '$[0].product_id') = p.id
                OR json_extract(o.items, '$[1].product_id') = p.id
                OR json_extract(o.items, '$[2].product_id') = p.id
            WHERE o.status NOT IN ('cancelled')
            GROUP BY p.id, p.name, p.category, p.price
            ORDER BY order_count DESC
            LIMIT 20
        """
        return db.execute_query(sql)

    @staticmethod
    def q10_mongo(db) -> List[Dict]:
        """Q10: Top products by order frequency"""
        pipeline = [
            {'$match': {'status': {'$nin': ['cancelled']}}},
            {'$unwind': '$items'},
            {
                '$group': {
                    '_id': '$items.product_id',
                    'order_count': {'$sum': 1},
                    'total_revenue': {'$sum': '$items.total'}
                }
            },
            {
                '$lookup': {
                    'from': 'products',
                    'localField': '_id',
                    'foreignField': '_id',
                    'as': 'product'
                }
            },
            {'$unwind': '$product'},
            {
                '$project': {
                    'id': '$_id',
                    'name': '$product.name',
                    'category': '$product.category',
                    'price': '$product.price',
                    'order_count': 1,
                    'total_revenue': 1
                }
            },
            {'$sort': {'order_count': -1}},
            {'$limit': 20}
        ]
        return db.execute_aggregation('orders', pipeline)

    @staticmethod
    def q11_sqlite(db) -> List[Dict]:
        """Q11: User registration trends by month"""
        sql = """
            SELECT
                strftime('%Y-%m', registration_date) as month,
                COUNT(*) as user_count,
                SUM(CASE WHEN is_active = 1 THEN 1 ELSE 0 END) as active_count
            FROM users
            GROUP BY month
            ORDER BY month DESC
        """
        return db.execute_query(sql)

    @staticmethod
    def q11_mongo(db) -> List[Dict]:
        """Q11: User registration trends by month"""
        pipeline = [
            {
                '$group': {
                    '_id': {
                        '$dateToString': {
                            'format': '%Y-%m',
                            'date': '$registration_date'
                        }
                    },
                    'user_count': {'$sum': 1},
                    'active_count': {
                        '$sum': {
                            '$cond': ['$is_active', 1, 0]
                        }
                    }
                }
            },
            {
                '$project': {
                    '_id': 0,
                    'month': '$_id',
                    'user_count': 1,
                    'active_count': 1
                }
            },
            {'$sort': {'month': -1}}
        ]
        return db.execute_aggregation('users', pipeline)

    @staticmethod
    def q12_sqlite(db) -> List[Dict]:
        """Q12: Multi-table join - users with orders and payments"""
        sql = """
            SELECT
                u.id as user_id,
                u.username,
                u.email,
                o.id as order_id,
                o.order_date,
                o.total_amount as order_amount,
                p.id as payment_id,
                p.status as payment_status,
                p.payment_method
            FROM users u
            INNER JOIN orders o ON u.id = o.user_id
            INNER JOIN payments p ON o.id = p.order_id
            WHERE o.order_date > date('now', '-3 months')
                AND p.status = 'completed'
            ORDER BY o.order_date DESC
            LIMIT 500
        """
        return db.execute_query(sql)

    @staticmethod
    def q12_mongo(db) -> List[Dict]:
        """Q12: Multi-table join - users with orders and payments"""
        cutoff_date = datetime.now() - timedelta(days=90)
        pipeline = [
            {
                '$match': {
                    'order_date': {'$gt': cutoff_date}
                }
            },
            {
                '$lookup': {
                    'from': 'users',
                    'localField': 'user_id',
                    'foreignField': '_id',
                    'as': 'user'
                }
            },
            {'$unwind': '$user'},
            {
                '$lookup': {
                    'from': 'payments',
                    'localField': '_id',
                    'foreignField': 'order_id',
                    'as': 'payment'
                }
            },
            {'$unwind': '$payment'},
            {
                '$match': {
                    'payment.status': 'completed'
                }
            },
            {
                '$project': {
                    'user_id': '$user._id',
                    'username': '$user.username',
                    'email': '$user.email',
                    'order_id': '$_id',
                    'order_date': 1,
                    'order_amount': '$total_amount',
                    'payment_id': '$payment._id',
                    'payment_status': '$payment.status',
                    'payment_method': '$payment.payment_method'
                }
            },
            {'$sort': {'order_date': -1}},
            {'$limit': 500}
        ]
        return db.execute_aggregation('orders', pipeline)

    @staticmethod
    def q13_sqlite(db) -> List[Dict]:
        """Q13: Average order value by status for recent period"""
        cutoff_date = (datetime.now() - timedelta(days=180)).isoformat()
        sql = """
            SELECT
                status,
                COUNT(*) as order_count,
                AVG(total_amount) as avg_amount,
                SUM(total_amount) as total_amount,
                MIN(total_amount) as min_amount,
                MAX(total_amount) as max_amount
            FROM orders
            WHERE order_date > ?
            GROUP BY status
            ORDER BY avg_amount DESC
        """
        return db.execute_query(sql, (cutoff_date,))

    @staticmethod
    def q13_mongo(db) -> List[Dict]:
        """Q13: Average order value by status for recent period"""
        cutoff_date = datetime.now() - timedelta(days=180)
        pipeline = [
            {
                '$match': {
                    'order_date': {'$gt': cutoff_date}
                }
            },
            {
                '$group': {
                    '_id': '$status',
                    'order_count': {'$sum': 1},
                    'avg_amount': {'$avg': '$total_amount'},
                    'total_amount': {'$sum': '$total_amount'},
                    'min_amount': {'$min': '$total_amount'},
                    'max_amount': {'$max': '$total_amount'}
                }
            },
            {
                '$project': {
                    '_id': 0,
                    'status': '$_id',
                    'order_count': 1,
                    'avg_amount': 1,
                    'total_amount': 1,
                    'min_amount': 1,
                    'max_amount': 1
                }
            },
            {'$sort': {'avg_amount': -1}}
        ]
        return db.execute_aggregation('orders', pipeline)

    @staticmethod
    def q14_sqlite(db) -> List[Dict]:
        """Q14: Text search with price range"""
        sql = """
            SELECT id, name, category, price, rating, stock_quantity
            FROM products
            WHERE (name LIKE '%e%' OR name LIKE '%a%')
                AND price BETWEEN 50 AND 500
                AND stock_quantity > 0
            ORDER BY rating DESC
            LIMIT 200
        """
        return db.execute_query(sql)

    @staticmethod
    def q14_mongo(db) -> List[Dict]:
        """Q14: Text search with price range"""
        return db.execute_query(
            'products',
            {
                'name': {'$regex': '[ea]', '$options': 'i'},
                'price': {'$gte': 50, '$lte': 500},
                'stock_quantity': {'$gt': 0}
            },
            projection={'name': 1, 'category': 1, 'price': 1, 'rating': 1, 'stock_quantity': 1},
            sort=[('rating', -1)],
            limit=200
        )

    @staticmethod
    def q15_sqlite(db) -> List[Dict]:
        """Q15: Complex user activity summary"""
        sql = """
            SELECT
                u.id,
                u.username,
                u.email,
                u.country,
                COUNT(DISTINCT o.id) as order_count,
                COUNT(DISTINCT e.id) as event_count,
                COUNT(DISTINCT s.id) as session_count,
                COALESCE(SUM(o.total_amount), 0) as total_spent
            FROM users u
            LEFT JOIN orders o ON u.id = o.user_id AND o.order_date > date('now', '-1 year')
            LEFT JOIN events e ON u.id = e.user_id AND e.timestamp > datetime('now', '-1 year')
            LEFT JOIN sessions s ON u.id = s.user_id AND s.start_time > datetime('now', '-1 year')
            WHERE u.is_active = 1
            GROUP BY u.id, u.username, u.email, u.country
            HAVING order_count > 0 OR event_count > 0 OR session_count > 0
            ORDER BY total_spent DESC
            LIMIT 1000
        """
        return db.execute_query(sql)

    @staticmethod
    def q15_mongo(db) -> List[Dict]:
        """Q15: Complex user activity summary"""
        one_year_ago = datetime.now() - timedelta(days=365)
        pipeline = [
            {'$match': {'is_active': True}},
            {
                '$lookup': {
                    'from': 'orders',
                    'let': {'user_id': '$_id'},
                    'pipeline': [
                        {
                            '$match': {
                                '$expr': {
                                    '$and': [
                                        {'$eq': ['$user_id', '$$user_id']},
                                        {'$gt': ['$order_date', one_year_ago]}
                                    ]
                                }
                            }
                        }
                    ],
                    'as': 'orders'
                }
            },
            {
                '$lookup': {
                    'from': 'events',
                    'let': {'user_id': '$_id'},
                    'pipeline': [
                        {
                            '$match': {
                                '$expr': {
                                    '$and': [
                                        {'$eq': ['$user_id', '$$user_id']},
                                        {'$gt': ['$timestamp', one_year_ago]}
                                    ]
                                }
                            }
                        }
                    ],
                    'as': 'events'
                }
            },
            {
                '$lookup': {
                    'from': 'sessions',
                    'let': {'user_id': '$_id'},
                    'pipeline': [
                        {
                            '$match': {
                                '$expr': {
                                    '$and': [
                                        {'$eq': ['$user_id', '$$user_id']},
                                        {'$gt': ['$start_time', one_year_ago]}
                                    ]
                                }
                            }
                        }
                    ],
                    'as': 'sessions'
                }
            },
            {
                '$addFields': {
                    'order_count': {'$size': '$orders'},
                    'event_count': {'$size': '$events'},
                    'session_count': {'$size': '$sessions'},
                    'total_spent': {'$sum': '$orders.total_amount'}
                }
            },
            {
                '$match': {
                    '$or': [
                        {'order_count': {'$gt': 0}},
                        {'event_count': {'$gt': 0}},
                        {'session_count': {'$gt': 0}}
                    ]
                }
            },
            {
                '$project': {
                    'username': 1,
                    'email': 1,
                    'country': 1,
                    'order_count': 1,
                    'event_count': 1,
                    'session_count': 1,
                    'total_spent': 1
                }
            },
            {'$sort': {'total_spent': -1}},
            {'$limit': 1000}
        ]
        return db.execute_aggregation('users', pipeline)
