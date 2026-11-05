"""Validate raw evidence, retain failures, and bootstrap independent seed units."""
from pathlib import Path
import hashlib
import json
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
GROUP = ['size', 'hit_rate', 'method']
SEED = 42
BOOTSTRAPS = 10000
METRICS = ['mean_lookup_ns', 'throughput_ops_per_s', 'build_ns']


def load_raw(root=ROOT):
    root = Path(root)
    raw = pd.read_json(root / 'data/raw/test_run.jsonl', lines=True)
    config = json.loads((root / 'data/provenance/config.snapshot.json').read_text())
    status = json.loads((root / 'data/provenance/status.json').read_text())
    if status['status'] not in ('completed', 'guardrail_failed'):
        raise ValueError('Incomplete collection: do not infer from partial data')
    validate_raw(raw, config)
    return raw, config, status


def validate_raw(raw, config):
    required = set(GROUP + ['phase', 'seed', 'pair', 'timestamp_utc', 'order_position',
        'lookups', 'batch_elapsed_ns', 'mean_lookup_ns', 'throughput_ops_per_s',
        'build_ns', 'peak_python_bytes', 'errors', 'workload_sha256'])
    if not required <= set(raw) or raw.empty or raw[list(required)].isna().any().any():
        raise ValueError('Empty data, missing fields, or null values')
    if set(raw.phase) != {'warmup', 'benchmark'} or set(raw.method) != {'list', 'set'}:
        raise ValueError('Unknown or missing phases/methods')
    identity = ['phase', 'size', 'hit_rate', 'seed', 'method', 'pair']
    if raw.duplicated(identity).any():
        raise ValueError('Duplicate observations')
    for column in ['size','seed','pair','order_position','lookups','batch_elapsed_ns',
                   'build_ns','peak_python_bytes','errors']:
        values = raw[column].to_numpy(dtype=float)
        if not np.isfinite(values).all() or (values < 0).any() or (values != np.floor(values)).any():
            raise ValueError('Invalid integer field: ' + column)
    for column in ['mean_lookup_ns','throughput_ops_per_s','batch_elapsed_ns','lookups']:
        if not np.isfinite(raw[column]).all() or (raw[column] <= 0).any():
            raise ValueError('Invalid timing field: ' + column)
    if not np.allclose(raw.mean_lookup_ns, raw.batch_elapsed_ns / raw.lookups, rtol=1e-10):
        raise ValueError('Latency identity failed')
    if not np.allclose(raw.mean_lookup_ns * raw.throughput_ops_per_s, 1e9, rtol=1e-10):
        raise ValueError('Throughput identity failed')
    pd.to_datetime(raw.timestamp_utc, utc=True, errors='raise', format='mixed')
    expected = {(n,h,s,m,p,i) for n in config['dataset_sizes'] for h in config['hit_rates']
        for s in config['seeds'] for m in ('list','set')
        for p,count in [('warmup',config['warmup_pairs']),('benchmark',config['measurement_pairs'])]
        for i in range(1,count+1)}
    actual = set(raw[['size','hit_rate','seed','method','phase','pair']].itertuples(index=False,name=None))
    if actual != expected:
        raise ValueError('Missing or unexpected conditions, seeds, methods, or repeats')
    if not raw.lookups.eq(config['queries_per_batch'] * config['batch_loops']).all():
        raise ValueError('Lookup count differs from collection protocol')
    if not raw.order_position.isin([1,2]).all():
        raise ValueError('Invalid method order')
    if not raw.groupby(['size','hit_rate','seed']).workload_sha256.nunique().eq(1).all():
        raise ValueError('Paired methods used different workloads')
    groups = raw.groupby(['size','hit_rate','seed','phase','pair'])
    if not groups.order_position.nunique().eq(2).all():
        raise ValueError('Each pair must contain first and second positions')
    measured = raw.loc[raw.phase.eq('benchmark')]
    first = measured.assign(first=measured.order_position.eq(1)).groupby(GROUP+['seed'])['first'].sum()
    if not first.eq(config['measurement_pairs']//2).all():
        raise ValueError('Unbalanced measurement order')


def filter_and_flag(raw):
    """Exclude only prespecified warmups; flag, never delete, timing outliers."""
    data = raw.loc[raw.phase.eq('benchmark')].copy()
    grouped = data.groupby(GROUP).mean_lookup_ns
    q1 = grouped.transform(lambda x: x.quantile(.25))
    q3 = grouped.transform(lambda x: x.quantile(.75))
    data['outlier_iqr'] = (data.mean_lookup_ns < q1 - 1.5*(q3-q1)) | (data.mean_lookup_ns > q3 + 1.5*(q3-q1))
    return data


def describe_seed_values(values, rng):
    values = np.asarray(values, dtype=float)
    if values.size < 2 or not np.isfinite(values).all():
        raise ValueError('At least two finite seed estimates are required')
    boot = np.median(rng.choice(values, size=(BOOTSTRAPS,len(values)), replace=True), axis=1)
    return dict(mean=float(values.mean()), sd=float(values.std(ddof=1)), median=float(np.median(values)),
        p25=float(np.percentile(values,25)), p75=float(np.percentile(values,75)),
        p95=float(np.percentile(values,95)), p99=float(np.percentile(values,99)),
        ci_low=float(np.percentile(boot,2.5)), ci_high=float(np.percentile(boot,97.5)))


def aggregate(data):
    # Eight within-seed observations are technical repeats, not independent n=240.
    seed_metrics = data.groupby(GROUP+['seed'],as_index=False,sort=True)[METRICS].median()
    rng = np.random.default_rng(SEED)
    entries = []
    for key, seeds in seed_metrics.groupby(GROUP,sort=True):
        rows = data.loc[(data[GROUP] == pd.Series(key,index=GROUP)).all(axis=1)]
        record = dict(zip(GROUP,key))
        record.update(seed_count=len(seeds), observations=len(rows),
            failed_observation_count=int(rows.errors.gt(0).sum()),
            failed_observation_rate=float(rows.errors.gt(0).mean()),
            error_indicator_sum=int(rows.errors.sum()), outlier_count=int(rows.outlier_iqr.sum()),
            max_peak_python_mib=float(rows.peak_python_bytes.max()/2**20))
        for metric in METRICS:
            record.update({metric+'_'+name:value for name,value in describe_seed_values(seeds[metric],rng).items()})
        entries.append(record)
    pivot = seed_metrics.pivot(index=['size','hit_rate','seed'],columns='method',values='mean_lookup_ns').reset_index()
    pivot.columns.name = None
    pivot['speedup'] = pivot['list'] / pivot['set']
    pivot['relative_improvement'] = 1 - pivot['set'] / pivot['list']
    paired = []
    for key, rows in pivot.groupby(['size','hit_rate'],sort=True):
        record = dict(zip(['size','hit_rate'],key))
        for metric in ['speedup','relative_improvement']:
            record.update({metric+'_'+name:value for name,value in describe_seed_values(rows[metric],rng).items()})
        paired.append(record)
    return pd.DataFrame(entries), seed_metrics, pivot, pd.DataFrame(paired)


def process(root=ROOT):
    root = Path(root)
    raw,config,status = load_raw(root)
    data = filter_and_flag(raw)
    summary,seeds,paired,paired_summary = aggregate(data)
    out = root / 'data/processed'; out.mkdir(parents=True,exist_ok=True)
    for name, frame in [('metrics_summary',summary),('seed_metrics',seeds),
                        ('paired_seed_metrics',paired),('paired_summary',paired_summary)]:
        frame.to_csv(out/(name+'.csv'),index=False,float_format='%.12g')
    audit = dict(raw_rows=len(raw),warmup_rows=int(raw.phase.eq('warmup').sum()),
        benchmark_rows=len(data),outlier_rows_retained=int(data.outlier_iqr.sum()),
        failed_benchmark_observations=int(data.errors.gt(0).sum()),
        failed_warmup_observations=int(raw.loc[raw.phase.eq('warmup'),'errors'].gt(0).sum()),
        max_peak_python_mib=float(raw.peak_python_bytes.max()/2**20),
        guardrails_pass=bool(raw.errors.eq(0).all() and raw.peak_python_bytes.le(config['guardrails']['max_peak_python_mib']*2**20).all()),
        bootstrap_seed=SEED,bootstrap_resamples=BOOTSTRAPS,
        statistical_unit='one seeded workload; eight technical repeats aggregated by median',
        raw_sha256=hashlib.sha256((root/'data/raw/test_run.jsonl').read_bytes()).hexdigest())
    (out/'analysis_audit.json').write_text(json.dumps(audit,indent=2)+'\n')
    return raw,data,summary,seeds,paired,paired_summary,audit


if __name__ == '__main__':
    *_, audit = process()
    print(json.dumps(audit,indent=2))
