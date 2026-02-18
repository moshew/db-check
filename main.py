#!/usr/bin/env python3
"""
SQLite vs MongoDB Benchmark Tool

Complete benchmarking suite comparing SQLite and MongoDB performance
across various workloads including inserts and complex queries.
"""

import argparse
import sys
from rich.console import Console
from rich.panel import Panel
from rich import print as rprint

from data.generator import DataGenerator
from db.sqlite_impl import SQLiteDB
from db.mongo_impl import MongoDB
from queries.definitions import QueryDefinitions
from bench.runner import BenchmarkRunner


console = Console()


def print_banner():
    """Print application banner."""
    banner = """
[bold cyan]╔══════════════════════════════════════════════╗
║   SQLite vs MongoDB Benchmark Suite         ║
║   Performance Testing & Analysis             ║
╚══════════════════════════════════════════════╝[/bold cyan]
    """
    console.print(banner)


def setup_sqlite(reset: bool = False) -> SQLiteDB:
    """
    Setup SQLite database.

    Args:
        reset: Whether to reset the database

    Returns:
        SQLiteDB instance
    """
    console.print("\n[bold]Setting up SQLite...[/bold]")
    db = SQLiteDB("benchmark.db")

    if reset:
        console.print("  Resetting database...")
        db.reset()
    else:
        db.connect()

    db.create_schema()
    console.print("  [green]✓[/green] SQLite ready")

    return db


def setup_mongodb(reset: bool = False) -> MongoDB:
    """
    Setup MongoDB database.

    Args:
        reset: Whether to reset the database

    Returns:
        MongoDB instance
    """
    console.print("\n[bold]Setting up MongoDB...[/bold]")

    try:
        db = MongoDB(
            connection_string="mongodb://admin:password123@localhost:27017/",
            database_name="benchmark"
        )
        db.connect()

        if reset:
            console.print("  Resetting database...")
            db.reset()

        db.create_schema()
        console.print("  [green]✓[/green] MongoDB ready")

        return db

    except Exception as e:
        console.print(f"  [red]✗[/red] Failed to connect to MongoDB: {e}")
        console.print("\n[yellow]Make sure MongoDB is running:[/yellow]")
        console.print("  docker-compose up -d")
        sys.exit(1)


def generate_data(record_count: int, seed: int) -> dict:
    """
    Generate test data.

    Args:
        record_count: Number of base records (users)
        seed: Random seed

    Returns:
        Dictionary of generated data
    """
    console.print(f"\n[bold]Generating test data (seed={seed})...[/bold]")

    generator = DataGenerator(seed=seed)

    # Calculate scale factor based on record count
    # Default 10k users = scale 1.0
    scale_factor = record_count / 10000

    data = generator.generate_all(user_count=record_count, scale_factor=scale_factor)

    # Print data summary
    console.print("\n[bold cyan]Generated Data Summary:[/bold cyan]")
    total_records = 0
    for entity_type, records in data.items():
        count = len(records)
        total_records += count
        console.print(f"  • {entity_type:12s}: {count:>8,} records")

    console.print(f"  [bold]Total: {total_records:,} records[/bold]")

    return data


def run_insert_benchmark(db_name: str, db_instance, data: dict, batch_size: int, runner: BenchmarkRunner):
    """
    Run insert benchmark for a database.

    Args:
        db_name: Database name
        db_instance: Database instance
        data: Generated data
        batch_size: Batch size for inserts
        runner: Benchmark runner
    """
    insert_results = runner.measure_insert_performance(
        db_name=db_name,
        db_instance=db_instance,
        data=data,
        batch_size=batch_size
    )

    return insert_results


def run_query_benchmark(db_name: str, db_instance, iterations: int, warmup: int, runner: BenchmarkRunner):
    """
    Run query benchmark for a database.

    Args:
        db_name: Database name
        db_instance: Database instance
        iterations: Number of iterations per query
        warmup: Number of warmup iterations
        runner: Benchmark runner
    """
    queries = QueryDefinitions.get_all_queries()

    query_results = runner.measure_query_performance(
        db_name=db_name,
        db_instance=db_instance,
        queries=queries,
        iterations=iterations,
        warmup=warmup
    )

    return query_results


def main():
    """Main application entry point."""
    parser = argparse.ArgumentParser(
        description='Benchmark SQLite vs MongoDB performance',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run both databases with default settings
  python main.py --db both --records 50000

  # Run only MongoDB with custom batch size
  python main.py --db mongo --records 100000 --batch-size 5000

  # Run with indexes and save results
  python main.py --db both --records 10000 --with-indexes --output results/benchmark

  # Run without indexes to compare
  python main.py --db both --records 10000 --no-indexes

  # Run with more iterations for accuracy
  python main.py --db both --records 20000 --iterations 10 --warmup 2
        """
    )

    parser.add_argument(
        '--db',
        choices=['sqlite', 'mongo', 'both'],
        default='both',
        help='Which database(s) to benchmark (default: both)'
    )

    parser.add_argument(
        '--records',
        type=int,
        default=10000,
        help='Number of user records to generate (default: 10000, other entities scale automatically)'
    )

    parser.add_argument(
        '--seed',
        type=int,
        default=42,
        help='Random seed for reproducibility (default: 42)'
    )

    parser.add_argument(
        '--batch-size',
        type=int,
        default=1000,
        help='Batch size for inserts (default: 1000)'
    )

    parser.add_argument(
        '--iterations',
        type=int,
        default=5,
        help='Number of iterations per query (default: 5)'
    )

    parser.add_argument(
        '--warmup',
        type=int,
        default=1,
        help='Number of warmup iterations (default: 1)'
    )

    parser.add_argument(
        '--with-indexes',
        action='store_true',
        help='Create indexes before running queries'
    )

    parser.add_argument(
        '--no-indexes',
        action='store_true',
        help='Explicitly run without indexes'
    )

    parser.add_argument(
        '--output',
        type=str,
        default='results/benchmark',
        help='Output path for results (default: results/benchmark)'
    )

    parser.add_argument(
        '--reset',
        action='store_true',
        help='Reset databases before running (drop all data)'
    )

    parser.add_argument(
        '--skip-inserts',
        action='store_true',
        help='Skip insert benchmark (assumes data already exists)'
    )

    parser.add_argument(
        '--skip-queries',
        action='store_true',
        help='Skip query benchmark (only do inserts)'
    )

    args = parser.parse_args()

    # Validate arguments
    if args.with_indexes and args.no_indexes:
        console.print("[red]Error: Cannot specify both --with-indexes and --no-indexes[/red]")
        sys.exit(1)

    # Determine index strategy (default is WITH indexes)
    use_indexes = not args.no_indexes

    # Print banner
    print_banner()

    # Print configuration
    config_text = f"""
[bold]Benchmark Configuration:[/bold]
  Database(s):     {args.db}
  User Records:    {args.records:,}
  Random Seed:     {args.seed}
  Batch Size:      {args.batch_size}
  Query Iterations: {args.iterations}
  Warmup Runs:     {args.warmup}
  Use Indexes:     {use_indexes}
  Reset DBs:       {args.reset}
    """
    console.print(Panel(config_text, title="Configuration", border_style="cyan"))

    # Initialize benchmark runner
    runner = BenchmarkRunner(output_dir="results")

    # Results storage
    all_results = {
        'config': vars(args),
        'inserts': {},
        'queries': {}
    }

    # Generate data (only if not skipping inserts)
    data = None
    if not args.skip_inserts:
        data = generate_data(args.records, args.seed)

    # Setup and run benchmarks based on selection
    run_sqlite = args.db in ['sqlite', 'both']
    run_mongo = args.db in ['mongo', 'both']

    sqlite_db = None
    mongo_db = None

    try:
        # Setup SQLite
        if run_sqlite:
            sqlite_db = setup_sqlite(reset=args.reset)

        # Setup MongoDB
        if run_mongo:
            mongo_db = setup_mongodb(reset=args.reset)

        # Run insert benchmarks
        if not args.skip_inserts:
            console.print("\n[bold yellow]═══ PHASE 1: INSERT BENCHMARKS ═══[/bold yellow]")

            if run_sqlite:
                all_results['inserts']['sqlite'] = run_insert_benchmark(
                    'sqlite', sqlite_db, data, args.batch_size, runner
                )

            if run_mongo:
                all_results['inserts']['mongo'] = run_insert_benchmark(
                    'mongo', mongo_db, data, args.batch_size, runner
                )

            # Print insert summary
            runner.print_insert_summary(all_results['inserts'])

        # Create indexes if requested
        if use_indexes and not args.skip_queries:
            console.print("\n[bold]Creating indexes...[/bold]")

            if run_sqlite:
                sqlite_db.create_indexes()
                console.print("  [green]✓[/green] SQLite indexes created")

            if run_mongo:
                mongo_db.create_indexes()
                console.print("  [green]✓[/green] MongoDB indexes created")

        # Run query benchmarks
        if not args.skip_queries:
            console.print("\n[bold yellow]═══ PHASE 2: QUERY BENCHMARKS ═══[/bold yellow]")

            if run_sqlite:
                all_results['queries']['sqlite'] = run_query_benchmark(
                    'sqlite', sqlite_db, args.iterations, args.warmup, runner
                )
                runner.print_query_summary(all_results['queries']['sqlite'], 'sqlite')

            if run_mongo:
                all_results['queries']['mongo'] = run_query_benchmark(
                    'mongo', mongo_db, args.iterations, args.warmup, runner
                )
                runner.print_query_summary(all_results['queries']['mongo'], 'mongo')

            # Comparison (if both databases were run)
            if run_sqlite and run_mongo:
                comparison_df = runner.compare_databases(
                    all_results['queries']['sqlite'],
                    all_results['queries']['mongo']
                )
                runner.print_comparison_summary(comparison_df)

                # Create chart
                chart_path = f"{args.output}_comparison.png"
                runner.create_performance_chart(comparison_df, chart_path)

        # Save results
        console.print("\n[bold]Saving results...[/bold]")
        runner.save_results(all_results, args.output)

        # Print database sizes
        console.print("\n[bold cyan]Database Sizes:[/bold cyan]")
        if run_sqlite:
            sqlite_size = sqlite_db.get_database_size()
            console.print(f"  SQLite:  {sqlite_size / (1024*1024):.2f} MB")

        if run_mongo:
            mongo_size = mongo_db.get_database_size()
            console.print(f"  MongoDB: {mongo_size / (1024*1024):.2f} MB")

        console.print("\n[bold green]✓ Benchmark complete![/bold green]\n")

    except KeyboardInterrupt:
        console.print("\n[yellow]Benchmark interrupted by user[/yellow]")
        sys.exit(1)

    except Exception as e:
        console.print(f"\n[red]Error during benchmark: {e}[/red]")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    finally:
        # Cleanup connections
        if sqlite_db:
            sqlite_db.disconnect()

        if mongo_db:
            mongo_db.disconnect()


if __name__ == '__main__':
    main()
