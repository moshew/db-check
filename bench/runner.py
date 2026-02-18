"""
Benchmark runner with timing and statistical analysis.
Measures insert and query performance with detailed metrics.
"""

import time
import numpy as np
import pandas as pd
from typing import Dict, Any, List, Callable
from tqdm import tqdm
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
import json
import os
from datetime import datetime
from html import escape


class BenchmarkRunner:
    """Run benchmarks and collect performance metrics."""

    def __init__(self, output_dir: str = "results"):
        """
        Initialize benchmark runner.

        Args:
            output_dir: Directory to store results
        """
        self.output_dir = output_dir
        self.console = Console()
        self.results = {
            'inserts': {},
            'queries': {}
        }

        # Ensure output directory exists
        os.makedirs(output_dir, exist_ok=True)

    def measure_insert_performance(self, db_name: str, db_instance: Any,
                                   data: Dict[str, List[Dict[str, Any]]],
                                   batch_size: int) -> Dict[str, Any]:
        """
        Measure insert performance for all entity types.

        Args:
            db_name: Name of the database (sqlite/mongo)
            db_instance: Database instance
            data: Dictionary of entity data
            batch_size: Batch size for inserts

        Returns:
            Dictionary with insert metrics
        """
        self.console.print(f"\n[bold cyan]Measuring {db_name.upper()} Insert Performance[/bold cyan]")

        insert_results = {}

        for entity_type, records in data.items():
            if not records:
                continue

            self.console.print(f"  Inserting {len(records):,} {entity_type}...", end=" ")

            # Measure insert time
            start_time = time.perf_counter()

            # Use appropriate insert method
            if db_name == 'sqlite':
                db_instance.bulk_insert(entity_type, records, batch_size)
            else:  # mongo
                db_instance.bulk_insert(entity_type, records, batch_size)

            end_time = time.perf_counter()
            duration = end_time - start_time

            throughput = len(records) / duration if duration > 0 else 0

            insert_results[entity_type] = {
                'count': len(records),
                'duration_seconds': duration,
                'throughput_per_second': throughput,
                'batch_size': batch_size
            }

            self.console.print(f"[green]✓[/green] {duration:.2f}s ({throughput:,.0f} records/sec)")

        return insert_results

    def measure_query_performance(self, db_name: str, db_instance: Any,
                                  queries: List[Dict[str, Any]],
                                  iterations: int = 5,
                                  warmup: int = 1) -> Dict[str, Any]:
        """
        Measure query performance with multiple iterations.

        Args:
            db_name: Name of the database (sqlite/mongo)
            db_instance: Database instance
            queries: List of query definitions
            iterations: Number of iterations per query
            warmup: Number of warmup iterations

        Returns:
            Dictionary with query metrics
        """
        self.console.print(f"\n[bold cyan]Measuring {db_name.upper()} Query Performance[/bold cyan]")
        self.console.print(f"  Warmup iterations: {warmup}, Measurement iterations: {iterations}\n")

        query_results = {}

        # Use tqdm for progress
        for query_def in tqdm(queries, desc=f"Running {db_name} queries"):
            query_id = query_def['id']
            query_name = query_def['name']

            # Get the appropriate query function
            query_func = query_def[db_name]

            # Warmup runs
            for _ in range(warmup):
                try:
                    _ = query_func(db_instance)
                except Exception as e:
                    self.console.print(f"[yellow]Warning: {query_id} warmup failed: {e}[/yellow]")

            # Measurement runs
            timings = []
            result_counts = []
            errors = []

            for _ in range(iterations):
                try:
                    start_time = time.perf_counter()
                    results = query_func(db_instance)
                    end_time = time.perf_counter()

                    duration_ms = (end_time - start_time) * 1000
                    timings.append(duration_ms)
                    result_counts.append(len(results))

                except Exception as e:
                    errors.append(str(e))

            # Calculate statistics
            if timings:
                stats = {
                    'query_id': query_id,
                    'query_name': query_name,
                    'description': query_def['description'],
                    'iterations': len(timings),
                    'errors': len(errors),
                    'avg_result_count': int(np.mean(result_counts)) if result_counts else 0,
                    'mean_ms': float(np.mean(timings)),
                    'median_ms': float(np.median(timings)),
                    'p50_ms': float(np.percentile(timings, 50)),
                    'p95_ms': float(np.percentile(timings, 95)),
                    'p99_ms': float(np.percentile(timings, 99)),
                    'min_ms': float(np.min(timings)),
                    'max_ms': float(np.max(timings)),
                    'stddev_ms': float(np.std(timings)),
                    'error_messages': errors[:3] if errors else []  # Keep first 3 errors
                }
            else:
                stats = {
                    'query_id': query_id,
                    'query_name': query_name,
                    'description': query_def['description'],
                    'iterations': 0,
                    'errors': len(errors),
                    'error_messages': errors[:3]
                }

            query_results[query_id] = stats

        return query_results

    def compare_databases(self, sqlite_results: Dict[str, Any],
                         mongo_results: Dict[str, Any]) -> pd.DataFrame:
        """
        Compare query performance between databases.

        Args:
            sqlite_results: SQLite query results
            mongo_results: MongoDB query results

        Returns:
            DataFrame with comparison
        """
        comparison_data = []

        for query_id in sqlite_results.keys():
            sqlite_stats = sqlite_results[query_id]
            mongo_stats = mongo_results.get(query_id, {})

            sqlite_mean = sqlite_stats.get('mean_ms', 0)
            mongo_mean = mongo_stats.get('mean_ms', 0)

            if sqlite_mean > 0 and mongo_mean > 0:
                speedup = sqlite_mean / mongo_mean
                faster = 'MongoDB' if speedup > 1 else 'SQLite'
                speedup_pct = abs(speedup - 1) * 100
            else:
                speedup = 0
                faster = 'N/A'
                speedup_pct = 0

            comparison_data.append({
                'Query ID': query_id,
                'Query Name': sqlite_stats.get('query_name', ''),
                'SQLite Mean (ms)': sqlite_mean,
                'MongoDB Mean (ms)': mongo_mean,
                'SQLite P95 (ms)': sqlite_stats.get('p95_ms', 0),
                'MongoDB P95 (ms)': mongo_stats.get('p95_ms', 0),
                'Speedup': speedup,
                'Faster': faster,
                'Speedup %': speedup_pct
            })

        return pd.DataFrame(comparison_data)

    def save_results(self, results: Dict[str, Any], filename: str) -> str:
        """
        Save results to JSON and CSV files.

        Args:
            results: Results dictionary
            filename: Base filename (without extension)

        Returns:
            Base path without extension, including timestamp suffix
        """
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        # Support both bare names ("benchmark") and explicit paths ("results/benchmark")
        if os.path.dirname(filename):
            base_prefix = filename
        else:
            base_prefix = os.path.join(self.output_dir, filename)

        base_path = f"{base_prefix}_{timestamp}"
        os.makedirs(os.path.dirname(base_path) or ".", exist_ok=True)

        # Save JSON
        json_path = f"{base_path}.json"
        with open(json_path, 'w') as f:
            json.dump(results, f, indent=2, default=str)

        self.console.print(f"[green]Results saved to {json_path}[/green]")

        # Save query results to CSV if available
        if 'queries' in results and results['queries']:
            for db_name, query_results in results['queries'].items():
                if query_results:
                    df = pd.DataFrame(list(query_results.values()))
                    csv_path = f"{base_path}_{db_name}_queries.csv"
                    df.to_csv(csv_path, index=False)
                    self.console.print(f"[green]Query results saved to {csv_path}[/green]")

        return base_path

    def export_reports(self, results: Dict[str, Any], base_path: str, formats: List[str]):
        """
        Export human-readable benchmark reports.

        Args:
            results: Benchmark results dictionary
            base_path: Base output path returned by save_results
            formats: List of formats to export (md/html/pdf)
        """
        requested = {fmt.lower().strip() for fmt in formats if fmt and fmt.strip()}
        valid_formats = {"md", "html", "pdf"}
        invalid_formats = sorted(requested - valid_formats)
        if invalid_formats:
            self.console.print(f"[yellow]Skipping unknown report formats: {', '.join(invalid_formats)}[/yellow]")
        selected = sorted(requested & valid_formats)
        if not selected:
            return

        md_text = self._build_markdown_report(results)

        if "md" in selected:
            md_path = f"{base_path}.md"
            with open(md_path, "w", encoding="utf-8") as f:
                f.write(md_text)
            self.console.print(f"[green]Report saved to {md_path}[/green]")

        if "html" in selected:
            html_path = f"{base_path}.html"
            html_text = self._build_html_report(results)
            with open(html_path, "w", encoding="utf-8") as f:
                f.write(html_text)
            self.console.print(f"[green]Report saved to {html_path}[/green]")

        if "pdf" in selected:
            pdf_path = f"{base_path}.pdf"
            self._build_pdf_report(md_text, pdf_path)

    def _build_markdown_report(self, results: Dict[str, Any]) -> str:
        """Build a Markdown report from benchmark results."""
        lines = ["# Benchmark Report", ""]

        config = results.get("config", {})
        lines.extend(["## Configuration", ""])
        for key, value in config.items():
            lines.append(f"- `{key}`: `{value}`")
        lines.append("")

        metadata = results.get("metadata", {})
        entities = metadata.get("entities", {})
        if entities:
            lines.extend(["## Entity Schema", ""])
            for entity_name, entity_meta in entities.items():
                fields = entity_meta.get("fields", {})
                if not fields:
                    continue
                rows = [{"Field": field, "Type": field_type} for field, field_type in fields.items()]
                df = pd.DataFrame(rows)
                lines.append(f"### {entity_name}")
                lines.append("")
                lines.append(df.to_markdown(index=False))
                lines.append("")

        query_complexity = metadata.get("query_complexity", {})
        if query_complexity:
            lines.extend(["## Query Complexity", ""])
            complexity_rows = []
            for query_id, meta in sorted(query_complexity.items()):
                complexity_rows.append({
                    "ID": query_id,
                    "Level": meta.get("level", ""),
                    "Why": meta.get("why", ""),
                    "Features": ", ".join(meta.get("features", []))
                })
            if complexity_rows:
                df = pd.DataFrame(complexity_rows)
                lines.append(df.to_markdown(index=False))
                lines.append("")
                very_high_count = sum(1 for row in complexity_rows if row["Level"] == "very_high")
                lines.append(f"- Very high complexity queries: **{very_high_count}**")
                lines.append("")

        inserts = results.get("inserts", {})
        if inserts:
            lines.extend(["## Insert Performance", ""])
            for db_name, entity_results in inserts.items():
                rows = []
                total_count = 0
                total_duration = 0.0
                for entity, stats in entity_results.items():
                    count = int(stats.get("count", 0))
                    duration = float(stats.get("duration_seconds", 0))
                    throughput = float(stats.get("throughput_per_second", 0))
                    rows.append([entity, f"{count:,}", f"{duration:.3f}", f"{throughput:,.0f}"])
                    total_count += count
                    total_duration += duration
                avg_tp = total_count / total_duration if total_duration > 0 else 0.0
                rows.append(["TOTAL", f"{total_count:,}", f"{total_duration:.3f}", f"{avg_tp:,.0f}"])
                df = pd.DataFrame(rows, columns=["Entity", "Records", "Duration (s)", "Throughput (rec/s)"])
                lines.append(f"### {db_name.upper()}")
                lines.append("")
                lines.append(df.to_markdown(index=False))
                lines.append("")

        queries = results.get("queries", {})
        if queries:
            lines.extend(["## Query Performance", ""])
            for db_name, query_results in queries.items():
                if not query_results:
                    continue
                rows = []
                for query_id, stats in query_results.items():
                    rows.append({
                        "ID": query_id,
                        "Query": stats.get("query_name", ""),
                        "Results": stats.get("avg_result_count", 0),
                        "Mean (ms)": round(float(stats.get("mean_ms", 0)), 3),
                        "P95 (ms)": round(float(stats.get("p95_ms", 0)), 3),
                        "P99 (ms)": round(float(stats.get("p99_ms", 0)), 3),
                        "Errors": int(stats.get("errors", 0))
                    })
                df = pd.DataFrame(rows)
                lines.append(f"### {db_name.upper()}")
                lines.append("")
                lines.append(df.to_markdown(index=False))
                lines.append("")

        sqlite_queries = queries.get("sqlite")
        mongo_queries = queries.get("mongo")
        if sqlite_queries and mongo_queries:
            cmp_df = self.compare_databases(sqlite_queries, mongo_queries)
            lines.extend(["## SQLite vs MongoDB Comparison", "", cmp_df.to_markdown(index=False), ""])

        return "\n".join(lines)

    def _build_html_report(self, results: Dict[str, Any]) -> str:
        """Build a lightweight HTML report from benchmark results."""
        html_sections = [
            "<h1>Benchmark Report</h1>",
            "<h2>Configuration</h2>",
            "<table><thead><tr><th>Key</th><th>Value</th></tr></thead><tbody>"
        ]

        for key, value in results.get("config", {}).items():
            html_sections.append(f"<tr><td>{escape(str(key))}</td><td>{escape(str(value))}</td></tr>")
        html_sections.append("</tbody></table>")

        metadata = results.get("metadata", {})
        entities = metadata.get("entities", {})
        if entities:
            html_sections.append("<h2>Entity Schema</h2>")
            for entity_name, entity_meta in entities.items():
                fields = entity_meta.get("fields", {})
                if not fields:
                    continue
                rows = [{"Field": field, "Type": field_type} for field, field_type in fields.items()]
                df = pd.DataFrame(rows)
                html_sections.append(f"<h3>{escape(entity_name)}</h3>")
                html_sections.append(df.to_html(index=False, border=0))

        query_complexity = metadata.get("query_complexity", {})
        if query_complexity:
            complexity_rows = []
            for query_id, meta in sorted(query_complexity.items()):
                complexity_rows.append({
                    "ID": query_id,
                    "Level": meta.get("level", ""),
                    "Why": meta.get("why", ""),
                    "Features": ", ".join(meta.get("features", []))
                })
            if complexity_rows:
                html_sections.append("<h2>Query Complexity</h2>")
                df = pd.DataFrame(complexity_rows)
                html_sections.append(df.to_html(index=False, border=0))
                very_high_count = sum(1 for row in complexity_rows if row["Level"] == "very_high")
                html_sections.append(f"<p><strong>Very high complexity queries:</strong> {very_high_count}</p>")

        inserts = results.get("inserts", {})
        if inserts:
            html_sections.append("<h2>Insert Performance</h2>")
            for db_name, entity_results in inserts.items():
                rows = []
                total_count = 0
                total_duration = 0.0
                for entity, stats in entity_results.items():
                    count = int(stats.get("count", 0))
                    duration = float(stats.get("duration_seconds", 0))
                    throughput = float(stats.get("throughput_per_second", 0))
                    rows.append({
                        "Entity": entity,
                        "Records": f"{count:,}",
                        "Duration (s)": f"{duration:.3f}",
                        "Throughput (rec/s)": f"{throughput:,.0f}"
                    })
                    total_count += count
                    total_duration += duration
                avg_tp = total_count / total_duration if total_duration > 0 else 0.0
                rows.append({
                    "Entity": "TOTAL",
                    "Records": f"{total_count:,}",
                    "Duration (s)": f"{total_duration:.3f}",
                    "Throughput (rec/s)": f"{avg_tp:,.0f}"
                })
                df = pd.DataFrame(rows)
                html_sections.append(f"<h3>{escape(db_name.upper())}</h3>")
                html_sections.append(df.to_html(index=False, border=0))

        queries = results.get("queries", {})
        if queries:
            html_sections.append("<h2>Query Performance</h2>")
            for db_name, query_results in queries.items():
                if not query_results:
                    continue
                rows = []
                for query_id, stats in query_results.items():
                    rows.append({
                        "ID": query_id,
                        "Query": stats.get("query_name", ""),
                        "Results": stats.get("avg_result_count", 0),
                        "Mean (ms)": round(float(stats.get("mean_ms", 0)), 3),
                        "P95 (ms)": round(float(stats.get("p95_ms", 0)), 3),
                        "P99 (ms)": round(float(stats.get("p99_ms", 0)), 3),
                        "Errors": int(stats.get("errors", 0))
                    })
                df = pd.DataFrame(rows)
                html_sections.append(f"<h3>{escape(db_name.upper())}</h3>")
                html_sections.append(df.to_html(index=False, border=0))

        sqlite_queries = queries.get("sqlite")
        mongo_queries = queries.get("mongo")
        if sqlite_queries and mongo_queries:
            html_sections.append("<h2>SQLite vs MongoDB Comparison</h2>")
            cmp_df = self.compare_databases(sqlite_queries, mongo_queries)
            html_sections.append(cmp_df.to_html(index=False, border=0))

        style = """
<style>
body { font-family: Arial, sans-serif; margin: 24px; line-height: 1.45; color: #1f2937; }
h1, h2, h3 { color: #0f172a; }
table { border-collapse: collapse; margin-bottom: 20px; width: 100%; }
th, td { border: 1px solid #d1d5db; padding: 8px; text-align: left; font-size: 14px; }
th { background: #f3f4f6; }
tr:nth-child(even) { background: #fafafa; }
pre { background: #f8fafc; border: 1px solid #e5e7eb; padding: 10px; white-space: pre-wrap; }
</style>
"""
        return f"<!doctype html><html><head><meta charset='utf-8'><title>Benchmark Report</title>{style}</head><body>{''.join(html_sections)}</body></html>"

    def _build_pdf_report(self, md_text: str, output_path: str):
        """
        Build a simple PDF report using matplotlib.
        Falls back gracefully if PDF backend is unavailable.
        """
        try:
            import matplotlib.pyplot as plt
            from matplotlib.backends.backend_pdf import PdfPages
            import textwrap

            lines = md_text.splitlines()
            pages = []
            current = []
            for line in lines:
                wrapped = textwrap.wrap(line, width=110) or [""]
                if len(current) + len(wrapped) > 50:
                    pages.append(current)
                    current = []
                current.extend(wrapped)
            if current:
                pages.append(current)

            with PdfPages(output_path) as pdf:
                for page_lines in pages:
                    fig = plt.figure(figsize=(8.27, 11.69))  # A4
                    fig.patch.set_facecolor("white")
                    text = "\n".join(page_lines)
                    fig.text(0.04, 0.98, text, va="top", ha="left", family="monospace", fontsize=8)
                    pdf.savefig(fig, bbox_inches="tight")
                    plt.close(fig)

            self.console.print(f"[green]Report saved to {output_path}[/green]")
        except Exception as e:
            self.console.print(f"[yellow]Could not create PDF report: {e}[/yellow]")

    def print_insert_summary(self, insert_results: Dict[str, Dict[str, Any]]):
        """
        Print insert performance summary.

        Args:
            insert_results: Insert results for all databases
        """
        self.console.print("\n[bold cyan]═══ Insert Performance Summary ═══[/bold cyan]\n")

        for db_name, entity_results in insert_results.items():
            table = Table(title=f"{db_name.upper()} Inserts", show_header=True, header_style="bold magenta")
            table.add_column("Entity Type", style="cyan")
            table.add_column("Records", justify="right", style="green")
            table.add_column("Duration (s)", justify="right")
            table.add_column("Throughput (rec/s)", justify="right", style="yellow")

            total_records = 0
            total_duration = 0

            for entity_type, stats in entity_results.items():
                table.add_row(
                    entity_type,
                    f"{stats['count']:,}",
                    f"{stats['duration_seconds']:.2f}",
                    f"{stats['throughput_per_second']:,.0f}"
                )
                total_records += stats['count']
                total_duration += stats['duration_seconds']

            avg_throughput = total_records / total_duration if total_duration > 0 else 0
            table.add_row(
                "[bold]TOTAL[/bold]",
                f"[bold]{total_records:,}[/bold]",
                f"[bold]{total_duration:.2f}[/bold]",
                f"[bold]{avg_throughput:,.0f}[/bold]"
            )

            self.console.print(table)
            self.console.print()

    def print_query_summary(self, query_results: Dict[str, Dict[str, Any]], db_name: str):
        """
        Print query performance summary.

        Args:
            query_results: Query results
            db_name: Database name
        """
        table = Table(title=f"{db_name.upper()} Query Performance", show_header=True, header_style="bold magenta")
        table.add_column("ID", style="cyan")
        table.add_column("Query Name", style="white")
        table.add_column("Results", justify="right", style="green")
        table.add_column("Mean (ms)", justify="right")
        table.add_column("P50 (ms)", justify="right")
        table.add_column("P95 (ms)", justify="right")
        table.add_column("P99 (ms)", justify="right")
        table.add_column("StdDev", justify="right", style="yellow")

        for query_id, stats in query_results.items():
            if stats.get('iterations', 0) > 0:
                table.add_row(
                    query_id,
                    stats.get('query_name', '')[:30],
                    f"{stats.get('avg_result_count', 0):,}",
                    f"{stats.get('mean_ms', 0):.2f}",
                    f"{stats.get('p50_ms', 0):.2f}",
                    f"{stats.get('p95_ms', 0):.2f}",
                    f"{stats.get('p99_ms', 0):.2f}",
                    f"{stats.get('stddev_ms', 0):.2f}"
                )
            else:
                table.add_row(
                    query_id,
                    stats.get('query_name', '')[:30],
                    "[red]ERROR[/red]",
                    "-",
                    "-",
                    "-",
                    "-",
                    "-"
                )

        self.console.print(table)
        self.console.print()

    def print_comparison_summary(self, comparison_df: pd.DataFrame):
        """
        Print comparison summary between databases.

        Args:
            comparison_df: Comparison DataFrame
        """
        self.console.print("\n[bold cyan]═══ Database Comparison ═══[/bold cyan]\n")

        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Query", style="cyan")
        table.add_column("SQLite (ms)", justify="right")
        table.add_column("MongoDB (ms)", justify="right")
        table.add_column("Faster", style="yellow")
        table.add_column("Speedup %", justify="right", style="green")

        for _, row in comparison_df.iterrows():
            faster_style = "green" if row['Faster'] != 'N/A' else "white"
            table.add_row(
                f"{row['Query ID']}: {row['Query Name'][:25]}",
                f"{row['SQLite Mean (ms)']:.2f}",
                f"{row['MongoDB Mean (ms)']:.2f}",
                f"[{faster_style}]{row['Faster']}[/{faster_style}]",
                f"{row['Speedup %']:.1f}%"
            )

        self.console.print(table)

        # Print summary statistics
        sqlite_wins = (comparison_df['Faster'] == 'SQLite').sum()
        mongo_wins = (comparison_df['Faster'] == 'MongoDB').sum()

        summary_text = f"""
[bold]Overall Summary:[/bold]
  • SQLite faster: {sqlite_wins} queries
  • MongoDB faster: {mongo_wins} queries
  • Average SQLite query time: {comparison_df['SQLite Mean (ms)'].mean():.2f} ms
  • Average MongoDB query time: {comparison_df['MongoDB Mean (ms)'].mean():.2f} ms
        """

        self.console.print(Panel(summary_text, title="Summary", border_style="green"))

    def create_performance_chart(self, comparison_df: pd.DataFrame, output_path: str):
        """
        Create performance comparison chart.

        Args:
            comparison_df: Comparison DataFrame
            output_path: Path to save the chart
        """
        try:
            import matplotlib.pyplot as plt

            fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))

            # Chart 1: Query time comparison
            queries = comparison_df['Query ID']
            x = np.arange(len(queries))
            width = 0.35

            ax1.bar(x - width/2, comparison_df['SQLite Mean (ms)'], width, label='SQLite', alpha=0.8)
            ax1.bar(x + width/2, comparison_df['MongoDB Mean (ms)'], width, label='MongoDB', alpha=0.8)

            ax1.set_xlabel('Query')
            ax1.set_ylabel('Mean Time (ms)')
            ax1.set_title('Query Performance Comparison')
            ax1.set_xticks(x)
            ax1.set_xticklabels(queries, rotation=45, ha='right')
            ax1.legend()
            ax1.grid(axis='y', alpha=0.3)

            # Chart 2: Speedup comparison
            speedup_data = []
            colors = []
            for _, row in comparison_df.iterrows():
                if row['Faster'] == 'SQLite':
                    speedup_data.append(row['Speedup %'])
                    colors.append('blue')
                elif row['Faster'] == 'MongoDB':
                    speedup_data.append(-row['Speedup %'])
                    colors.append('green')
                else:
                    speedup_data.append(0)
                    colors.append('gray')

            ax2.barh(queries, speedup_data, color=colors, alpha=0.7)
            ax2.set_xlabel('Speedup % (Negative = MongoDB faster)')
            ax2.set_ylabel('Query')
            ax2.set_title('Relative Performance (% faster)')
            ax2.axvline(x=0, color='black', linestyle='-', linewidth=0.5)
            ax2.grid(axis='x', alpha=0.3)

            plt.tight_layout()
            plt.savefig(output_path, dpi=150, bbox_inches='tight')
            plt.close()

            self.console.print(f"[green]Chart saved to {output_path}[/green]")

        except ImportError:
            self.console.print("[yellow]Matplotlib not available, skipping chart generation[/yellow]")
        except Exception as e:
            self.console.print(f"[yellow]Could not create chart: {e}[/yellow]")
