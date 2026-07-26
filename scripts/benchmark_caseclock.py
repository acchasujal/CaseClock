"""Reproducible local benchmarks for deterministic CaseClock prototype code.

Uses only in-memory synthetic data and does not touch production persistence.
"""
from __future__ import annotations

import json
import platform
import statistics
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from backend.app.core.clock.engine import ClockEngine
from synthetic_data.configs import SyntheticDataConfig
from synthetic_data.generator import generate_synthetic_graph


def pct(values: list[float], p: float) -> float:
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, round((p / 100) * (len(ordered) - 1))))
    return ordered[index]


def run_size(case_count: int, repeats: int = 7) -> dict[str, object]:
    assembly = generate_synthetic_graph(SyntheticDataConfig(seed=42, case_count=case_count))
    clock_nodes = [record.node for record in assembly.clock_records]
    engine = ClockEngine(datetime(2026, 1, 1, tzinfo=timezone.utc))

    for node in clock_nodes:
        engine.from_clock_node(str(node.id), node.properties)

    timings: list[float] = []
    last_statuses: list[str] = []
    for _ in range(repeats):
        start = time.perf_counter()
        responses = [engine.from_clock_node(str(node.id), node.properties) for node in clock_nodes]
        timings.append((time.perf_counter() - start) * 1000)
        last_statuses = [response.status.value for response in responses]

    return {
        "cases": len(assembly.case_blueprints),
        "clocks": len(clock_nodes),
        "runs": repeats,
        "runtime_ms_p50": round(pct(timings, 50), 3),
        "runtime_ms_p95": round(pct(timings, 95), 3),
        "runtime_ms_mean": round(statistics.mean(timings), 3),
        "clocks_per_sec_p50": round(len(clock_nodes) / (pct(timings, 50) / 1000), 1),
        "status_counts": {status: last_statuses.count(status) for status in sorted(set(last_statuses))},
    }


def main() -> None:
    results = [run_size(size) for size in (100, 500, 1000, 5000)]
    payload = {
        "environment": {
            "os": platform.platform(),
            "python": sys.version.split()[0],
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        },
        "dataset": "SyntheticDataConfig(seed=42), generated in memory; no production data modified.",
        "results": results,
    }
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
