"""
Benchmark runner with timing and statistical analysis.
Measures insert and query performance with detailed metrics.
"""

import time
import numpy as np
import pandas as pd
from typing import Dict, Any, List, Callable, Optional
from tqdm import tqdm
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
import json
import os
from datetime import datetime
from html import escape
import threading
import subprocess
import re
import base64

try:
    import psutil
except ImportError:
    psutil = None


def _parse_cpu_percent(cpu_text: str) -> Optional[float]:
    match = re.search(r"([0-9]+(?:\.[0-9]+)?)", cpu_text or "")
    if not match:
        return None
    return float(match.group(1))


def _parse_size_to_mb(size_text: str) -> Optional[float]:
    match = re.search(r"([0-9]+(?:\.[0-9]+)?)\s*([KMGTP]?i?B)", size_text or "", re.IGNORECASE)
    if not match:
        return None
    value = float(match.group(1))
    unit = match.group(2).lower()
    factors = {
        "b": 1 / (1024 * 1024),
        "kib": 1 / 1024,
        "kb": 1 / 1024,
        "mib": 1.0,
        "mb": 1.0,
        "gib": 1024.0,
        "gb": 1024.0,
        "tib": 1024.0 * 1024.0,
        "tb": 1024.0 * 1024.0,
    }
    factor = factors.get(unit)
    if factor is None:
        return None
    return value * factor


def _normalize_docker_error(error_text: str) -> str:
    text = (error_text or "").lower()
    if "permission denied while trying to connect to the docker daemon socket" in text:
        return "no docker socket access (re-login or run newgrp docker)"
    if "a password is required" in text or "a terminal is required" in text:
        return "docker stats via sudo needs interactive password"
    if "command not found" in text:
        return "docker command not found"
    return (error_text or "docker_stats_failed").strip()


class _BaseMonitor:
    def __init__(self, sample_interval_s: float = 0.5):
        self.sample_interval_s = sample_interval_s
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._cpu_samples: List[float] = []
        self._mem_samples_mb: List[float] = []
        self._error: Optional[str] = None
        self._start_ts = 0.0

    def start(self):
        self._running = True
        self._start_ts = time.perf_counter()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self) -> Dict[str, Any]:
        self._running = False
        if self._thread:
            self._thread.join(timeout=2.0)

        duration = max(0.0, time.perf_counter() - self._start_ts)
        if self._error:
            return {"available": False, "reason": self._error}

        if not self._cpu_samples and not self._mem_samples_mb:
            return {"available": False, "reason": "no_samples_collected"}

        return {
            "available": True,
            "samples": max(len(self._cpu_samples), len(self._mem_samples_mb)),
            "duration_seconds": duration,
            "cpu_avg_percent": float(np.mean(self._cpu_samples)) if self._cpu_samples else None,
            "cpu_peak_percent": float(np.max(self._cpu_samples)) if self._cpu_samples else None,
            "memory_avg_mb": float(np.mean(self._mem_samples_mb)) if self._mem_samples_mb else None,
            "memory_peak_mb": float(np.max(self._mem_samples_mb)) if self._mem_samples_mb else None,
        }

    def _run(self):
        raise NotImplementedError


class _ProcessMonitor(_BaseMonitor):
    def __init__(self, sample_interval_s: float = 0.5):
        super().__init__(sample_interval_s=sample_interval_s)
        self._process = psutil.Process(os.getpid()) if psutil else None

    def _run(self):
        if self._process is None:
            self._error = "psutil_not_installed"
            return

        while self._running:
            try:
                cpu = self._process.cpu_percent(interval=self.sample_interval_s)
                mem_mb = self._process.memory_info().rss / (1024 * 1024)
                self._cpu_samples.append(cpu)
                self._mem_samples_mb.append(mem_mb)
            except Exception as exc:
                self._error = str(exc)
                self._running = False
                return


class _DockerContainerMonitor(_BaseMonitor):
    def __init__(self, container_name: str, sample_interval_s: float = 1.0):
        super().__init__(sample_interval_s=sample_interval_s)
        self.container_name = container_name

    def _run(self):
        base_cmd = [
            "docker", "stats", "--no-stream",
            "--format", "{{.CPUPerc}}|{{.MemUsage}}",
            self.container_name
        ]
        fallback_cmd = [
            "sudo", "-n", "docker", "stats", "--no-stream",
            "--format", "{{.CPUPerc}}|{{.MemUsage}}",
            self.container_name
        ]

        while self._running:
            try:
                proc = subprocess.run(base_cmd, capture_output=True, text=True, check=False)
                if proc.returncode != 0:
                    base_err = (proc.stderr.strip() or proc.stdout.strip() or "docker_stats_failed")
                    if "permission denied while trying to connect to the Docker daemon socket" in base_err:
                        sudo_proc = subprocess.run(fallback_cmd, capture_output=True, text=True, check=False)
                        if sudo_proc.returncode != 0:
                            sudo_err = sudo_proc.stderr.strip() or sudo_proc.stdout.strip() or "docker_stats_failed"
                            self._error = _normalize_docker_error(sudo_err)
                            self._running = False
                            return
                        proc = sudo_proc
                    else:
                        self._error = _normalize_docker_error(base_err)
                        self._running = False
                        return

                line = proc.stdout.strip().splitlines()
                if not line:
                    time.sleep(self.sample_interval_s)
                    continue

                cpu_text, _, mem_text = line[0].partition("|")
                cpu = _parse_cpu_percent(cpu_text)
                mem_used = _parse_size_to_mb((mem_text or "").split("/")[0].strip())
                if cpu is not None:
                    self._cpu_samples.append(cpu)
                if mem_used is not None:
                    self._mem_samples_mb.append(mem_used)
            except FileNotFoundError:
                self._error = "docker command not found"
                self._running = False
                return
            except Exception as exc:
                self._error = str(exc)
                self._running = False
                return
            time.sleep(self.sample_interval_s)


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

    def run_with_monitoring(self, db_name: str, phase_name: str, workload: Callable[[], Any]) -> tuple[Any, Dict[str, Any]]:
        """
        Run a workload while sampling CPU/Memory monitoring metrics.

        Args:
            db_name: Database target (sqlite/mongo)
            phase_name: Logical phase name (inserts/queries)
            workload: Callable to execute

        Returns:
            Tuple of (workload result, monitoring metrics dictionary)
        """
        process_monitor = _ProcessMonitor(sample_interval_s=0.5)
        mongo_monitor = _DockerContainerMonitor(container_name="benchmark_mongo", sample_interval_s=1.0) \
            if db_name == "mongo" else None

        process_monitor.start()
        if mongo_monitor:
            mongo_monitor.start()

        try:
            result = workload()
        finally:
            process_stats = process_monitor.stop()
            mongo_stats = mongo_monitor.stop() if mongo_monitor else None

        metrics = {
            "phase": phase_name,
            "runner_process": process_stats
        }
        if mongo_stats is not None:
            metrics["mongo_container"] = mongo_stats
        return result, metrics

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

    def export_reports(self, results: Dict[str, Any], base_path: str):
        """
        Export a human-readable HTML benchmark report.

        Args:
            results: Benchmark results dictionary
            base_path: Base output path returned by save_results
        """
        html_path = f"{base_path}.html"
        html_text = self._build_html_report(results)
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html_text)
        self.console.print(f"[green]Report saved to {html_path}[/green]")

    def print_monitoring_summary(self, monitoring: Dict[str, Dict[str, Any]]):
        """Print CPU/Memory monitoring summary."""
        if not monitoring:
            return

        self.console.print("\n[bold cyan]═══ Resource Monitoring Summary ═══[/bold cyan]\n")

        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("DB", style="cyan")
        table.add_column("Phase")
        table.add_column("Scope")
        table.add_column("CPU Avg %", justify="right")
        table.add_column("CPU Peak %", justify="right")
        table.add_column("Mem Avg MB", justify="right")
        table.add_column("Mem Peak MB", justify="right")
        table.add_column("Status", style="yellow")

        for db_name, phases in monitoring.items():
            for phase_name, phase_stats in phases.items():
                for scope in ("runner_process", "mongo_container"):
                    stats = phase_stats.get(scope)
                    if stats is None:
                        continue
                    if not stats.get("available"):
                        table.add_row(
                            db_name.upper(), phase_name, scope,
                            "-", "-", "-", "-",
                            stats.get("reason", "unavailable")
                        )
                        continue

                    table.add_row(
                        db_name.upper(),
                        phase_name,
                        scope,
                        f"{(stats.get('cpu_avg_percent') or 0):.2f}",
                        f"{(stats.get('cpu_peak_percent') or 0):.2f}",
                        f"{(stats.get('memory_avg_mb') or 0):.2f}",
                        f"{(stats.get('memory_peak_mb') or 0):.2f}",
                        "ok"
                    )

        self.console.print(table)
        self.console.print()

    def _build_html_report(self, results: Dict[str, Any]) -> str:
        """Build a detailed, visual HTML report from benchmark results."""
        config = results.get("config", {})
        metadata = results.get("metadata", {})
        entities = metadata.get("entities", {})
        query_complexity = metadata.get("query_complexity", {})
        artifacts = metadata.get("artifacts", {})
        inserts = results.get("inserts", {})
        queries = results.get("queries", {})
        monitoring = results.get("monitoring", {})

        complexity_rank = {"low": 1, "medium": 2, "high": 3, "very_high": 4}

        total_records = 0
        for db_stats in inserts.values():
            total_records = max(total_records, sum(int(s.get("count", 0)) for s in db_stats.values()))

        db_query_means = {}
        for db_name, qstats in queries.items():
            means = [float(s.get("mean_ms", 0)) for s in qstats.values() if s.get("iterations", 0) > 0]
            if means:
                db_query_means[db_name] = float(np.mean(means))

        very_high_count = sum(1 for meta in query_complexity.values() if meta.get("level") == "very_high")

        def _max_metric(db: str, scope: str, metric: str) -> float:
            phases = monitoring.get(db, {})
            vals = []
            for phase in phases.values():
                stats = phase.get(scope, {})
                if stats.get("available") and stats.get(metric) is not None:
                    vals.append(float(stats.get(metric)))
            return max(vals) if vals else 0.0

        sqlite_peak_cpu = _max_metric("sqlite", "runner_process", "cpu_peak_percent")
        sqlite_peak_mem = _max_metric("sqlite", "runner_process", "memory_peak_mb")
        mongo_peak_cpu = _max_metric("mongo", "mongo_container", "cpu_peak_percent")
        mongo_peak_mem = _max_metric("mongo", "mongo_container", "memory_peak_mb")

        highlight_rows = []
        for query_id, meta in query_complexity.items():
            qname = ""
            mean_candidates = []
            for db_name, qstats in queries.items():
                if query_id in qstats:
                    s = qstats[query_id]
                    qname = s.get("query_name", qname)
                    if s.get("iterations", 0) > 0:
                        mean_candidates.append(float(s.get("mean_ms", 0)))
            highlight_rows.append({
                "id": query_id,
                "name": qname or query_id,
                "level": meta.get("level", "low"),
                "score": complexity_rank.get(meta.get("level", "low"), 1),
                "mean_ms": max(mean_candidates) if mean_candidates else 0.0,
                "why": meta.get("why", "")
            })

        highlight_rows = sorted(highlight_rows, key=lambda r: (r["score"], r["mean_ms"]), reverse=True)[:6]

        def table_from_df(df: pd.DataFrame) -> str:
            return df.to_html(index=False, border=0, classes="report-table", justify="left")

        def level_badge(level: str) -> str:
            safe = escape(level.lower())
            label = safe.replace("_", " ").title()
            return f"<span class='badge {safe}'>{label}</span>"

        config_rows = "".join(
            f"<tr><td>{escape(str(k))}</td><td>{escape(str(v))}</td></tr>"
            for k, v in config.items()
        )

        entity_sections = []
        for entity_name, entity_meta in entities.items():
            fields = entity_meta.get("fields", {})
            if not fields:
                continue
            field_df = pd.DataFrame(
                [{"Field": name, "Type": field_type} for name, field_type in fields.items()]
            )
            nested_count = sum(1 for t in fields.values() if "object" in t or "array" in t)
            entity_sections.append(
                f"""
                <details class="entity-card">
                  <summary><strong>{escape(entity_name)}</strong> <span class="muted">({len(fields)} fields, {nested_count} nested)</span></summary>
                  {table_from_df(field_df)}
                </details>
                """
            )

        complexity_rows = []
        for query_id, meta in sorted(
            query_complexity.items(),
            key=lambda item: int(re.sub(r"[^0-9]", "", item[0]) or 0)
        ):
            complexity_rows.append({
                "ID": query_id,
                "Complexity": level_badge(meta.get("level", "low")),
                "Why": escape(meta.get("why", "")),
                "Features": escape(", ".join(meta.get("features", [])))
            })
        complexity_df = pd.DataFrame(complexity_rows) if complexity_rows else pd.DataFrame()
        if not complexity_df.empty:
            complexity_html = complexity_df.to_html(index=False, border=0, classes="report-table", escape=False)
        else:
            complexity_html = "<p class='muted'>No complexity metadata available.</p>"

        insert_sections = []
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
            insert_sections.append(
                f"<section class='panel'><h3>{escape(db_name.upper())} Insert Throughput</h3>{table_from_df(pd.DataFrame(rows))}</section>"
            )

        query_sections = []
        for db_name, query_results in queries.items():
            if not query_results:
                continue
            rows = []
            for query_id, stats in query_results.items():
                level = query_complexity.get(query_id, {}).get("level", "low")
                rows.append({
                    "ID": query_id,
                    "Complexity": level_badge(level),
                    "Query": escape(stats.get("query_name", "")),
                    "Results": f"{int(stats.get('avg_result_count', 0)):,}",
                    "Mean (ms)": f"{float(stats.get('mean_ms', 0)):.2f}",
                    "P95 (ms)": f"{float(stats.get('p95_ms', 0)):.2f}",
                    "P99 (ms)": f"{float(stats.get('p99_ms', 0)):.2f}"
                })
            qdf = pd.DataFrame(rows)
            query_sections.append(
                f"<section class='panel'><h3>{escape(db_name.upper())} Query Latency</h3>{qdf.to_html(index=False, border=0, classes='report-table', escape=False)}</section>"
            )

        comparison_panel = ""
        sqlite_queries = queries.get("sqlite")
        mongo_queries = queries.get("mongo")
        if sqlite_queries and mongo_queries:
            cmp_df = self.compare_databases(sqlite_queries, mongo_queries)
            max_speedup = float(cmp_df["Speedup %"].max()) if not cmp_df.empty else 1.0
            max_speedup = max(max_speedup, 1.0)
            bar_rows = []
            for _, row in cmp_df.sort_values("Speedup %", ascending=False).iterrows():
                faster = str(row["Faster"])
                if faster == "SQLite":
                    db_class = "sqlite"
                elif faster == "MongoDB":
                    db_class = "mongo"
                else:
                    db_class = "neutral"
                width = (float(row["Speedup %"]) / max_speedup) * 100.0
                bar_rows.append(
                    f"""
                    <div class="speed-row">
                      <div class="speed-label">{escape(row['Query ID'])} <span class="muted">{escape(str(row['Query Name'])[:42])}</span></div>
                      <div class="speed-track"><span class="speed-fill {db_class}" style="width:{width:.1f}%"></span></div>
                      <div class="speed-value">{escape(faster)} {float(row['Speedup %']):.1f}%</div>
                    </div>
                    """
                )

            cmp_display_df = cmp_df.copy()
            query_id_with_dot = []
            for _, row in cmp_display_df.iterrows():
                qid = str(row.get("Query ID", ""))
                level = str(query_complexity.get(qid, {}).get("level", "low")).lower()
                dot = f"<span class='complexity-dot {escape(level)}' title='{escape(level.replace('_', ' ').title())}'></span>"
                query_id_with_dot.append(f"<span class='qid-cell'>{dot}<span>{escape(qid)}</span></span>")
            cmp_display_df["Query ID"] = query_id_with_dot

            comparison_panel = f"""
            <section class="panel">
              <h3>SQLite vs MongoDB: Relative Wins</h3>
              <div class="speed-grid">{''.join(bar_rows)}</div>
              {cmp_display_df.round(3).to_html(index=False, border=0, classes='report-table', escape=False)}
            </section>
            """

        embedded_chart_html = ""
        chart_path = artifacts.get("comparison_chart_png")
        if chart_path and os.path.exists(chart_path):
            try:
                with open(chart_path, "rb") as chart_file:
                    chart_b64 = base64.b64encode(chart_file.read()).decode("ascii")
                embedded_chart_html = f"""
                <section class="panel">
                  <h3>Comparison Chart</h3>
                  <p class="muted">Visual comparison of query latency and relative speedup between SQLite and MongoDB.</p>
                  <img class="embedded-chart" src="data:image/png;base64,{chart_b64}" alt="SQLite vs MongoDB comparison chart" />
                </section>
                """
            except Exception as exc:
                embedded_chart_html = f"""
                <section class="panel">
                  <h3>Comparison Chart</h3>
                  <p class="muted">Could not embed chart image: {escape(str(exc))}</p>
                </section>
                """

        monitoring_rows = []
        for db_name, phases in monitoring.items():
            for phase_name, phase_stats in phases.items():
                for scope in ("runner_process", "mongo_container"):
                    stats = phase_stats.get(scope)
                    if stats is None:
                        continue
                    monitoring_rows.append({
                        "DB": db_name.upper(),
                        "Phase": phase_name,
                        "Scope": scope,
                        "CPU Avg %": "-" if not stats.get("available") or stats.get("cpu_avg_percent") is None else f"{float(stats.get('cpu_avg_percent')):.2f}",
                        "CPU Peak %": "-" if not stats.get("available") or stats.get("cpu_peak_percent") is None else f"{float(stats.get('cpu_peak_percent')):.2f}",
                        "Mem Avg MB": "-" if not stats.get("available") or stats.get("memory_avg_mb") is None else f"{float(stats.get('memory_avg_mb')):.2f}",
                        "Mem Peak MB": "-" if not stats.get("available") or stats.get("memory_peak_mb") is None else f"{float(stats.get('memory_peak_mb')):.2f}"
                    })
        monitoring_html = (
            table_from_df(pd.DataFrame(monitoring_rows))
            if monitoring_rows else "<p class='muted'>Monitoring metrics were not collected.</p>"
        )

        highlight_cards = []
        for row in highlight_rows:
            highlight_cards.append(
                f"""
                <article class="mini-card">
                  <div class="mini-top">
                    <span class="query-id">{escape(row['id'])}</span>
                    {level_badge(row['level'])}
                  </div>
                  <h4>{escape(row['name'])}</h4>
                  <p class="muted">{escape(row['why'])}</p>
                  <div class="metric-line">Worst mean latency: <strong>{row['mean_ms']:.2f} ms</strong></div>
                </article>
                """
            )

        html = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Benchmark Report</title>
  <style>
    :root {{
      --bg1:#f4fbf6; --bg2:#e8f4ff; --ink:#0f172a; --muted:#4b5563;
      --panel:#ffffff; --line:#dbe3ec; --accent:#0f766e; --accent2:#0369a1;
      --low:#94a3b8; --medium:#0ea5e9; --high:#f59e0b; --veryhigh:#dc2626;
      --sqlite:#0ea5a4; --mongo:#2563eb; --neutral:#64748b;
    }}
    * {{ box-sizing:border-box; }}
    body {{
      margin:0; color:var(--ink); line-height:1.45;
      font-family:"IBM Plex Sans","Segoe UI",system-ui,sans-serif;
      background: radial-gradient(circle at 12% 15%, var(--bg1), transparent 35%),
                  radial-gradient(circle at 88% 5%, var(--bg2), transparent 30%),
                  linear-gradient(140deg, #f8fafc, #eef6ff 55%, #f7fbf3);
    }}
    .wrap {{ width:min(1200px, 94vw); margin:28px auto 60px; }}
    .hero {{
      background: linear-gradient(120deg, #0f766e, #0369a1 60%, #334155);
      color:#f8fafc; border-radius:20px; padding:28px 30px; box-shadow:0 18px 40px rgba(15,23,42,.22);
      animation: fadeUp .5s ease both;
    }}
    .hero h1 {{ margin:0 0 6px; font-size: clamp(1.6rem, 2.2vw, 2.3rem); letter-spacing:.2px; }}
    .hero p {{ margin:0; opacity:.92; }}
    .kpi-grid {{
      display:grid; grid-template-columns:repeat(auto-fit,minmax(180px,1fr)); gap:14px; margin-top:18px;
    }}
    .kpi {{
      background:rgba(255,255,255,.12); border:1px solid rgba(255,255,255,.24);
      border-radius:14px; padding:14px 12px;
    }}
    .kpi .label {{ font-size:.78rem; text-transform:uppercase; letter-spacing:.08em; opacity:.88; }}
    .kpi .value {{ font-size:1.45rem; font-weight:700; margin-top:4px; }}
    .section {{ margin-top:24px; animation: fadeUp .55s ease both; }}
    .section h2 {{ margin:0 0 12px; font-size:1.2rem; }}
    .panel {{
      background:var(--panel); border:1px solid var(--line); border-radius:16px; padding:16px;
      box-shadow:0 8px 24px rgba(15,23,42,.06);
    }}
    .panel h3 {{ margin:0 0 10px; color:#0b3b55; }}
    .stack {{ display:grid; gap:14px; }}
    .two-col {{ display:grid; gap:14px; grid-template-columns:1fr; }}
    @media (min-width: 980px) {{ .two-col {{ grid-template-columns: 1.1fr 1fr; }} }}
    .report-table {{ width:100%; border-collapse:collapse; font-size:.9rem; }}
    .report-table th, .report-table td {{ border-bottom:1px solid var(--line); padding:8px 10px; text-align:left; vertical-align:top; }}
    .report-table th {{ background:#f8fbff; color:#0b3b55; position:sticky; top:0; }}
    .report-table tr:hover td {{ background:#f7fbff; }}
    .report-table th:nth-child(2), .report-table td:nth-child(2) {{ min-width: 118px; }}
    .muted {{ color:var(--muted); }}
    details.entity-card {{
      background:#fff; border:1px solid var(--line); border-radius:12px; padding:8px 12px; margin-bottom:10px;
    }}
    details.entity-card summary {{ cursor:pointer; padding:4px 0; }}
    .badge {{
      display:inline-block; border-radius:999px; padding:2px 9px; font-size:.74rem; font-weight:700;
      text-transform:uppercase; letter-spacing:.04em;
      white-space: nowrap;
    }}
    .badge.low {{ background:#e2e8f0; color:#334155; }}
    .badge.medium {{ background:#dbeafe; color:#1d4ed8; }}
    .badge.high {{ background:#fef3c7; color:#92400e; }}
    .badge.very_high {{ background:#fee2e2; color:#991b1b; }}
    .highlights {{ display:grid; gap:12px; grid-template-columns:repeat(auto-fit,minmax(240px,1fr)); }}
    .mini-card {{
      background:#fff; border:1px solid var(--line); border-radius:14px; padding:14px;
      box-shadow:0 6px 20px rgba(2,132,199,.08);
    }}
    .mini-top {{ display:flex; justify-content:space-between; align-items:center; gap:8px; margin-bottom:8px; }}
    .query-id {{ font-weight:700; color:#0b3b55; }}
    .mini-card h4 {{ margin:0 0 6px; font-size:1rem; }}
    .metric-line {{ margin-top:8px; font-size:.9rem; }}
    .speed-grid {{ display:grid; gap:8px; margin-bottom:14px; }}
    .speed-row {{ display:grid; grid-template-columns: minmax(170px, 1.2fr) 2fr 130px; align-items:center; gap:10px; }}
    .speed-label {{ font-size:.86rem; }}
    .speed-track {{ height:10px; background:#e2e8f0; border-radius:999px; overflow:hidden; }}
    .speed-fill {{ display:block; height:100%; border-radius:999px; }}
    .speed-fill.sqlite {{ background:linear-gradient(90deg, #14b8a6, #0f766e); }}
    .speed-fill.mongo {{ background:linear-gradient(90deg, #60a5fa, #1d4ed8); }}
    .speed-fill.neutral {{ background:linear-gradient(90deg, #94a3b8, #64748b); }}
    .speed-value {{ text-align:right; font-size:.86rem; font-weight:600; }}
    .complexity-dot {{
      display:inline-block;
      width:10px;
      height:10px;
      border-radius:50%;
      vertical-align:middle;
    }}
    .complexity-dot.low {{ background: var(--low); }}
    .complexity-dot.medium {{ background: var(--medium); }}
    .complexity-dot.high {{ background: var(--high); }}
    .complexity-dot.very_high {{ background: var(--veryhigh); }}
    .qid-cell {{
      display:inline-flex;
      align-items:center;
      gap:8px;
    }}
    .embedded-chart {{
      width: 100%;
      border-radius: 12px;
      border: 1px solid var(--line);
      box-shadow: 0 10px 28px rgba(15,23,42,.10);
      background: #fff;
    }}
    @keyframes fadeUp {{ from {{ opacity:0; transform:translateY(8px); }} to {{ opacity:1; transform:none; }} }}
  </style>
</head>
<body>
  <main class="wrap">
    <section class="hero">
      <h1>SQLite vs MongoDB Benchmark Report</h1>
      <p>Detailed performance, schema and complexity analysis generated from your latest run.</p>
        <div class="kpi-grid">
        <div class="kpi"><div class="label">Base Records</div><div class="value">{int(config.get('records', 0)):,}</div></div>
        <div class="kpi"><div class="label">Generated Records</div><div class="value">{total_records:,}</div></div>
        <div class="kpi"><div class="label">Query Set Size</div><div class="value">{len(query_complexity)}</div></div>
        <div class="kpi"><div class="label">Very High Complexity</div><div class="value">{very_high_count}</div></div>
        <div class="kpi"><div class="label">Avg SQLite Mean</div><div class="value">{db_query_means.get('sqlite', 0):.2f} ms</div></div>
        <div class="kpi"><div class="label">Avg Mongo Mean</div><div class="value">{db_query_means.get('mongo', 0):.2f} ms</div></div>
        <div class="kpi"><div class="label">SQLite Peak CPU</div><div class="value">{sqlite_peak_cpu:.1f}%</div></div>
        <div class="kpi"><div class="label">SQLite Peak Mem</div><div class="value">{sqlite_peak_mem:.1f} MB</div></div>
        <div class="kpi"><div class="label">Mongo Peak CPU</div><div class="value">{mongo_peak_cpu:.1f}%</div></div>
        <div class="kpi"><div class="label">Mongo Peak Mem</div><div class="value">{mongo_peak_mem:.1f} MB</div></div>
      </div>
    </section>

    <section class="section two-col">
      <article class="panel">
        <h2>Run Configuration</h2>
        <table class="report-table"><thead><tr><th>Parameter</th><th>Value</th></tr></thead><tbody>{config_rows}</tbody></table>
      </article>
      <article class="panel">
        <h2>Most Demanding Queries</h2>
        <div class="highlights">{''.join(highlight_cards)}</div>
      </article>
    </section>

    <section class="section">
      <article class="panel">
        <h2>Entity Schema</h2>
        <p class="muted">Field names and data types per entity, including nested structures.</p>
        {''.join(entity_sections)}
      </article>
    </section>

    <section class="section">
      <article class="panel">
        <h2>Query Complexity</h2>
        <p class="muted">Complexity profile shows why each query is simple/advanced and what operations dominate runtime.</p>
        {complexity_html}
      </article>
    </section>

    <section class="section stack">
      {''.join(insert_sections)}
    </section>

    <section class="section stack">
      {''.join(query_sections)}
    </section>

    <section class="section">
      <article class="panel">
        <h2>Resource Monitoring (CPU / Memory)</h2>
        <p class="muted">Sampled during inserts and queries for each solution.</p>
        {monitoring_html}
      </article>
    </section>

    <section class="section">
      {embedded_chart_html}
    </section>

    <section class="section">
      {comparison_panel}
    </section>
  </main>
</body>
</html>"""
        return html

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
