"""Check the published compact record without launching a simulator."""
import hashlib
import json
from pathlib import Path

import numpy as np

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
load=lambda name:json.loads((HERE/name).read_text())
sha=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()
frozen=load('frozen_configuration.json')
for name,digest in frozen['scientific_file_sha256'].items():
    if sha(ROOT/name)!=digest:raise ValueError('Frozen source changed: '+name)
manifest=load('evidence/manifest.json')
for name,record in manifest['files'].items():
    path=HERE/name
    if path.stat().st_size!=record['bytes'] or sha(path)!=record['sha256']:
        raise ValueError('Published artifact changed: '+name)
protocol=load('protocol.json')
results=load('evidence/results.json')
rows=load('evidence/run_measurements.json')
configs=load('evidence/run_configurations.json')
expected={(s['selected']['active'],seed,freq,steps)
          for s in frozen['calibration']['selections']
          for seed in protocol['evaluation_seeds']
          for steps,frequencies in [(20,protocol['frequencies_Hz']),(40,protocol['primary_frequencies_Hz'])]
          for freq in frequencies}
keys=[(r['active'],r['seed'],r['frequency_Hz'],r['steps']) for r in rows]
if len(keys)!=len(set(keys)) or set(keys)!=expected:raise ValueError('Coverage is incomplete')
for row in rows:
    cfg=configs[row['label']]
    if cfg['scientific_file_sha256']!=frozen['scientific_file_sha256']:
        raise ValueError('A run uses different scientific sources')
    if cfg['executable_sha256']!=frozen['executable_sha256']:
        raise ValueError('A run uses a different executable')
    if row['input_spikes']!=5*row['active']:
        raise ValueError('Input event count differs from pulse protocol')
    np.testing.assert_allclose(np.mean(row['cell_ratios']),row['mean_ratios'][-1],rtol=0,atol=3e-7)
for comparison in results['comparisons']:
    group=[r for r in rows if r['active']==comparison['active_afferents']
           and r['frequency_Hz']==comparison['frequency_Hz'] and r['steps']==20]
    np.testing.assert_allclose(np.mean([r['mean_ratios'][-1] for r in group]),comparison['model_mean_ratio'],rtol=0,atol=1e-7)
    lower,upper=comparison['conservative_source_interval']
    expected_pass=all(r['eligible'] for r in group) and lower<=comparison['model_mean_ratio']<=upper
    if expected_pass!=comparison['inside_compatibility_band']:raise ValueError('Incorrect band decision')
checks=load('evidence/numerical_checks.json')
if len(checks)!=30 or all(r['pass'] for r in checks)!=results['numerical_pass']:
    raise ValueError('Numerical summary inconsistency')
print(f'Verified {len(rows)} run summaries, {len(checks)} numerical pairs and {len(manifest["files"])} published artifacts.')
print('Compact-record integrity does not replace re-analysis of raw monitors or biological validation.')
