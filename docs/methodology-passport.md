# Methodology Passport Card

## Project information

- **Title:** List versus set membership for repeated integer lookup
- **Course deliverable:** Research Methods Task 2, Weeks 5 and 6
- **Authors:** Кожахмет Медетбек and Джазбаев Айбар
- **Work format:** Pair submission
- **GitHub account:** `medetkb`
- **Public repository:** https://github.com/medetkb/integer-membership-benchmark
**Document date:** 8 October 2026

**Publication status:** this project is published in the public repository above on the `main` branch. The benchmark examples in this package are smoke-validation evidence, not confirmatory study results.

**Topic assumption:** neither the supplied `task2.docx` nor the available prior conversation identifies the Task 1 research topic. This submission therefore uses integer-membership benchmarking as a neutral demonstration topic. It must not be represented as the actual Task 1 topic unless the authors verify that connection. If Task 1 was different, revise the methodology and instrument together.

## Research purpose and type

The study asks whether using a prebuilt Python set instead of a prebuilt list offers a practically meaningful reduction in repeated integer-lookup time at a specified workload, without correctness errors or excessive incremental allocations.

This is a **quantitative controlled computational experiment**. The investigator varies the membership data structure, collection size and proportion of successful queries, and records numerical time, throughput, allocation and correctness measurements. The same workload is evaluated by both methods, forming a paired comparison. Interviews, surveys and qualitative coding are unnecessary for this question.

The primary scope is steady-state lookup after construction, not end-to-end data ingestion or a one-off search. Construction time is recorded separately so that the cost of creating a set remains visible.

## Research question and hypotheses

**Research question:** for 10,000 unique integer keys and 1,000-query batches containing exactly 50% hits, does set membership reduce typical per-query time by more than 20% relative to list membership, while returning exactly correct results and keeping incremental traced Python allocations at or below 8 MiB on one fixed computer?

For each workload seed `i`, define `L_list,i` and `L_set,i` as the medians of eight measured batch-average lookup times, in nanoseconds per query. A measurement replays the same 1,000-query batch ten times. Define the paired relative improvement:

```text
R_i = 1 - L_set,i / L_list,i
theta = median of R_i over the specified seeded-workload population
```

- **Null hypothesis H0:** `theta <= 0.20`.
- **Alternative hypothesis H1:** `theta > 0.20`.

The 20% threshold is an a priori educational definition of practical relevance, not a threshold estimated from the smoke results. The alternative is directional and empirically testable. The claim is conditional on the selected machine, interpreter and workload-generation protocol.

## Variable matrix

| Role | Variable | Operational definition and levels |
|---|---|---|
| Independent | Membership structure | Native Python `list` (baseline) versus `set`; the same `query in container` loop is used |
| Independent | Collection size | Study: 100, 1,000 and 10,000 unique integers; smoke: 8 committed sample records |
| Independent | Query hit rate | Study: exactly 0%, 50% and 100%; the primary cell is 10,000 keys and 50% hits |
| Dependent | Lookup time | Batch elapsed nanoseconds divided by 10,000 lookups; median over eight technical repeats per method and seed |
| Dependent | Construction time and throughput | Separate construction timer in nanoseconds; lookups divided by elapsed seconds |
| Dependent | Allocation peak and errors | Peak additional traced Python bytes in an untimed pass; mismatches against generated Boolean labels |
| Controlled | Runtime and system | CPython 3.12.14; same physical computer, native/container choice, architecture, OS/kernel, power mode and background-load policy |
| Controlled | Inputs within each pair | Identical keys, order, queries, labels and seed; no file I/O or workload generation inside timing |
| Controlled | Measurement procedure | 1,000 queries, ten batch loops, two warmup pairs, eight measured pairs, tracing off and garbage collection off during timed regions |
| Blocking and scheduling | Seed and method order | Seeds 101-130 define paired workload blocks; fresh process per block/cell; balanced randomized method order and fixed randomized cell schedule |

The seed is a blocking variable, not the treatment. Hardware must be fixed within the full run; `environment.json` records available platform details and the authors should add CPU model, installed RAM and power mode to the run notes. A pinned container fixes userspace, not the host CPU or kernel.

## Metrics and fair baseline

**Primary metric:** the median paired relative reduction `R_i` across 30 seeds in the primary condition. Lower raw lookup time is better; larger `R_i` is better. A raw observation is a batch average, not a single-query percentile.

**Secondary metrics:** per-method median lookup time, speedup `L_list,i / L_set,i`, throughput in operations per second and construction time. Throughput is derived from the same timing and is not independent evidence. The exploratory size/hit-rate cells describe sensitivity; they do not generate additional confirmatory tests.

| Guardrail | Prespecified requirement | Measurement and failure handling |
|---|---|---|
| Correctness | Zero errors for both methods | Every query is checked against its known label outside timing; timed hit totals are checked too |
| Incremental Python allocations | At most 8 MiB for each method in every tested cell | Separate `tracemalloc` pass measures construction plus one Boolean output vector; preexisting keys and queries are excluded |
| Completion | Every worker finishes within 120 seconds | The parent enforces a process timeout; failed runs keep partial data and produce no hypothesis decision |

The 8 MiB bound is a chosen budget for this small demonstration. It is not a total-RAM limit: traced Python allocations exclude operating-system memory, interpreter baseline and inputs allocated before tracing. Timing is never collected while tracing is active.

**Baseline:** native Python list membership on the exact same integer collection and queries. The comparison does not replace the baseline's membership operation with an artificially slow hand-written search. Each method receives the same warmups and number of timed operations. List and set construction are both excluded from the primary lookup timer and reported separately. The method first in each pair is balanced across the eight repeats to reduce order bias.

## Data and collection protocol

All data are synthetic and contain no personal information. `data/sample/keys.csv` has a header and eight records. It is sufficient to test reading, workload generation, correctness checks, timing and file output.

For the study, the generator creates `1_000_000 + 2*i` for `i = 0 ... n-1`, then shuffles the key order. Hits are sampled from those keys; misses are larger than the maximum key. Labels are assigned during generation rather than inferred from either tested method. The query/label pairs are shuffled together. Randomness is seeded, and each workload receives a SHA-256 hash.

1. Confirm the topic, create the public repository, review the protocol and freeze the code/configuration in an identifiable commit before Week 7 collection.
2. Run the automated checks and sample benchmark. Require exit code 0, zero errors and all guardrails passing. A smoke run has one seed and cannot test H0.
3. Record the host CPU model, RAM and power mode. Use one machine and one environment for the full run; close heavy applications and keep it on stable power.
4. Run `configs/study.json`. The fixed schedule shuffles all nine size/hit-rate cells and 30 seeds. Each of the 270 cells/seed combinations runs in a fresh process.
5. For each worker, measure memory and correctness outside timing, run two warmup pairs, then eight measured pairs. Both structures use the same query sequence. Each method is first in exactly four measured pairs.
6. Retain raw observations, input/code/config hashes, the exact configuration, schedule and environment record. Preserve all completed observations; do not remove slow values after inspecting the results.
7. If a worker times out or fails, retain the failed run and investigate. Document any fix and rerun the full collection into a new directory. Do not silently replace selected slow workers.

| Run | Workload | Workload blocks | Raw measured rows | Interpretation |
|---|---|---:|---:|---|
| Task 2 smoke | 8 keys, 50% hits | 1 | 16 | Instrument validation only |
| Primary Week 7 cell | 10,000 keys, 50% hits | 30 | 480 | One planned hypothesis test |
| Complete Week 7 grid | 3 sizes by 3 hit rates, including primary cell | 270 cell/seed blocks | 4,320 | Primary test plus descriptive sensitivity analysis |

Seeds are pseudo-random workload blocks within one host, not independent machines. Repeats within a block are technical repeats; treating all 480 primary timing rows as independent observations would overstate the sample size.

## Analysis and decision rule

For the primary cell, compute the per-seed medians and `R_i`. Count `K`, the number of the 30 reductions that are strictly greater than 0.20. Under the null, the probability of exceeding that threshold is at most one half. Use the conservative one-sided exact sign-test tail:

```text
p = sum(comb(30, k) for k = K ... 30) / 2**30
```

Ties count as failures. Reject H0 only when `p < 0.05`; with 30 blocks, at least 20 strict successes are required. Declare practical support for H1 only if H0 is rejected and all study guardrails pass. Otherwise report that the prespecified criteria were not met. Do not equate failure to reject H0 with proof of no effect.

The instrument implements this rule only for a completed study with exactly 30 primary seeds and the reference runtime. It disables inference for the smoke check, incomplete primary data and a different Python implementation/version. The full planned study has not been carried out as part of this Task 2 package; no confirmatory p-value or conclusion is claimed here.

## Reproducibility and repository deliverables

The repository includes an English academic README, a Dockerfile pinned by image digest, CPython version pin, an explicitly empty third-party dependency set, JSON configurations, executable benchmark, eight-row sample, tests, MIT license and Python-specific ignore rules. Data, code, documentation, optional notebooks and generated outputs have separate directories.

The three-command native Quickstart changes into the project, runs tests and runs the smoke benchmark. A completed run writes `raw.csv`, `summary.json`, `environment.json`, `config.snapshot.json`, `schedule.json` and `status.json`. The program refuses to overwrite a nonempty output directory. A small labelled example is kept under `docs/example-results/`; bulk results and technical caches are excluded from Git.

Native execution was verified on CPython 3.12.14, macOS arm64. The local test suite contains 13 checks. Docker was not available in the preparation environment, so container build success is not asserted. The authors should execute the Docker Quickstart if using it for their submission. Detailed, actual validation evidence is in `docs/verification.md`.

## Validity limits and ethics

Balanced order, paired workloads, warmups and fresh worker processes reduce some measurement biases. They do not eliminate cache effects, CPU frequency changes, system scheduling or dependence across runs on the same machine. For very fast set operations, loop/timer overhead and noise may occupy a noticeable fraction of measured time; report the clock resolution and batch durations rather than interpreting nanosecond units as nanosecond accuracy.

The workload uses unique integers and an explicit 50% primary hit rate. Results need not transfer to strings, custom objects, duplicated datasets, hash-collision attacks, concurrent services or real databases. Excluding construction addresses repeated lookup only; it cannot justify set conversion for a single query. The 30-block design is a feasible course plan, not a formal power guarantee.

The sample is synthetic and requires no human-subject recruitment, consent or external dataset license. Code, documentation and synthetic data use MIT. The package was prepared with AI assistance; both authors should review it, reproduce the run and record their own actual contributions in accordance with course requirements.

## Sources

1. Supplied course handout `task2.docx`, Task 2 requirements and evaluation rubric.
2. [Python timing API](https://docs.python.org/3.12/library/time.html#time.perf_counter_ns).
3. [Python allocation tracing](https://docs.python.org/3.12/library/tracemalloc.html).
4. [Seeded random generation and reproducibility](https://docs.python.org/3.12/library/random.html#notes-on-reproducibility).
5. [Official Python container image and digest](https://hub.docker.com/layers/library/python/3.12.14-slim-bookworm/images/sha256-1aaa65a85fda306ffb8b910824d4e93bdce61e212c7e87168123ea3073b41a1a).

The sign-test formula and decision rule are stated in full above and implemented using Python's exact integer binomial coefficients; no external statistics package is required.
