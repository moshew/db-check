"""
Data generation module using Faker to create realistic test data.
Generates 8 different entity types with various field types and relationships.
"""

from faker import Faker
from datetime import datetime, timedelta
import random
from typing import List, Dict, Any


class DataGenerator:
    """Generate fake data for benchmarking databases."""

    def __init__(self, seed: int = 42):
        """
        Initialize the data generator with a deterministic seed.

        Args:
            seed: Random seed for reproducibility
        """
        self.fake = Faker()
        Faker.seed(seed)
        random.seed(seed)

        # Predefined data for realistic generation
        self.product_categories = [
            'Electronics', 'Clothing', 'Home & Garden', 'Sports', 'Books',
            'Toys', 'Automotive', 'Health', 'Beauty', 'Food', 'Pet Supplies'
        ]

        self.event_types = [
            'page_view', 'click', 'purchase', 'signup', 'login', 'logout',
            'search', 'add_to_cart', 'remove_from_cart', 'checkout'
        ]

        self.ticket_priorities = ['low', 'medium', 'high', 'critical']
        self.ticket_statuses = ['open', 'in_progress', 'waiting', 'resolved', 'closed']

        self.log_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']

        self.payment_methods = ['credit_card', 'debit_card', 'paypal', 'bank_transfer', 'cryptocurrency']
        self.payment_statuses = ['pending', 'completed', 'failed', 'refunded']

        self.order_statuses = ['pending', 'confirmed', 'processing', 'shipped', 'delivered', 'cancelled']

    def generate_users(self, count: int) -> List[Dict[str, Any]]:
        """
        Generate user entities with profile information.

        Fields: id, username, email, full_name, age, country, city,
                registration_date, last_login, is_active, preferences (nested),
                tags (array)
        """
        users = []
        start_date = datetime.now() - timedelta(days=730)  # 2 years ago

        for i in range(count):
            reg_date = self.fake.date_time_between(start_date=start_date, end_date='now')
            last_login = self.fake.date_time_between(start_date=reg_date, end_date='now')

            user = {
                'id': i + 1,
                'username': self.fake.user_name(),
                'email': self.fake.email(),
                'full_name': self.fake.name(),
                'age': random.randint(18, 80),
                'country': self.fake.country(),
                'city': self.fake.city(),
                'registration_date': reg_date,
                'last_login': last_login,
                'is_active': random.random() > 0.1,  # 90% active
                'preferences': {
                    'newsletter': random.random() > 0.5,
                    'notifications': random.random() > 0.3,
                    'theme': random.choice(['light', 'dark', 'auto']),
                    'language': random.choice(['en', 'es', 'fr', 'de', 'ja'])
                },
                'tags': random.sample(['premium', 'verified', 'early_adopter', 'influencer', 'developer', 'tester'],
                                     k=random.randint(0, 3))
            }
            users.append(user)

        return users

    def generate_products(self, count: int) -> List[Dict[str, Any]]:
        """
        Generate product entities.

        Fields: id, name, description, category, price, cost, stock_quantity,
                rating, review_count, is_featured, specifications (nested),
                tags (array), created_at
        """
        products = []

        for i in range(count):
            price = round(random.uniform(5.99, 999.99), 2)
            cost = round(price * random.uniform(0.3, 0.7), 2)

            product = {
                'id': i + 1,
                'name': self.fake.catch_phrase(),
                'description': self.fake.text(max_nb_chars=200),
                'category': random.choice(self.product_categories),
                'price': price,
                'cost': cost,
                'stock_quantity': random.randint(0, 1000),
                'rating': round(random.uniform(1.0, 5.0), 2),
                'review_count': random.randint(0, 5000),
                'is_featured': random.random() > 0.8,  # 20% featured
                'specifications': {
                    'weight': round(random.uniform(0.1, 50.0), 2),
                    'dimensions': {
                        'length': round(random.uniform(1, 100), 1),
                        'width': round(random.uniform(1, 100), 1),
                        'height': round(random.uniform(1, 100), 1)
                    },
                    'color': self.fake.color_name(),
                    'material': random.choice(['plastic', 'metal', 'wood', 'fabric', 'glass'])
                },
                'tags': random.sample(['new', 'sale', 'popular', 'limited', 'eco-friendly', 'handmade'],
                                     k=random.randint(0, 3)),
                'created_at': self.fake.date_time_between(start_date='-2y', end_date='now')
            }
            products.append(product)

        return products

    def generate_orders(self, count: int, user_count: int) -> List[Dict[str, Any]]:
        """
        Generate order entities with relationships to users.

        Fields: id, user_id, order_date, status, total_amount, discount,
                tax, shipping_address (nested), items (array of nested objects),
                payment_method, notes
        """
        orders = []

        for i in range(count):
            order_date = self.fake.date_time_between(start_date='-1y', end_date='now')

            # Generate 1-5 items per order
            num_items = random.randint(1, 5)
            items = []
            subtotal = 0

            for j in range(num_items):
                item_price = round(random.uniform(10.0, 200.0), 2)
                quantity = random.randint(1, 5)
                items.append({
                    'product_id': random.randint(1, min(10000, count)),
                    'quantity': quantity,
                    'unit_price': item_price,
                    'total': round(item_price * quantity, 2)
                })
                subtotal += item_price * quantity

            discount = round(subtotal * random.uniform(0, 0.2), 2) if random.random() > 0.7 else 0
            tax = round((subtotal - discount) * 0.08, 2)
            total = round(subtotal - discount + tax, 2)

            order = {
                'id': i + 1,
                'user_id': random.randint(1, user_count),
                'order_date': order_date,
                'status': random.choice(self.order_statuses),
                'total_amount': total,
                'discount': discount,
                'tax': tax,
                'shipping_address': {
                    'street': self.fake.street_address(),
                    'city': self.fake.city(),
                    'state': self.fake.state(),
                    'zip_code': self.fake.zipcode(),
                    'country': self.fake.country()
                },
                'items': items,
                'payment_method': random.choice(self.payment_methods),
                'notes': self.fake.sentence() if random.random() > 0.7 else None
            }
            orders.append(order)

        return orders

    def generate_events(self, count: int, user_count: int) -> List[Dict[str, Any]]:
        """
        Generate event entities (analytics/tracking events).

        Fields: id, event_type, user_id, timestamp, session_id, page_url,
                metadata (nested), duration_ms, ip_address, user_agent
        """
        events = []

        for i in range(count):
            event = {
                'id': i + 1,
                'event_type': random.choice(self.event_types),
                'user_id': random.randint(1, user_count) if random.random() > 0.1 else None,
                'timestamp': self.fake.date_time_between(start_date='-30d', end_date='now'),
                'session_id': self.fake.uuid4(),
                'page_url': self.fake.url(),
                'metadata': {
                    'browser': random.choice(['Chrome', 'Firefox', 'Safari', 'Edge']),
                    'os': random.choice(['Windows', 'macOS', 'Linux', 'iOS', 'Android']),
                    'screen_resolution': random.choice(['1920x1080', '1366x768', '1440x900', '2560x1440']),
                    'referrer': self.fake.url() if random.random() > 0.3 else None
                },
                'duration_ms': random.randint(100, 60000),
                'ip_address': self.fake.ipv4(),
                'user_agent': self.fake.user_agent()
            }
            events.append(event)

        return events

    def generate_sessions(self, count: int, user_count: int) -> List[Dict[str, Any]]:
        """
        Generate session entities.

        Fields: id, user_id, start_time, end_time, duration_seconds,
                page_views, actions (array), device_info (nested), location (nested)
        """
        sessions = []

        for i in range(count):
            start_time = self.fake.date_time_between(start_date='-60d', end_date='now')
            duration_seconds = random.randint(30, 7200)  # 30s to 2 hours
            end_time = start_time + timedelta(seconds=duration_seconds)

            num_actions = random.randint(1, 20)
            actions = [
                {
                    'action': random.choice(['click', 'scroll', 'hover', 'submit', 'navigate']),
                    'target': f"#{self.fake.word()}",
                    'timestamp': random.randint(0, duration_seconds)
                }
                for _ in range(num_actions)
            ]

            session = {
                'id': i + 1,
                'user_id': random.randint(1, user_count) if random.random() > 0.05 else None,
                'start_time': start_time,
                'end_time': end_time,
                'duration_seconds': duration_seconds,
                'page_views': random.randint(1, 50),
                'actions': actions,
                'device_info': {
                    'device_type': random.choice(['desktop', 'mobile', 'tablet']),
                    'browser': random.choice(['Chrome', 'Firefox', 'Safari', 'Edge']),
                    'browser_version': f"{random.randint(90, 120)}.0"
                },
                'location': {
                    'country': self.fake.country_code(),
                    'city': self.fake.city(),
                    'latitude': float(self.fake.latitude()),
                    'longitude': float(self.fake.longitude())
                }
            }
            sessions.append(session)

        return sessions

    def generate_tickets(self, count: int, user_count: int) -> List[Dict[str, Any]]:
        """
        Generate support ticket entities.

        Fields: id, user_id, subject, description, priority, status,
                created_at, updated_at, resolved_at, assignee, comments (array),
                tags (array)
        """
        tickets = []

        for i in range(count):
            created_at = self.fake.date_time_between(start_date='-180d', end_date='now')
            updated_at = self.fake.date_time_between(start_date=created_at, end_date='now')

            status = random.choice(self.ticket_statuses)
            resolved_at = self.fake.date_time_between(start_date=updated_at, end_date='now') \
                if status in ['resolved', 'closed'] else None

            num_comments = random.randint(0, 10)
            comments = [
                {
                    'author': self.fake.name(),
                    'text': self.fake.paragraph(),
                    'timestamp': self.fake.date_time_between(start_date=created_at, end_date=updated_at)
                }
                for _ in range(num_comments)
            ]

            ticket = {
                'id': i + 1,
                'user_id': random.randint(1, user_count),
                'subject': self.fake.sentence(),
                'description': self.fake.paragraph(nb_sentences=5),
                'priority': random.choice(self.ticket_priorities),
                'status': status,
                'created_at': created_at,
                'updated_at': updated_at,
                'resolved_at': resolved_at,
                'assignee': self.fake.name() if random.random() > 0.2 else None,
                'comments': comments,
                'tags': random.sample(['bug', 'feature', 'question', 'documentation', 'urgent', 'customer'],
                                     k=random.randint(1, 3))
            }
            tickets.append(ticket)

        return tickets

    def generate_logs(self, count: int) -> List[Dict[str, Any]]:
        """
        Generate log entry entities.

        Fields: id, timestamp, level, logger_name, message, exception (nested),
                context (nested), hostname, process_id
        """
        logs = []
        logger_names = ['auth', 'api', 'database', 'cache', 'worker', 'scheduler', 'email']

        for i in range(count):
            level = random.choice(self.log_levels)

            # Higher chance of exceptions for ERROR/CRITICAL
            has_exception = (level in ['ERROR', 'CRITICAL'] and random.random() > 0.5)

            exception_data = None
            if has_exception:
                exception_data = {
                    'type': random.choice(['ValueError', 'KeyError', 'TypeError', 'RuntimeError', 'IOError']),
                    'message': self.fake.sentence(),
                    'stack_trace': self.fake.text(max_nb_chars=300)
                }

            log = {
                'id': i + 1,
                'timestamp': self.fake.date_time_between(start_date='-7d', end_date='now'),
                'level': level,
                'logger_name': random.choice(logger_names),
                'message': self.fake.sentence(),
                'exception': exception_data,
                'context': {
                    'user_id': random.randint(1, 10000) if random.random() > 0.3 else None,
                    'request_id': self.fake.uuid4(),
                    'endpoint': f"/{self.fake.uri_path()}",
                    'duration_ms': random.randint(1, 5000)
                },
                'hostname': self.fake.hostname(),
                'process_id': random.randint(1000, 9999)
            }
            logs.append(log)

        return logs

    def generate_payments(self, count: int, user_count: int, order_count: int) -> List[Dict[str, Any]]:
        """
        Generate payment transaction entities.

        Fields: id, order_id, user_id, amount, currency, payment_method,
                status, transaction_id, processed_at, card_details (nested),
                billing_address (nested), metadata (nested)
        """
        payments = []
        currencies = ['USD', 'EUR', 'GBP', 'JPY', 'CAD', 'AUD']

        for i in range(count):
            payment_method = random.choice(self.payment_methods)

            card_details = None
            if payment_method in ['credit_card', 'debit_card']:
                card_details = {
                    'last_four': f"{random.randint(0, 9999):04d}",
                    'brand': random.choice(['Visa', 'Mastercard', 'Amex', 'Discover']),
                    'expiry_month': random.randint(1, 12),
                    'expiry_year': random.randint(2024, 2030)
                }

            payment = {
                'id': i + 1,
                'order_id': random.randint(1, order_count),
                'user_id': random.randint(1, user_count),
                'amount': round(random.uniform(5.0, 2000.0), 2),
                'currency': random.choice(currencies),
                'payment_method': payment_method,
                'status': random.choice(self.payment_statuses),
                'transaction_id': self.fake.uuid4(),
                'processed_at': self.fake.date_time_between(start_date='-1y', end_date='now'),
                'card_details': card_details,
                'billing_address': {
                    'street': self.fake.street_address(),
                    'city': self.fake.city(),
                    'state': self.fake.state(),
                    'zip_code': self.fake.zipcode(),
                    'country': self.fake.country_code()
                },
                'metadata': {
                    'ip_address': self.fake.ipv4(),
                    'user_agent': self.fake.user_agent(),
                    'fraud_score': round(random.uniform(0, 100), 2)
                }
            }
            payments.append(payment)

        return payments

    def generate_all(self, user_count: int, scale_factor: float = 1.0) -> Dict[str, List[Dict[str, Any]]]:
        """
        Generate all entity types with appropriate scaling.

        Args:
            user_count: Number of users to generate (base count)
            scale_factor: Multiplier for related entities

        Returns:
            Dictionary containing all generated entities
        """
        print(f"Generating data with {user_count} users (scale factor: {scale_factor})...")

        # Calculate counts for each entity type
        product_count = int(user_count * 0.5 * scale_factor)  # 0.5x users
        order_count = int(user_count * 2.0 * scale_factor)    # 2x users
        event_count = int(user_count * 10.0 * scale_factor)   # 10x users
        session_count = int(user_count * 1.5 * scale_factor)  # 1.5x users
        ticket_count = int(user_count * 0.3 * scale_factor)   # 0.3x users
        log_count = int(user_count * 20.0 * scale_factor)     # 20x users
        payment_count = int(user_count * 1.8 * scale_factor)  # 1.8x users

        return {
            'users': self.generate_users(user_count),
            'products': self.generate_products(product_count),
            'orders': self.generate_orders(order_count, user_count),
            'events': self.generate_events(event_count, user_count),
            'sessions': self.generate_sessions(session_count, user_count),
            'tickets': self.generate_tickets(ticket_count, user_count),
            'logs': self.generate_logs(log_count),
            'payments': self.generate_payments(payment_count, user_count, order_count)
        }
