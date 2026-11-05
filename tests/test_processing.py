"""Check exclusion, independence, completeness, pairing and guardrail preservation."""
import unittest
import numpy as np
import pandas as pd
from src import benchmark as bench
from src import process_data as proc
from unittest.mock import patch


def fixture():
    config = __import__('json').loads((bench.ROOT/'config.json').read_text())
    config.update(seeds=[101,102],queries_per_batch=10,batch_loops=1,warmup_pairs=1,measurement_pairs=4)
    records=[]
    for seed in config['seeds']:
        result=bench.run_worker(dict(config=config,size=8,hit_rate=.5,seed=seed,
            sample_keys=bench.load_sample(bench.ROOT/'data/sample/keys.csv')))
        records += result['warmup_rows']+result['rows']
    return pd.DataFrame(records),config


class AnalysisTests(unittest.TestCase):
    def test_warmup_is_logged_and_filtered_without_removing_failures(self):
        raw,config=fixture()
        proc.validate_raw(raw,config)
        raw.loc[raw.phase.eq('warmup'),'mean_lookup_ns']=1e12
        benchmark_index=raw.index[raw.phase.eq('benchmark')][0]
        raw.loc[benchmark_index,'errors']=1
        clean=proc.filter_and_flag(raw)
        self.assertEqual(len(clean),16)
        self.assertEqual(clean.errors.sum(),1)
        self.assertLess(clean.mean_lookup_ns.max(),1e12)
        summary,*_=proc.aggregate(clean)
        self.assertEqual(summary.failed_observation_count.sum(),1)
        self.assertTrue(summary.seed_count.eq(2).all())

    def test_missing_duplicate_and_mismatched_pairs_are_rejected(self):
        raw,config=fixture()
        bad_hash=raw.copy();bad_hash.loc[0,'workload_sha256']='0'*64
        bad_phase=raw.copy();bad_phase.loc[0,'phase']='unknown'
        for bad in [raw.iloc[1:],pd.concat([raw,raw.iloc[[0]]]),bad_hash,bad_phase]:
            with self.assertRaises(ValueError): proc.validate_raw(bad,config)

    def test_bootstrap_is_deterministic_and_uses_seeds(self):
        records=[]
        # An unequal number of technical repeats must not give one seed more weight.
        for seed,value,count in [(1,10,20),(2,30,4)]:
            for method,multiplier in [('list',1),('set',.5)]:
                for _ in range(count):
                    records.append(dict(size=8,hit_rate=.5,method=method,seed=seed,
                        mean_lookup_ns=value*multiplier,throughput_ops_per_s=1e9/(value*multiplier),
                        build_ns=2,errors=0,peak_python_bytes=100,outlier_iqr=False))
        df=pd.DataFrame(records)
        first=proc.aggregate(df);second=proc.aggregate(df)
        for a,b in zip(first,second):pd.testing.assert_frame_equal(a,b)
        self.assertEqual(first[0].set_index('method').loc['list','mean_lookup_ns_median'],20)
        self.assertTrue(first[2].speedup.eq(2).all())
        self.assertTrue(first[3].speedup_ci_low.eq(2).all())
        self.assertTrue(first[3].speedup_ci_high.eq(2).all())

    def test_flagged_spike_is_retained(self):
        raw,_=fixture();clean=proc.filter_and_flag(raw)
        clean['mean_lookup_ns']=10.0
        clean.loc[clean.index[0],'mean_lookup_ns']=1e8
        flagged=proc.filter_and_flag(clean)
        self.assertEqual(len(clean),len(flagged))
        self.assertTrue(flagged.loc[clean.index[0],'outlier_iqr'])

if __name__=='__main__':unittest.main()
