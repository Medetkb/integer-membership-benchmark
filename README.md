# List versus set membership for repeated integer lookup

Research Methods Task 2: a methodology passport and an executable measurement instrument.

## Authors

**Кожахмет Медетбек and Джазбаев Айбар** (pair submission). GitHub account: `medetkb`.

Repository: **https://github.com/medetkb/integer-membership-benchmark**

The URL above is the planned repository address; create it under `medetkb` before submission. This package has not published it. Record actual contributions in [CONTRIBUTIONS.md](CONTRIBUTIONS.md).

## Overview

This quantitative controlled experiment compares Python list membership, the baseline, with set membership for repeated integer queries. It measures query latency, construction time, throughput and incremental Python allocation peaks, while checking every query against known ground truth.

**Topic assumption:** the supplied `task2.docx` and the available prior conversation do not specify the Task 1 topic. This repository therefore uses a neutral demonstration topic. It does not claim continuity with an unknown Task 1. If the actual topic differs, revise the question, hypotheses, variables and code together before submission.

**Task 2 status:** the sample run validates the instrument. It does not confirm a research hypothesis. The Week 7 collection protocol is specified separately in [the methodology passport](docs/methodology-passport.md). Local validation evidence is in [docs/verification.md](docs/verification.md).

## Research question

For 10,000 unique integers and batches of 1,000 membership queries with exactly 50% hits, does replacing a prebuilt list with a prebuilt set reduce typical per-query time by more than 20%, while preserving exact correctness and keeping incremental traced allocations at or below 8 MiB on the same computer?

For seed `i`, let `L_list,i` and `L_set,i` be the medians of eight batch-average lookup times, and let `R_i = 1 - L_set,i / L_list,i`.

- **H0:** the population median of `R_i` under the specified workload and host is at most 0.20.
- **H1:** the population median of `R_i` is greater than 0.20.

The primary endpoint is the median relative improvement over 30 prespecified seeded workloads. A one-sided exact sign test uses `alpha = 0.05`; ties at the 20% threshold count as failures. Practical support additionally requires every guardrail to pass. Failing to reject H0 is not proof that the methods are equivalent.

## System requirements

- Reference interpreter: **CPython 3.12.14**, pinned in `.python-version` and in the Docker image.
- No third-party runtime or test packages. `requirements.txt` intentionally contains comments only; there are no unpinned library dependencies.
- Linux, macOS or Windows with Python available in a terminal. Commands below use `python`; on macOS/Linux use `python3` if that is your interpreter command.
- Alternatively, a running Docker installation. Its base image is pinned by multi-platform digest, including the operating-system userspace and Python libraries.
- A single local computer with at least 1 GiB available RAM and 100 MiB free disk is sufficient for this small benchmark. Close heavy background applications and keep the power mode constant for the study.

Python 3.12 or later can run the smoke check. If the exact version or implementation differs from the reference, the program records that fact and disables confirmatory inference. No packages, data or credentials are downloaded during benchmark execution.

## Quickstart guide

After extracting the archive, run these **three commands** from the directory containing `task2-research-methods`:

```bash
cd task2-research-methods
python -m unittest discover -s tests -v
python src/benchmark.py --config config.json
```

The last command reads all **8 sample records** in `data/sample/keys.csv`, builds 1,000 labelled queries, performs two warmup pairs and eight measured pairs, and writes **16 measurement rows** under `results/smoke/`. A successful run exits with code 0 and prints `COMPLETED` and `Hypothesis decision: not_evaluated`.

Each query batch is replayed ten times inside a measurement, giving 10,000 lookups per timed observation. Timings will differ across machines and runs. There is intentionally no fixed speed threshold in the smoke test.

For another run, preserve the previous evidence and choose a new directory:

```bash
python src/benchmark.py --config config.json --output results/smoke-02
```

No environment activation or `pip install` is needed. If your course workflow requires an environment, `python -m venv .venv` is sufficient; the empty `requirements.txt` needs no downloads.

### Docker alternative

From the repository root, these commands build the image, run the tests during the build and save a smoke run to a new host directory:

```bash
docker build -t integer-membership:task2 .
docker run --rm --network none -v "${PWD}/results/docker-smoke:/results" integer-membership:task2
```

These commands use Bash/Zsh syntax; PowerShell also expands `${PWD}`. Docker was not available in the preparation environment, so the build and container run are **provided but not locally executed**. The native Python path was executed. See [environment pinning](docs/environment.md) for the verified base-image source and exact digest. Repeat with a new output directory; existing results are never overwritten.

## Planned benchmarks

| Benchmark | Data source | Key count | Hit rate | Seeds | Measured pairs per seed | Purpose |
|---|---|---:|---:|---:|---:|---|
| Task 2 smoke | Committed CSV | 8 | 50% | 1 | 8 | Validate input, timing, metrics and output |
| Primary Week 7 condition | Deterministic generator | 10,000 | 50% | 30 | 8 | Test H0 versus H1 |
| Exploratory grid | Same generator | 100, 1,000, 10,000 | 0%, 50%, 100% | 30 per cell | 8 | Describe size and hit-rate sensitivity |

The full 3 by 3 grid includes the primary cell once: **270 worker processes and 4,320 raw measurement rows**, excluding warmups. Seeds are 101 through 130. Each cell uses 1,000 queries, ten batch loops, two warmup pairs, balanced randomized method order and a 120-second worker timeout. Large-list cells dominate runtime; total study time is machine dependent.

```bash
python src/benchmark.py --config configs/study.json
```

Run the study only after freezing the protocol and resolving the topic assumption. Do not combine measurements from different computers, interpreters or native/container environments into one primary test. Eight repeats within a seed are technical repeats, not eight independent experimental units. See the passport for the inference and exclusion rules.

## Repository structure

```text
task2-research-methods/
├── README.md
├── LICENSE
├── CONTRIBUTIONS.md
├── Dockerfile
├── requirements.txt
├── .python-version
├── .gitignore
├── .dockerignore
├── config.json
├── configs/
│   └── study.json
├── data/
│   ├── README.md
│   └── sample/
│       └── keys.csv
├── src/
│   ├── __init__.py
│   └── benchmark.py
├── tests/
│   └── test_benchmark.py
├── docs/
│   ├── methodology-passport.md
│   ├── environment.md
│   ├── verification.md
│   ├── rubric-map.md
│   ├── github-guide-ru.md
│   └── example-results/
│       ├── smoke-raw.csv
│       ├── smoke-summary.json
│       ├── smoke-environment.json
│       ├── smoke-status.json
│       ├── smoke-config.snapshot.json
│       ├── smoke-schedule.json
│       └── tests.txt
├── notebooks/
│   └── README.md
└── results/
    └── README.md
```

## Configuration and output

`config.json` is the smoke configuration; `configs/study.json` defines the planned experiment. JSON is explicitly allowed by the assignment and needs no YAML dependency. Data and configuration paths are relative to the repository root, independent of the current terminal directory. An absolute path is also accepted. `--output` selects a new output directory.

Each completed run saves:

| File | Contents |
|---|---|
| `raw.csv` | Every timed observation, seed, method order, workload hash, construction time, lookup time, throughput, traced peak and errors |
| `summary.json` | Scenario summaries, paired seed estimates, guardrail outcome and eligible primary sign test |
| `environment.json` | Python/build, OS/kernel, architecture, CPU count, clock, config hash and code/input hashes |
| `config.snapshot.json` | Exact configuration used |
| `schedule.json` | Actual order of workload cells and seeds |
| `status.json` | Completion/failure state, elapsed time and measurement count |

`mean_lookup_ns` is elapsed batch time divided by the number of lookups. It includes loop and result-accumulation overhead; it is not an individual-query p95. Throughput is the reciprocal transformation of the same timing, not an independent endpoint. Container construction is measured separately and excluded from the primary timer. `peak_python_bytes` is a separate untimed allocation measurement, **not total process RAM or RSS**. Error counts must be zero; allocation peaks must not exceed 8 MiB.

Exit codes: `0` successful run and guardrails; `1` invalid input/configuration or output-path issue; `2` completed run with a failed guardrail; `3` failed or timed-out worker. A timeout retains partial data, writes `status.json` and prevents statistical inference. A nonempty output directory causes an error instead of overwriting previous evidence.

## Reproducibility and limitations

Both methods execute the same Python `query in container` loop over the same labelled query sequence. Set construction is amortized outside the steady-state endpoint; its separate cost must be considered when discussing one-off lookups. Tracing is disabled for all timing measurements, and garbage collection is disabled only within those measurement regions. All workers receive `PYTHONHASHSEED=0`.

The set and list have different memory layouts. Cache effects, interpreter overhead, operating-system scheduling and CPU frequency can affect results. Seeds vary workloads but do not create independent physical computers. The proposed inference is conditional on the specified machine/protocol; this project cannot establish a universal speedup for databases, strings, adversarial hash collisions or production services.

The repository contains a small, labelled smoke example in `docs/example-results/`. Generated runs, caches, environments, binary datasets and model weights are ignored by Git. No large datasets, weights, private data or credentials are needed.

## GitHub and submission

Follow [the Russian GitHub guide](docs/github-guide-ru.md) to create the planned public repository, make meaningful commits and submit the passport plus the real repository link. The ZIP contains the source files, not fabricated commit history. For pair work, each person should commit and document their actual contribution.

## Citation and license

Suggested citation after publishing the repository:

> Кожахмет Медетбек and Джазбаев Айбар. (2026). *List versus set membership for repeated integer lookup*. Research Methods Task 2. https://github.com/medetkb/integer-membership-benchmark. Specify the commit used for the experiment.

The code, documentation and synthetic sample are released under the [MIT License](LICENSE). The original course handout is not redistributed in this repository.

## References

- [Python `time` documentation](https://docs.python.org/3.12/library/time.html#time.perf_counter_ns): timing API.
- [Python `tracemalloc` documentation](https://docs.python.org/3.12/library/tracemalloc.html): traced allocation scope.
- [Python `random` documentation](https://docs.python.org/3.12/library/random.html#notes-on-reproducibility): seeded workloads and version-specific reproducibility.
- [Official Python Docker image](https://hub.docker.com/layers/library/python/3.12.14-slim-bookworm/images/sha256-1aaa65a85fda306ffb8b910824d4e93bdce61e212c7e87168123ea3073b41a1a): pinned image provenance.
- [GitHub guide to publishing local code](https://docs.github.com/en/migrations/importing-source-code/using-the-command-line-to-import-source-code/adding-locally-hosted-code-to-github).
