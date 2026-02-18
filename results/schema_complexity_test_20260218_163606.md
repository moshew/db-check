# Benchmark Report

## Configuration

- `db`: `sqlite`
- `records`: `200`
- `seed`: `42`
- `batch_size`: `100`
- `iterations`: `1`
- `warmup`: `0`
- `with_indexes`: `True`
- `no_indexes`: `False`
- `output`: `results/schema_complexity_test`
- `report_formats`: `md,html`
- `reset`: `True`
- `skip_inserts`: `False`
- `skip_queries`: `False`

## Entity Schema

### users

| Field             | Type       |
|:------------------|:-----------|
| id                | int        |
| username          | str        |
| email             | str        |
| full_name         | str        |
| age               | int        |
| country           | str        |
| city              | str        |
| registration_date | datetime   |
| last_login        | datetime   |
| is_active         | bool       |
| preferences       | object     |
| tags              | array<str> |

### products

| Field          | Type       |
|:---------------|:-----------|
| id             | int        |
| name           | str        |
| description    | str        |
| category       | str        |
| price          | float      |
| cost           | float      |
| stock_quantity | int        |
| rating         | float      |
| review_count   | int        |
| is_featured    | bool       |
| specifications | object     |
| tags           | array<str> |
| created_at     | datetime   |

### orders

| Field            | Type          |
|:-----------------|:--------------|
| id               | int           |
| user_id          | int           |
| order_date       | datetime      |
| status           | str           |
| total_amount     | float         |
| discount         | float         |
| tax              | float         |
| shipping_address | object        |
| items            | array<object> |
| payment_method   | str           |
| notes            | str|null      |

### events

| Field       | Type     |
|:------------|:---------|
| id          | int      |
| event_type  | str      |
| user_id     | int|null |
| timestamp   | datetime |
| session_id  | str      |
| page_url    | str      |
| metadata    | object   |
| duration_ms | int      |
| ip_address  | str      |
| user_agent  | str      |

### sessions

| Field            | Type          |
|:-----------------|:--------------|
| id               | int           |
| user_id          | int|null      |
| start_time       | datetime      |
| end_time         | datetime      |
| duration_seconds | int           |
| page_views       | int           |
| actions          | array<object> |
| device_info      | object        |
| location         | object        |

### tickets

| Field       | Type          |
|:------------|:--------------|
| id          | int           |
| user_id     | int           |
| subject     | str           |
| description | str           |
| priority    | str           |
| status      | str           |
| created_at  | datetime      |
| updated_at  | datetime      |
| resolved_at | datetime|null |
| assignee    | str|null      |
| comments    | array<object> |
| tags        | array<str>    |

### logs

| Field       | Type        |
|:------------|:------------|
| id          | int         |
| timestamp   | datetime    |
| level       | str         |
| logger_name | str         |
| message     | str         |
| exception   | object|null |
| context     | object      |
| hostname    | str         |
| process_id  | int         |

### payments

| Field           | Type     |
|:----------------|:---------|
| id              | int      |
| order_id        | int      |
| user_id         | int      |
| amount          | float    |
| currency        | str      |
| payment_method  | str      |
| status          | str      |
| transaction_id  | str      |
| processed_at    | datetime |
| card_details    | object   |
| billing_address | object   |
| metadata        | object   |

## Query Complexity

| ID   | Level     | Why                                                                                      | Features                                                                                                                |
|:-----|:----------|:-----------------------------------------------------------------------------------------|:------------------------------------------------------------------------------------------------------------------------|
| Q1   | low       | Simple selective filter + single sort                                                    | single collection/table filter, single sort key                                                                         |
| Q10  | very_high | Array expansion + join/lookup + aggregate + ranking                                      | array unnest/unwind, join/lookup, group aggregation, top-k ranking                                                      |
| Q11  | medium    | Time bucketing with grouped counts                                                       | date bucketing, group aggregation                                                                                       |
| Q12  | very_high | Multi-join query across users/orders/payments with filtering and projection              | multiple joins/lookups, time filter, status filter, sort + limit                                                        |
| Q13  | high      | Time-window aggregate statistics by status                                               | time-range predicate, group aggregation, multi-metric rollup                                                            |
| Q14  | high      | Text-pattern search + numeric range + ordering                                           | regex/LIKE pattern, numeric range, sort + limit                                                                         |
| Q15  | very_high | Correlated multi-source activity summary with three joins/lookups and derived aggregates | multiple correlated lookups, derived counters, multi-source aggregation, post-aggregation filtering, sort + large limit |
| Q2   | medium    | Range + IN filter with sorting                                                           | range predicate, set membership predicate, sort                                                                         |
| Q3   | medium    | Time-window filtering + sort                                                             | time-range predicate, single sort key                                                                                   |
| Q4   | medium    | Multiple predicates and compound ordering with limit                                     | multi-filter predicate, multi-column sort, top-k limit                                                                  |
| Q5   | high      | Join/lookup + aggregate metrics + HAVING-style filter                                    | join/lookup, group aggregation, derived metrics, post-aggregation filtering                                             |
| Q6   | low       | Simple two-threshold filter and sort                                                     | range predicates, single sort key                                                                                       |
| Q7   | high      | Conditional aggregation over grouped dimensions                                          | group by multiple dimensions, conditional aggregate                                                                     |
| Q8   | medium    | Selective logging filter with high result cap                                            | set membership predicate, null-check predicate, limit                                                                   |
| Q9   | high      | Multi-metric aggregation over grouped dimensions                                         | group aggregation, min/max/avg/sum metrics                                                                              |

- Very high complexity queries: **3**

## Insert Performance

### SQLITE

| Entity   |   Records |   Duration (s) | Throughput (rec/s)   |
|:---------|----------:|---------------:|:---------------------|
| users    |       200 |          0.006 | 35,480               |
| products |         2 |          0     | 7,183                |
| orders   |         8 |          0.001 | 5,758                |
| events   |        40 |          0.001 | 30,777               |
| sessions |         6 |          0.001 | 7,426                |
| tickets  |         1 |          0     | 3,189                |
| logs     |        80 |          0.002 | 44,281               |
| payments |         7 |          0.001 | 8,174                |
| TOTAL    |       344 |          0.012 | 27,766               |

## Query Performance

### SQLITE

| ID   | Query                                |   Results |   Mean (ms) |   P95 (ms) |   P99 (ms) |   Errors |
|:-----|:-------------------------------------|----------:|------------:|-----------:|-----------:|---------:|
| Q1   | Active Users by Country              |         0 |       0.263 |      0.263 |      0.263 |        0 |
| Q2   | High-Value Orders                    |         3 |       0.383 |      0.383 |      0.383 |        0 |
| Q3   | Recent Events by Type                |         1 |       0.18  |      0.18  |      0.18  |        0 |
| Q4   | Product Search with Multiple Filters |         0 |       0.13  |      0.13  |      0.13  |        0 |
| Q5   | User Order History with Join         |         8 |       0.514 |      0.514 |      0.514 |        0 |
| Q6   | Session Duration Analysis            |         6 |       0.121 |      0.121 |      0.121 |        0 |
| Q7   | Ticket Status Aggregation            |         1 |       0.2   |      0.2   |      0.2   |        0 |
| Q8   | Error Log Analysis                   |        12 |       0.448 |      0.448 |      0.448 |        0 |
| Q9   | Payment Method Statistics            |         6 |       0.199 |      0.199 |      0.199 |        0 |
| Q10  | Top Selling Products                 |         2 |       0.373 |      0.373 |      0.373 |        0 |
| Q11  | User Registration Trends             |        25 |       0.508 |      0.508 |      0.508 |        0 |
| Q12  | Complex Multi-Table Join             |         0 |       0.128 |      0.128 |      0.128 |        0 |
| Q13  | Time Range with Aggregation          |         3 |       0.192 |      0.192 |      0.192 |        0 |
| Q14  | Text Pattern Search                  |         2 |       0.151 |      0.151 |      0.151 |        0 |
| Q15  | User Activity Summary                |        43 |       1.685 |      1.685 |      1.685 |        0 |
