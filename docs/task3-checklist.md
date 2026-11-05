# Task 3 requirement checklist

| Requirement | Artifact and evidence |
|---|---|
| Raw JSONL and warmup filtering | `data/raw/test_run.jsonl`: 5,400 rows, including 1,080 warmup rows; notebook explicitly filters them. |
| Median, percentiles, bootstrap CI | `src/process_data.py`; 30 seed units per condition, 10,000 bootstrap resamples, seed 42. |
| Error guardrail | Zero failed evaluation or warmup observations; `data/processed/analysis_audit.json`. |
| Outlier handling | 212 IQR flags retained, not deleted. |
| Executed notebook | Eight code cells with sequential execution counts and saved outputs; no error outputs. |
| Plot units and uncertainty | ns/query and keys; log axes in Figure 1, 95% CI on both figures. |
| Accessible styling | Okabe-Ito blue/orange, different markers and line styles; separate distribution panels labelled. |
| PDF and PNG | Both figures exported to vector PDF and PNG at 300 DPI in `reports/figures/`. |
| Domain model | `docs/domain_model.md`: Mermaid C4 component model with M1-M3 metric points. |
| Modular processing | Separate `src/process_data.py` and `src/visualize.py`; notebook imports them. |
| Results table and figures | Root README contains median (p25-p75) table, discussion, plots and domain-model link. |
| Report | `reports/task3_report.md` and `reports/Task3_Report_EN.pdf`. |
| Git hygiene | Explicit evidence allowlist; runtime runs, checkpoints and environments excluded. |
| Release | Final tag `v3.0.1-task3` identifies the submission snapshot. |

## Validation

17 automated tests passed, covering Task 2 instrument invariants, worker failures/timeouts, no-overwrite behaviour, phase filtering, retention of errors/outliers, complete paired data, and deterministic seed-level bootstrap. The notebook ran in a fresh CPython 3.12.14 kernel. Scientific plots and the report were visually inspected. `data/provenance/environment.json` identifies the collection source hashes; `docs/task3-verification.json` records final artifact checks.

The original Week 7-9 teaching prompts are background material. This implementation follows the Task 3 deliverables without assuming that every example API/service workload is relevant to a local integer-lookup experiment. Week 10 Zotero/Overleaf work is outside Task 3's mandatory deliverables.
