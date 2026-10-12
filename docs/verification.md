# Actual validation evidence

Validation date: **8 October 2026**. Environment: **CPython 3.12.14**, macOS 26.6.2, arm64. Full interpreter/build, operating-system and timer metadata are stored in `example-results/smoke-environment.json`.

## Automated checks

The standard-library test suite passed **13 tests**. It covers independently labelled hit/miss workloads, seed reproducibility, correctness on edge cases, balanced order, known sign-test probabilities, ties, inference eligibility, invalid input, operation from a different working directory, existing-output protection, timeout reporting and memory-guardrail failure. It deliberately does not assert a machine-specific speedup.

Command: `python -m unittest discover -s tests -v`. Captured output is in `example-results/tests.txt`.

## Sample execution

The committed eight-record sample was run with the unmodified `config.json`. The run completed with **one worker, 16 measured rows, zero errors and all guardrails passing**. The raw observations and summaries are included under `example-results/`.

| Method | Median batch-average lookup time in ns/query | Median construction time in ns | Peak traced Python allocation in MiB | Errors |
|---|---:|---:|---:|---:|
| list | 34.3146 | 125 | 0.008606 | 0 |
| set | 22.72915 | 209 | 0.009186 | 0 |

These values are actual local smoke observations, not target values. They measure a loop over eight keys, not the 10,000-key primary condition. The program correctly reported `statistical_decision: not_evaluated`; there is no confirmatory p-value. Timing precision and performance vary by host.

`smoke-raw.csv`, `smoke-summary.json`, `smoke-environment.json`, `smoke-status.json`, `smoke-config.snapshot.json` and `smoke-schedule.json` preserve the example. Its output location was redirected to a temporary validation directory; the experiment parameters were unchanged.

## Study generator development check

A reduced development run exercised all nine study size/hit-rate combinations: sizes 100, 1,000 and 10,000, with 0%, 50% and 100% hits. It used seed 101, one warmup pair, four measured pairs and two batch loops, producing **72 measured rows across nine workers**. All guardrails passed. Inference remained disabled because there was only one primary seed.

This was an implementation check, not the frozen 30-seed Week 7 study. The full primary research result is still to be collected under the final agreed protocol.

## Repository hygiene

Git ignore behavior was checked in an isolated temporary repository. Eight representative cache, environment, result, secret, binary-weight and log paths were excluded. Seven intended source, sample and documentation paths remained eligible for tracking. The final archive is assembled without caches, runtime result folders or Git metadata.

## Validation boundaries

- Docker is absent from the preparation environment. The Dockerfile has a verified image digest and runs tests during build, but **no successful container build or run is claimed**.
- GitHub publication is an author action still to be completed. The planned `medetkb` URL is not presented as a published repository.
- No earlier Task 1 topic or experimental result was available; the demonstration-topic assumption remains explicit.
