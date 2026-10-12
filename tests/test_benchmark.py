"""Check scientific invariants and the runnable pipeline, not timing thresholds."""

import csv
import json
import math
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from src import benchmark as bench


def default_config():
    return json.loads((bench.ROOT / "config.json").read_text())


class ScientificInvariantTests(unittest.TestCase):
    def test_workload_has_exact_ground_truth_and_is_reproducible(self):
        keys = [10, 20, 30, 40]
        for rate in (0.0, 0.5, 1.0):
            first = bench.make_workload(keys, 100, rate, 42)
            self.assertEqual(first, bench.make_workload(keys, 100, rate, 42))
            queries, expected = first
            self.assertEqual(sum(expected), round(100 * rate))
            self.assertEqual(expected, [query in keys for query in queries])

    def test_list_and_set_agree_including_duplicates_negative_values_and_misses(self):
        keys = [-10, 0, 0, 1000]
        queries = [-10, -1, 0, 1000, 1001]
        expected = [True, False, True, True, False]
        for method in bench.METHODS:
            peak, errors = bench.memory_and_errors(method, keys, queries, expected)
            self.assertEqual(errors, 0)
            self.assertGreater(peak, 0)
            self.assertEqual(bench.count_hits(bench.METHODS[method](keys), queries, 7), 21)

    def test_exact_sign_test_known_values(self):
        self.assertEqual(bench.binomial_upper_tail(0, 5), 1.0)
        self.assertEqual(bench.binomial_upper_tail(5, 5), 1 / 32)
        self.assertAlmostEqual(bench.binomial_upper_tail(4, 5), 6 / 32)
        self.assertLess(bench.binomial_upper_tail(20, 30), 0.05)
        self.assertGreater(bench.binomial_upper_tail(19, 30), 0.05)

    def test_invalid_config_is_rejected(self):
        for field, value in (("seeds", [1, 1]), ("hit_rates", [0.333]),
                             ("batch_loops", 0), ("measurement_pairs", 3),
                             ("worker_timeout_seconds", float("nan"))):
            config = default_config()
            config[field] = value
            if field == "hit_rates":
                config["queries_per_batch"] = 10
            with self.subTest(field=field), self.assertRaises(ValueError):
                bench.validate_config(config)

    def test_bad_sample_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bad.csv"
            for text in ("id\n1\n", "key\n1\n1\n", "key\n", "key\n1,2\n"):
                path.write_text(text)
                with self.subTest(text=text), self.assertRaises(ValueError):
                    bench.load_sample(path)

    def test_worker_balances_order_and_checks_every_method(self):
        config = default_config()
        config.update(queries_per_batch=10, batch_loops=2, warmup_pairs=0, measurement_pairs=4)
        task = {"config": config, "seed": 101, "size": 8, "hit_rate": 0.5,
                "sample_keys": bench.load_sample(bench.ROOT / "data/sample/keys.csv")}
        rows = bench.run_worker(task)["rows"]
        self.assertEqual(len(rows), 8)
        self.assertEqual(len({row["workload_sha256"] for row in rows}), 1)
        for method in bench.METHODS:
            subset = [row for row in rows if row["method"] == method]
            self.assertEqual(sum(row["order_position"] == 1 for row in subset), 2)
        for row in rows:
            self.assertEqual(row["errors"], 0)
            self.assertEqual(row["lookups"], 20)
            self.assertTrue(math.isfinite(row["mean_lookup_ns"]))
            self.assertGreater(row["mean_lookup_ns"], 0)
            self.assertTrue(math.isclose(row["mean_lookup_ns"] * row["throughput_ops_per_s"], 1e9, rel_tol=1e-12))

    @staticmethod
    def synthetic_rows(set_time=50, errors=0):
        return [
            {"size": 10000, "hit_rate": 0.5, "seed": seed, "method": method,
             "mean_lookup_ns": 100 if method == "list" else set_time,
             "build_ns": 10, "peak_python_bytes": 1024, "errors": errors}
            for seed in range(101, 131) for method in bench.METHODS
        ]

    def test_smoke_never_claims_hypothesis_confirmation(self):
        summary = bench.summarize(self.synthetic_rows(), default_config(), True)
        self.assertFalse(summary["analysis"]["eligible_for_primary_test"])
        self.assertIsNone(summary["analysis"]["p_value_one_sided"])

    def test_primary_test_separates_significance_and_guardrails(self):
        config = default_config()
        config["mode"] = "study"
        summary = bench.summarize(self.synthetic_rows(), config, True)
        self.assertEqual(summary["analysis"]["practical_decision"], "supports_H1_within_scope")
        self.assertAlmostEqual(summary["analysis"]["p_value_one_sided"], 2**-30)
        failed = bench.summarize(self.synthetic_rows(errors=1), config, True)
        self.assertFalse(failed["guardrails_pass"])
        self.assertEqual(failed["analysis"]["practical_decision"], "criteria_not_met")

    def test_ties_do_not_count_as_successes(self):
        config = default_config()
        config["mode"] = "study"
        config["hypothesis"]["minimum_relative_improvement"] = 0.5
        analysis = bench.summarize(self.synthetic_rows(), config, True)["analysis"]
        self.assertEqual(analysis["seeds_strictly_above_threshold"], 0)
        self.assertEqual(analysis["p_value_one_sided"], 1)
        self.assertEqual(analysis["statistical_decision"], "do_not_reject_H0")

    def test_incomplete_study_or_wrong_runtime_disables_inference(self):
        config = default_config()
        config["mode"] = "study"
        for rows, runtime in ((self.synthetic_rows()[:-2], True), (self.synthetic_rows(), False)):
            with self.subTest(runtime=runtime):
                analysis = bench.summarize(rows, config, runtime)["analysis"]
                self.assertFalse(analysis["eligible_for_primary_test"])


class PipelineTests(unittest.TestCase):
    def run_cli(self, config, directory, name="run"):
        config_path = Path(directory) / (name + ".json")
        config_path.write_text(json.dumps(config))
        output = Path(directory) / name
        command = [sys.executable, str(bench.ROOT / "src/benchmark.py"),
                   "--config", str(config_path), "--output", str(output)]
        result = subprocess.run(command, cwd=directory, text=True, capture_output=True, timeout=30)
        return result, output, command

    def test_cli_works_outside_repository_and_protects_previous_results(self):
        with tempfile.TemporaryDirectory() as directory:
            result, output, command = self.run_cli(default_config(), directory)
            self.assertEqual(result.returncode, 0, result.stderr)
            status = json.loads((output / "status.json").read_text())
            self.assertEqual(status["raw_rows"], 16)
            self.assertTrue(status["guardrails_pass"])
            with (output / "raw.csv").open() as stream:
                self.assertEqual(len(list(csv.DictReader(stream))), 16)
            before = (output / "raw.csv").read_bytes()
            rerun = subprocess.run(command, cwd=directory, capture_output=True, text=True)
            self.assertEqual(rerun.returncode, 1)
            self.assertEqual(before, (output / "raw.csv").read_bytes())

    def test_timeout_is_a_reported_failure_without_inference(self):
        config = default_config()
        config["worker_timeout_seconds"] = 0.000001
        with tempfile.TemporaryDirectory() as directory:
            result, output, _ = self.run_cli(config, directory)
            self.assertEqual(result.returncode, 3, result.stderr)
            self.assertEqual(json.loads((output / "status.json").read_text())["error"], "TimeoutExpired")
            self.assertFalse((output / "summary.json").exists())

    def test_memory_guardrail_returns_nonzero_exit_status(self):
        config = default_config()
        config["guardrails"]["max_peak_python_mib"] = 0.000001
        with tempfile.TemporaryDirectory() as directory:
            result, output, _ = self.run_cli(config, directory)
            self.assertEqual(result.returncode, 2, result.stderr)
            self.assertFalse(json.loads((output / "summary.json").read_text())["guardrails_pass"])


if __name__ == "__main__":
    unittest.main()
