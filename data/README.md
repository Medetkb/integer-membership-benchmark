# Synthetic data

`sample/keys.csv` has one header (`key`) and eight unique integer records. The integers identify no people or real entities. The file is authored for this demonstration and covered by the repository's MIT license.

The smoke benchmark reads the entire file. Queries are generated from its keys with exactly 50% hits. A hit is sampled from the keys; a miss is sampled above the largest key. Labels are assigned before either method is evaluated. Queries and labels are shuffled together using a fixed seed.

The study generates `1_000_000 + 2 * i` for `i` from 0 through `n - 1`, then shuffles the key order. Sizes and hit rates are in `configs/study.json`. This is synthetic workload generation, not a sampled human population or a public real-world dataset. No external download is required.

Keep only the micro-sample in version control. `data/raw/`, `data/generated/` and `data/processed/` are ignored. Per-worker hashes in `raw.csv` identify the exact keys, queries and labels; the pinned interpreter, generator code and seed reconstruct them.
