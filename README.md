# SQLite vs MongoDB Benchmark Suite

A comprehensive, production-ready benchmarking tool that compares SQLite and MongoDB performance across various workloads including bulk inserts, complex queries, aggregations, and joins.

## Features

- **8 Diverse Entity Types**: Users, Products, Orders, Events, Sessions, Tickets, Logs, Payments
- **Realistic Data Generation**: Uses Faker to generate 50k-200k+ records with relationships
- **15 Complex Queries**: Multi-filter, aggregations, joins, time ranges, text search, percentiles
- **Detailed Performance Metrics**: P50/P95/P99 latencies, throughput, standard deviation
- **Index Comparison**: Benchmark with and without indexes
- **Comprehensive Output**: JSON/CSV artifacts, visual HTML report, comparison chart
- **Resource Monitoring**: CPU/Memory monitoring for benchmark runner and MongoDB container
- **Query Complexity Metadata**: Per-query complexity levels (low/medium/high/very_high)
- **Reproducible**: Deterministic seeding for consistent benchmarks
- **Production-Ready**: Error handling, progress bars, rich CLI output

## Quick Start

### Prerequisites

- Python 3.11+
- Docker and Docker Compose (for MongoDB)

### Installation

1. **Install Python dependencies:**

```bash
python3 -m pip install -r requirements.txt
```

2. **Start MongoDB (via Docker):**

```bash
# For newer Docker Desktop (recommended)
docker compose up -d

# OR for older versions with standalone docker-compose
docker-compose up -d
```

This will start:
- MongoDB on port 27017
- Mongo Express (web UI) on port 8081

To verify MongoDB is running:
```bash
docker ps
```

**Note**: If neither command works, ensure Docker Desktop is installed and running. You can verify with `docker --version`.

### Run Your First Benchmark

```bash
# Run a quick benchmark with both databases (10k users)
python main.py --db both --records 10000 --with-indexes

# Run a larger benchmark (50k users)
python main.py --db both --records 50000 --with-indexes --iterations 10

# Run MongoDB only with 100k users
python main.py --db mongo --records 100000 --with-indexes

# Run and set custom base output path for generated HTML/artifacts
python main.py --db both --records 50000 --with-indexes --html results/run_01
```

## Usage

### Command Line Options

```
python main.py [OPTIONS]

Options:
  --db {sqlite,mongo,both}    Which database(s) to benchmark (default: both)
  --records N                 Number of user records (default: 10000)
  --seed N                    Random seed for reproducibility (default: 42)
  --batch-size N              Batch size for inserts (default: 1000)
  --iterations N              Number of query iterations (default: 5)
  --warmup N                  Number of warmup runs (default: 1)
  --with-indexes              Create indexes before queries
  --no-indexes                Explicitly disable indexes
  --html PATH                 Base output path for HTML report and result artifacts (default: results/benchmark)
  --reset                     Reset databases before running
  --skip-inserts              Skip insert benchmark
  --skip-queries              Skip query benchmark
```

### Example Commands

```bash
# Compare performance WITH indexes (recommended)
python main.py --db both --records 50000 --with-indexes

# Compare performance WITHOUT indexes
python main.py --db both --records 50000 --no-indexes

# Large-scale test with more iterations
python main.py --db both --records 200000 --iterations 10 --warmup 2 --with-indexes

# Test only inserts with different batch sizes
python main.py --db both --records 100000 --batch-size 5000 --skip-queries

# Test only queries (assumes data already loaded)
python main.py --db both --skip-inserts --with-indexes

# Reproducible tests with custom seed
python main.py --db both --records 50000 --seed 12345 --with-indexes
```

## Project Structure

```
db-check/
├── main.py                 # CLI entrypoint
├── requirements.txt        # Python dependencies
├── docker-compose.yml      # MongoDB setup
├── README.md              # This file
│
├── data/
│   └── generator.py       # Data generation with Faker
│
├── db/
│   ├── sqlite_impl.py     # SQLite implementation
│   └── mongo_impl.py      # MongoDB implementation
│
├── queries/
│   └── definitions.py     # Query workload definitions
│
├── bench/
│   └── runner.py          # Benchmark runner and metrics
│
└── results/               # Output directory
    ├── *.json            # Full benchmark + metadata
    ├── *.csv             # Per-DB query metrics
    ├── *.html            # Visual report (main output)
    └── *.png             # Comparison chart (embedded into HTML for --db both)
```

## Data Model

### Entity Types

The benchmark generates 8 different entity types with various field types and relationships:

#### 1. Users (Base Entity)
- **Fields**: id, username, email, full_name, age, country, city, registration_date, last_login, is_active
- **Complex Fields**: preferences (nested object), tags (array)
- **Scale**: N records (user-specified)

#### 2. Products
- **Fields**: id, name, description, category, price, cost, stock_quantity, rating, review_count, is_featured, created_at
- **Complex Fields**: specifications (nested with dimensions), tags (array)
- **Scale**: 0.5N records

#### 3. Orders
- **Fields**: id, user_id, order_date, status, total_amount, discount, tax, payment_method, notes
- **Complex Fields**: shipping_address (nested), items (array of objects)
- **Relationships**: Many-to-one with Users
- **Scale**: 2N records

#### 4. Events (Analytics)
- **Fields**: id, event_type, user_id, timestamp, session_id, page_url, duration_ms, ip_address, user_agent
- **Complex Fields**: metadata (nested)
- **Relationships**: Many-to-one with Users
- **Scale**: 10N records

#### 5. Sessions
- **Fields**: id, user_id, start_time, end_time, duration_seconds, page_views
- **Complex Fields**: actions (array), device_info (nested), location (nested)
- **Relationships**: Many-to-one with Users
- **Scale**: 1.5N records

#### 6. Tickets (Support)
- **Fields**: id, user_id, subject, description, priority, status, created_at, updated_at, resolved_at, assignee
- **Complex Fields**: comments (array of objects), tags (array)
- **Relationships**: Many-to-one with Users
- **Scale**: 0.3N records

#### 7. Logs
- **Fields**: id, timestamp, level, logger_name, message, hostname, process_id
- **Complex Fields**: exception (nested), context (nested)
- **Scale**: 20N records

#### 8. Payments
- **Fields**: id, order_id, user_id, amount, currency, payment_method, status, transaction_id, processed_at
- **Complex Fields**: card_details (nested), billing_address (nested), metadata (nested)
- **Relationships**: One-to-one with Orders, Many-to-one with Users
- **Scale**: 1.8N records

**Total Records** (for N=10,000): ~370,000 records

### Schema Design Choices

#### SQLite Schema

**Approach**: Normalized tables with JSON fields for complex data

**Rationale**:
- SQLite natively supports JSON operations via `json_extract()` and related functions
- JSON fields provide flexibility for nested objects and arrays
- Keeps schema simple while supporting complex data structures
- Foreign keys enforce relationships

**Trade-offs**:
- JSON querying is slower than native columns
- No indexes on JSON fields (without computed columns)
- Good for moderate complexity; full normalization would require many more tables

**Example**:
```sql
CREATE TABLE orders (
    id INTEGER PRIMARY KEY,
    user_id INTEGER,
    order_date TEXT,
    total_amount REAL,
    items TEXT,  -- JSON array: [{"product_id": 1, "quantity": 2, ...}]
    shipping_address TEXT,  -- JSON object
    FOREIGN KEY (user_id) REFERENCES users(id)
);
```

#### MongoDB Schema

**Approach**: Document-based with embedded documents and arrays

**Rationale**:
- Natural fit for MongoDB's document model
- Embedded documents reduce need for joins
- Arrays allow one-to-many relationships within documents
- Flexible schema for complex, nested data

**Trade-offs**:
- Larger document size due to embedded data
- Some data duplication (denormalization)
- Excellent for read-heavy workloads and complex nested queries
- Less efficient for many-to-many relationships (requires $lookup)

**Example**:
```javascript
{
    _id: 1,
    user_id: 42,
    order_date: ISODate("2024-01-15"),
    total_amount: 299.99,
    items: [
        {product_id: 101, quantity: 2, unit_price: 99.99, total: 199.98},
        {product_id: 205, quantity: 1, unit_price: 100.01, total: 100.01}
    ],
    shipping_address: {
        street: "123 Main St",
        city: "New York",
        state: "NY"
    }
}
```

#### Why This Matters for Benchmarking

1. **Realistic Comparison**: Both databases use their native strengths
2. **Complex Data**: Tests how each handles nested structures
3. **Query Variety**: Different query types favor different schemas
4. **Real-World Patterns**: Reflects actual application design decisions

## Query Workloads

The benchmark includes 15 diverse queries covering common patterns:

### Simple Filters
- **Q1**: Active users by country (indexed filter)
- **Q2**: High-value orders with status filter (range + IN clause)
- **Q3**: Recent events by type (time range filter)
- **Q4**: Multi-filter product search (category + boolean + range)

### Aggregations
- **Q7**: Ticket statistics grouped by status and priority
- **Q9**: Payment statistics by method (COUNT, SUM, AVG, MIN, MAX)
- **Q11**: User registration trends by month
- **Q13**: Average order value by status for time range

### Joins / Lookups
- **Q5**: User order statistics (JOIN in SQLite, $lookup in Mongo)
- **Q10**: Top products by order frequency (complex JOIN)
- **Q12**: Three-table join (users, orders, payments)
- **Q15**: Complex user activity summary (multiple JOINs/$lookups)

### Mixed Complexity
- **Q6**: Session duration with multiple filters
- **Q8**: Error logs with nested exception data
- **Q14**: Text pattern search with price range

### Result Set Sizes
- **Small**: <100 rows (aggregations, top-N)
- **Medium**: 100-10,000 rows (filtered queries)
- **Large**: >10,000 rows (broad filters, analytics)

## Performance Metrics

The benchmark collects comprehensive statistics:

### Insert Metrics
- Total records inserted
- Duration (seconds)
- Throughput (records/second)
- Per-entity-type breakdown

### Query Metrics
- Mean latency (ms)
- Median / P50 (ms)
- P95 latency (ms)
- P99 latency (ms)
- Min/Max latency (ms)
- Standard deviation
- Result count

### Monitoring Metrics
- Runner process CPU avg/peak (%)
- Runner process memory avg/peak (MB)
- MongoDB container CPU avg/peak (%) when `docker stats` is accessible
- MongoDB container memory avg/peak (MB) when `docker stats` is accessible

### Comparison
- Query-by-query comparison
- Speedup percentage
- Winner identification
- Overall statistics

## Output Files

Results are saved with timestamps in the `results/` directory:

```
results/
├── benchmark_20240115_143022.json               # Complete benchmark + metadata
├── benchmark_20240115_143022_sqlite_queries.csv # SQLite query metrics
├── benchmark_20240115_143022_mongo_queries.csv  # MongoDB query metrics
├── benchmark_20240115_143022.html               # Visual report (primary)
└── benchmark_comparison.png                      # Comparison chart (for --db both)
```

The HTML report includes:
- configuration summary
- entity schema section (field names + field types)
- query complexity section
- insert/query performance tables
- resource monitoring tables
- SQLite vs MongoDB comparison table (with complexity indicator)
- embedded comparison chart image (when available)

## Understanding Results

### Insert Performance

**Factors Affecting Performance**:
- **Batch Size**: Larger batches = higher throughput
- **Indexes**: Creating indexes during insert slows performance
- **Data Complexity**: Nested objects/arrays increase serialization time
- **Transaction Overhead**: SQLite benefits from batched transactions

**Typical Results**:
- SQLite: 20,000-50,000 records/sec (with transactions)
- MongoDB: 30,000-80,000 records/sec (bulk inserts)

### Query Performance

**Factors Affecting Performance**:
- **Indexes**: Massive impact on range/filter queries
- **Result Set Size**: Larger results = longer query times
- **Join Complexity**: SQLite JOINs vs MongoDB $lookup
- **Data Locality**: MongoDB embedded documents can be faster
- **Query Optimization**: Each DB optimizes differently

**Typical Results** (with indexes):
- Simple filters: 1-10ms
- Aggregations: 10-100ms
- Complex joins: 50-500ms

### When SQLite is Faster
- Simple indexed lookups
- Small result sets
- Sequential scans on small tables
- Local file access (no network overhead)

### When MongoDB is Faster
- Complex nested queries
- Aggregation pipelines
- Large result sets
- Embedded document access
- Parallel query execution

## Troubleshooting

### MongoDB Connection Failed

**Error**: `Failed to connect to MongoDB`

**Solution**:
```bash
# Check if MongoDB is running
docker ps

# Start MongoDB if not running (use the command that works for your system)
docker compose up -d         # Newer Docker Desktop
# OR
docker-compose up -d         # Older versions

# Check logs
docker compose logs mongodb  # Newer Docker Desktop
# OR
docker-compose logs mongodb  # Older versions
```

### Mongo Container Monitoring Permission Denied

**Error**: `permission denied while trying to connect to the Docker daemon socket...`

**Cause**: Current shell session does not have docker-group access.

**Solution**:
```bash
# one-time setup
sudo usermod -aG docker $USER

# refresh current shell group membership
newgrp docker

# verify
docker stats --no-stream --format '{{.CPUPerc}}|{{.MemUsage}}' benchmark_mongo
```

### Out of Memory

**Error**: System runs out of memory with large datasets

**Solution**:
- Reduce `--records` count
- Increase Docker memory limit (Docker Desktop settings)
- Use smaller `--batch-size`

### Slow Performance

**Issue**: Benchmarks taking too long

**Solution**:
- Reduce `--records` for initial testing
- Reduce `--iterations`
- Use `--skip-inserts` if data already loaded
- Test one database at a time: `--db sqlite` or `--db mongo`

## Advanced Usage

### Testing Index Impact

```bash
# Test WITHOUT indexes
python main.py --db both --records 50000 --no-indexes --html results/no_indexes

# Test WITH indexes
python main.py --db both --records 50000 --with-indexes --html results/with_indexes
```

### Testing Different Batch Sizes

```bash
# Small batches
python main.py --db both --records 50000 --batch-size 500 --with-indexes

# Large batches
python main.py --db both --records 50000 --batch-size 10000 --with-indexes
```

### High-Precision Benchmarking

```bash
# More iterations for stable results
python main.py --db both --records 100000 --iterations 20 --warmup 5 --with-indexes
```

## Design Philosophy

### Why These Choices?

1. **Real-World Relevance**: Entity types reflect common application domains
2. **Complexity Spectrum**: Mix of simple and complex queries
3. **Fair Comparison**: Each DB uses idiomatic patterns
4. **Reproducibility**: Seeded random generation
5. **Comprehensive Metrics**: Beyond simple averages
6. **Ease of Use**: Docker setup, clear CLI, rich output

### Limitations

- **Single Machine**: No distributed/cluster testing
- **Network**: MongoDB over localhost (minimal network impact)
- **Concurrency**: Single-threaded benchmark (no concurrent queries)
- **Data Size**: Limited by available memory

## License

This project is provided as-is for educational and benchmarking purposes.

## Acknowledgments

- **Faker**: Realistic data generation
- **Rich**: Beautiful terminal output
- **PyMongo**: MongoDB Python driver
- **Pandas/NumPy**: Statistical analysis
- **Matplotlib**: Visualization

---

**Happy Benchmarking! 🚀**
