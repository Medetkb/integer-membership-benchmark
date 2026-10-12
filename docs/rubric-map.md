# Task 2 requirements and evidence

This map follows the supplied `task2.docx`. It records coverage, not a promised grade.

| Rubric area | Points available | Evidence in this package | Action before submission |
|---|---:|---|---|
| Methodology passport | 30 | `docs/methodology-passport.md`: project, type, testable H0/H1, variable matrix, primary/guardrail metrics and fair baseline | Confirm the demonstration topic and verify the published repository URL |
| Reproducibility and executable pipeline | 30 | `Dockerfile`, `.python-version`, `requirements.txt`, `config.json`, `configs/study.json`, `src/benchmark.py`, sample and tests | Run the Quickstart on the authors' computer; Docker build is supplied but not locally validated |
| English README | 20 | Title, Authors, Overview, Research Question, requirements, tree, benchmark table, three-command Quickstart, citation/license | Check the real public link |
| Repository hygiene and workflow | 20 | `.gitignore`, `.dockerignore`, separate folders, small synthetic data, labelled smoke evidence, `CONTRIBUTIONS.md` | Create actual informative commits from both contributors and publish them |

The assignment permits PDF or Markdown for the passport and JSON or YAML for configuration. This project uses both PDF and Markdown deliverables, and JSON configuration. The PDF is supplied separately for LMS; the source repository keeps the Markdown card.

Exact pins are achieved without adding unnecessary packages: the Python runtime is fixed to 3.12.14, the third-party dependency set is empty, and the optional Docker userspace is pinned by digest.

The public GitHub link and real contribution history cannot be provided by merely extracting a ZIP. The included guide explains those final author actions. The Task 1 connection remains an explicit assumption until checked by the authors.
