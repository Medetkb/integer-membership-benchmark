#!/usr/bin/env python3
"""Paired list/set membership measurements; Python standard library only.

The controller launches one fresh process per (size, hit rate, seed).
All relative config/data paths are resolved from the repository root.
"""

from __future__ import annotations

import argparse
import csv
import gc
import hashlib
import json
import math
import os
import platform
import random
import statistics
import subprocess
import sys
import time
import tracemalloc
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
METHODS = {"list": list, "set": set}
MIB = 1024 * 1024


def root_path(path: str | Path) -> Path:
    path = Path(path)
    return path if path.is_absolute() else ROOT / path


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def positive_integer(value: object) -> bool:
    return type(value) is int and value > 0


def finite_number(value: object) -> bool:
    return type(value) in (int, float) and math.isfinite(value)


def validate_config(config: dict) -> None:
    if not isinstance(config, dict):
        raise ValueError("The configuration must be a JSON object.")
    required = {
        "schema_version", "mode", "sample_path", "dataset_sizes", "hit_rates", "seeds",
        "queries_per_batch", "batch_loops", "warmup_pairs", "measurement_pairs",
        "worker_timeout_seconds", "output_dir", "guardrails", "hypothesis",
    }
    if set(config) != required:
        raise ValueError(f"Config fields differ: {sorted(set(config) ^ required)}")
    if config["schema_version"] != 1 or config["mode"] not in ("smoke", "study"):
        raise ValueError("Use schema_version 1 and mode smoke or study.")
    for name in ("sample_path", "output_dir"):
        if not isinstance(config[name], str) or not config[name].strip():
            raise ValueError(f"{name} must be a nonempty path.")
    for name in ("queries_per_batch", "batch_loops", "measurement_pairs"):
        if not positive_integer(config[name]):
            raise ValueError(f"{name} must be a positive integer.")
    if config["measurement_pairs"] < 4 or config["measurement_pairs"] % 2:
        raise ValueError("measurement_pairs must be even and at least 4 (balanced order).")
    if type(config["warmup_pairs"]) is not int or config["warmup_pairs"] < 0:
        raise ValueError("warmup_pairs must be a nonnegative integer.")
    if not finite_number(config["worker_timeout_seconds"]) or config["worker_timeout_seconds"] <= 0:
        raise ValueError("worker_timeout_seconds must be positive and finite.")
    for name in ("dataset_sizes", "seeds"):
        values = config[name]
        if not isinstance(values, list) or not values or not all(positive_integer(v) for v in values):
            raise ValueError(f"{name} must be a nonempty list of positive integers.")
        if len(values) != len(set(values)):
            raise ValueError(f"{name} must contain unique values.")
    rates = config["hit_rates"]
    if not isinstance(rates, list) or not rates or any(not finite_number(v) or not 0 <= v <= 1 for v in rates):
        raise ValueError("hit_rates must be finite values between 0 and 1.")
    if len(rates) != len(set(rates)):
        raise ValueError("hit_rates must be unique.")
    for rate in rates:
        hits = rate * config["queries_per_batch"]
        if not math.isclose(hits, round(hits), rel_tol=0, abs_tol=1e-9):
            raise ValueError("Each hit rate must imply an integer number of queries.")
    guard = config["guardrails"]
    if not isinstance(guard, dict) or set(guard) != {"max_errors", "max_peak_python_mib"}:
        raise ValueError("guardrails must specify max_errors and max_peak_python_mib.")
    if type(guard["max_errors"]) is not int or guard["max_errors"] != 0:
        raise ValueError("Correctness requires max_errors = 0.")
    if not finite_number(guard["max_peak_python_mib"]) or guard["max_peak_python_mib"] <= 0:
        raise ValueError("max_peak_python_mib must be positive and finite.")
    hyp = config["hypothesis"]
    if not isinstance(hyp, dict) or set(hyp) != {
        "primary_size", "primary_hit_rate", "minimum_relative_improvement", "alpha", "required_seeds"
    }:
        raise ValueError("Invalid hypothesis fields.")
    if not positive_integer(hyp["primary_size"]) or not positive_integer(hyp["required_seeds"]):
        raise ValueError("Primary size and required seeds must be positive integers.")
    for name in ("primary_hit_rate", "minimum_relative_improvement", "alpha"):
        if not finite_number(hyp[name]) or not 0 <= hyp[name] <= 1:
            raise ValueError(f"Invalid {name}.")
    if not 0 < hyp["alpha"] < 1 or not 0 < hyp["minimum_relative_improvement"] < 1:
        raise ValueError("alpha and minimum_relative_improvement must be strictly between 0 and 1.")


def load_sample(path: Path) -> list[int]:
    with path.open(newline="", encoding="utf-8") as stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames != ["key"]:
            raise ValueError("Sample CSV must have exactly one column named key.")
        rows = list(reader)
    if any(set(row) != {"key"} or row["key"] is None for row in rows):
        raise ValueError("Every sample row must contain exactly one integer.")
    keys = [int(row["key"]) for row in rows]
    if not keys or len(set(keys)) != len(keys):
        raise ValueError("Sample keys must be nonempty and unique.")
    return keys


def make_workload(keys: list[int], query_count: int, hit_rate: float, seed: int) -> tuple[list[int], list[bool]]:
    """Ground truth is assigned when sampling, independent of either algorithm."""
    rng = random.Random(seed)
    hit_count = round(query_count * hit_rate)
    # Recreate integer objects instead of intentionally reusing key object identities.
    queries = [(int(str(rng.choice(keys))), True) for _ in range(hit_count)]
    first_miss = max(keys) + 1
    queries.extend((first_miss + rng.randrange(len(keys)), False) for _ in range(query_count - hit_count))
    rng.shuffle(queries)
    return [item[0] for item in queries], [item[1] for item in queries]


def workload_digest(keys: list[int], queries: list[int], expected: list[bool]) -> str:
    payload = json.dumps([keys, queries, expected], separators=(",", ":"))
    return hashlib.sha256(payload.encode()).hexdigest()


def count_hits(container: list[int] | set[int], queries: list[int], loops: int) -> int:
    hits = 0
    for _ in range(loops):
        for query in queries:
            hits += query in container
    return hits


def memory_and_errors(method: str, keys: list[int], queries: list[int], expected: list[bool]) -> tuple[int, int]:
    """Separate, untimed pass. Existing input keys/queries are outside the trace."""
    gc.collect()
    tracemalloc.start()
    try:
        container = METHODS[method](keys)
        predicted = [query in container for query in queries]
        _, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
    return peak, sum(a != b for a, b in zip(predicted, expected, strict=True))


def measure(method: str, keys: list[int], queries: list[int], loops: int, expected_hits: int) -> tuple[int, int, int]:
    """Construction and lookup get separate timers; neither has memory tracing."""
    gc.collect()
    was_enabled = gc.isenabled()
    gc.disable()
    try:
        start = time.perf_counter_ns()
        container = METHODS[method](keys)
        build_ns = time.perf_counter_ns() - start
        start = time.perf_counter_ns()
        found = count_hits(container, queries, loops)
        elapsed_ns = time.perf_counter_ns() - start
    finally:
        if was_enabled:
            gc.enable()
    if elapsed_ns <= 0:
        raise RuntimeError("Timer returned a nonpositive elapsed duration.")
    return build_ns, elapsed_ns, int(found != expected_hits * loops)


def run_worker(task: dict) -> dict:
    config = task["config"]
    seed, size, rate = task["seed"], task["size"], task["hit_rate"]
    keys = list(task["sample_keys"]) if config["mode"] == "smoke" else [1_000_000 + 2 * i for i in range(size)]
    random.Random(seed).shuffle(keys)
    queries, expected = make_workload(keys, config["queries_per_batch"], rate, seed + 1_000_000)
    digest = workload_digest(keys, queries, expected)
    memory = {method: memory_and_errors(method, keys, queries, expected) for method in METHODS}
    loops = config["batch_loops"]
    expected_hits = sum(expected)
    for _ in range(config["warmup_pairs"]):
        for method in METHODS:
            _, _, errors = measure(method, keys, queries, loops, expected_hits)
            if errors:
                raise RuntimeError("Incorrect warmup output.")
    # Each method is first in exactly half the pairs; shuffle that balanced schedule.
    orders = [("list", "set"), ("set", "list")] * (config["measurement_pairs"] // 2)
    random.Random(seed + 2_000_000).shuffle(orders)
    rows = []
    for pair, order in enumerate(orders, start=1):
        for position, method in enumerate(order, start=1):
            build_ns, elapsed_ns, errors = measure(method, keys, queries, loops, expected_hits)
            peak, vector_errors = memory[method]
            lookups = len(queries) * loops
            rows.append({
                "size": size, "hit_rate": rate, "seed": seed, "method": method,
                "pair": pair, "order_position": position, "lookups": lookups,
                "batch_elapsed_ns": elapsed_ns, "mean_lookup_ns": elapsed_ns / lookups,
                "throughput_ops_per_s": lookups * 1e9 / elapsed_ns, "build_ns": build_ns,
                "peak_python_bytes": peak, "errors": errors + vector_errors,
                "workload_sha256": digest,
            })
    return {"rows": rows}


def binomial_upper_tail(successes: int, total: int) -> float:
    """Exact one-sided sign-test p-value under p=0.5. Ties count as failures."""
    if not 0 <= successes <= total or total <= 0:
        raise ValueError("Require 0 <= successes <= total and total > 0.")
    return sum(math.comb(total, k) for k in range(successes, total + 1)) / 2**total


def summarize(rows: list[dict], config: dict, runtime_match: bool) -> dict:
    per_seed = []
    groups = sorted({(row["size"], row["hit_rate"], row["seed"]) for row in rows})
    for size, rate, seed in groups:
        group = [row for row in rows if (row["size"], row["hit_rate"], row["seed"]) == (size, rate, seed)]
        medians = {
            method: statistics.median(row["mean_lookup_ns"] for row in group if row["method"] == method)
            for method in METHODS
        }
        per_seed.append({
            "size": size, "hit_rate": rate, "seed": seed,
            "list_median_mean_lookup_ns": medians["list"], "set_median_mean_lookup_ns": medians["set"],
            "relative_improvement": 1 - medians["set"] / medians["list"],
            "speedup": medians["list"] / medians["set"],
        })
    scenarios = []
    for size, rate in sorted({(row["size"], row["hit_rate"]) for row in rows}):
        chosen = [row for row in per_seed if (row["size"], row["hit_rate"]) == (size, rate)]
        for method in METHODS:
            subset = [row for row in rows if (row["size"], row["hit_rate"], row["method"]) == (size, rate, method)]
            scenarios.append({
                "size": size, "hit_rate": rate, "method": method, "seed_count": len(chosen),
                "median_of_seed_medians_ns": statistics.median(row[f"{method}_median_mean_lookup_ns"] for row in chosen),
                "median_build_ns": statistics.median(row["build_ns"] for row in subset),
                "max_peak_python_mib": max(row["peak_python_bytes"] for row in subset) / MIB,
                "max_errors_in_any_measurement": max(row["errors"] for row in subset),
            })
    guardrails_pass = all(
        row["errors"] <= config["guardrails"]["max_errors"]
        and row["peak_python_bytes"] <= config["guardrails"]["max_peak_python_mib"] * MIB
        for row in rows
    )
    hyp = config["hypothesis"]
    primary = [row for row in per_seed if row["size"] == hyp["primary_size"] and row["hit_rate"] == hyp["primary_hit_rate"]]
    eligible = config["mode"] == "study" and len(primary) == hyp["required_seeds"] and runtime_match
    analysis = {
        "eligible_for_primary_test": eligible,
        "primary_seed_count": len(primary),
        "p_value_one_sided": None,
        "median_relative_improvement": None,
        "seeds_strictly_above_threshold": None,
        "statistical_decision": "not_evaluated",
        "practical_decision": "not_evaluated",
        "note": "Smoke runs and incomplete studies cannot test the research hypothesis.",
    }
    if eligible:
        improvements = [row["relative_improvement"] for row in primary]
        successes = sum(value > hyp["minimum_relative_improvement"] for value in improvements)
        p_value = binomial_upper_tail(successes, len(improvements))
        reject = p_value < hyp["alpha"]
        analysis.update({
            "p_value_one_sided": p_value,
            "median_relative_improvement": statistics.median(improvements),
            "seeds_strictly_above_threshold": successes,
            "statistical_decision": "reject_H0" if reject else "do_not_reject_H0",
            "practical_decision": "supports_H1_within_scope" if reject and guardrails_pass else "criteria_not_met",
            "note": "One prespecified primary scenario; other scenarios are descriptive. Conditional on this machine and protocol.",
        })
    return {"guardrails_pass": guardrails_pass, "scenarios": scenarios, "paired_seed_estimates": per_seed, "analysis": analysis}


def environment_metadata(config_path: Path, config: dict) -> dict:
    pinned = (ROOT / ".python-version").read_text().strip()
    info = time.get_clock_info("perf_counter")
    files = [Path("src/benchmark.py"), Path(".python-version"), Path("requirements.txt"), Path("data/sample/keys.csv")]
    return {
        "started_utc": datetime.now(timezone.utc).isoformat(),
        "python": platform.python_version(), "python_build": platform.python_build(),
        "implementation": platform.python_implementation(), "reference_python": pinned,
        "runtime_matches_pin": platform.python_version() == pinned and platform.python_implementation() == "CPython",
        "os": platform.system(), "os_release": platform.release(), "os_version": platform.version(),
        "architecture": platform.machine(), "processor": platform.processor(), "logical_cpu_count": os.cpu_count(),
        "clock": {"implementation": info.implementation, "resolution_seconds": info.resolution, "monotonic": info.monotonic},
        "worker_pythonhashseed": "0", "config_name": config_path.name,
        "config_sha256": sha256_file(config_path),
        "input_and_code_sha256": {path.as_posix(): sha256_file(ROOT / path) for path in files},
        "configured_sample_sha256": sha256_file(root_path(config["sample_path"])),
        "measurement_scope": "in-process Python membership loop; I/O and construction excluded from lookup timer",
        "memory_scope": "incremental traced Python allocations for container plus one Boolean output vector; not RSS",
    }


def run_controller(config_path: Path, output_override: str | None) -> int:
    config = json.loads(config_path.read_text(encoding="utf-8"))
    validate_config(config)
    sample_keys = load_sample(root_path(config["sample_path"]))
    if config["mode"] == "smoke" and config["dataset_sizes"] != [len(sample_keys)]:
        raise ValueError("Smoke dataset_sizes must match the CSV row count exactly.")
    output = root_path(output_override or config["output_dir"])
    output.mkdir(parents=True, exist_ok=True)
    if any(output.iterdir()):
        raise ValueError(f"Output directory is not empty: {output}. Choose a new --output path.")
    metadata = environment_metadata(config_path, config)
    write_json(output / "environment.json", metadata)
    write_json(output / "config.snapshot.json", config)
    if not metadata["runtime_matches_pin"]:
        print("NOTE: Python differs from .python-version; primary inference is disabled.", file=sys.stderr)
    tasks = [(size, rate, seed) for size in config["dataset_sizes"] for rate in config["hit_rates"] for seed in config["seeds"]]
    # Spread temporal drift over the workload grid with a fixed, recorded scheduling rule.
    random.Random(8675309).shuffle(tasks)
    write_json(output / "schedule.json", [{"size": size, "hit_rate": rate, "seed": seed} for size, rate, seed in tasks])
    started = time.monotonic()
    rows = []
    with (output / "raw.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = None
        for index, (size, rate, seed) in enumerate(tasks, start=1):
            task = {"config": config, "size": size, "hit_rate": rate, "seed": seed, "sample_keys": sample_keys}
            try:
                completed = subprocess.run(
                    [sys.executable, str(Path(__file__).resolve()), "--worker"],
                    input=json.dumps(task), text=True, capture_output=True,
                    timeout=config["worker_timeout_seconds"], check=True,
                    env={**os.environ, "PYTHONHASHSEED": "0", "PYTHONDONTWRITEBYTECODE": "1"},
                )
                new_rows = json.loads(completed.stdout)["rows"]
            except (subprocess.TimeoutExpired, subprocess.CalledProcessError, json.JSONDecodeError, KeyError) as error:
                write_json(output / "status.json", {
                    "status": "failed", "completed_workers": index - 1,
                    "failed_task": {"size": size, "hit_rate": rate, "seed": seed},
                    "error": type(error).__name__,
                    "detail": str(getattr(error, "stderr", "") or str(error))[-2000:],
                    "note": "Partial raw data retained. No hypothesis test was performed.",
                })
                print(f"FAILED worker {index}/{len(tasks)}; see status.json", file=sys.stderr)
                return 3
            if writer is None:
                writer = csv.DictWriter(stream, fieldnames=list(new_rows[0]))
                writer.writeheader()
            writer.writerows(new_rows)
            stream.flush()
            rows.extend(new_rows)
            print(f"Completed {index}/{len(tasks)}: n={size}, hit_rate={rate}, seed={seed}", flush=True)
    summary = summarize(rows, config, metadata["runtime_matches_pin"])
    write_json(output / "summary.json", summary)
    status = "completed" if summary["guardrails_pass"] else "guardrail_failed"
    write_json(output / "status.json", {
        "status": status, "mode": config["mode"], "workers": len(tasks), "raw_rows": len(rows),
        "elapsed_seconds": time.monotonic() - started, "guardrails_pass": summary["guardrails_pass"],
        "finished_utc": datetime.now(timezone.utc).isoformat(),
    })
    print(f"{status.upper()}: {len(rows)} measurements; results in {output}")
    print("Hypothesis decision: " + summary["analysis"]["statistical_decision"])
    return 0 if summary["guardrails_pass"] else 2


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="config.json", help="JSON config; relative paths use repository root")
    parser.add_argument("--output", help="New or empty output directory; relative paths use repository root")
    parser.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    if sys.version_info < (3, 12):
        parser.error("Python 3.12 or newer is required; reference runtime is in .python-version.")
    try:
        if args.worker:
            result = run_worker(json.load(sys.stdin))
            print(json.dumps(result, allow_nan=False))
            return 0
        return run_controller(root_path(args.config), args.output)
    except (ValueError, OSError, TypeError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
