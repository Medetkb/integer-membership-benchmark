# Data evidence

`raw/test_run.jsonl` is the complete small Task 3 measurement log collected on 5 November 2026: 1,080 warmup and 4,320 evaluation observations. The total file is about 2 MiB. Extra raw files are ignored by Git.

`provenance/` preserves the collection environment, source hashes, exact configuration, worker schedule, completion status and original instrument summary. `host_hardware.json` states the limitations of desktop environment control. Analysis package versions are recorded separately from the standard-library measurement runtime.

`processed/metrics_summary.csv` contains 18 condition/method summaries based on 30 seed medians each. `seed_metrics.csv` preserves the 540 seed/method estimates. `paired_seed_metrics.csv` and `paired_summary.csv` hold within-seed list/set ratios and relative reductions. `analysis_audit.json` records phase exclusion, guardrails, retained outliers and the raw-file hash.

The generated integer workloads contain no personal data. All raw evaluation records, including the 212 IQR flags, remain available. Error fields combine a batch-result mismatch indicator with the separate element-wise mismatch count; the reported rate is a failed-observation rate, not a per-query error probability.

`sample/keys.csv` remains the original small Task 2 smoke dataset. Do not combine smoke runs or earlier descriptive runs with the submitted Task 3 study.
