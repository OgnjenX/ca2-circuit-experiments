"""Verify separately versioned evidence, full coverage and all setup gates without a GPU."""
import hashlib,json,sys
from pathlib import Path
import numpy as np
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];sys.path.insert(0,str(ROOT/'src'))
from ca2lab.benchmark import require_coverage,setup_pass
load=lambda name:json.loads((HERE/name).read_text())
sha=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()
frozen=load('frozen_configuration.json');protocol=load('protocol.json')
for name,digest in frozen['scientific_file_sha256'].items():
    if sha(ROOT/name)!=digest:raise ValueError('Frozen source changed: '+name)
manifest=load('evidence/manifest.json')
for name,record in manifest['files'].items():
    path=HERE/name
    if path.stat().st_size!=record['bytes'] or sha(path)!=record['sha256']:raise ValueError('Published artifact changed: '+name)
rows=load('evidence/run_measurements.json');configs=load('evidence/run_configurations.json');results=load('evidence/results.json');checks=load('evidence/numerical_checks.json')
expected={(release,s['selected']['active'],seed,freq,steps)
          for release in ['stp','static'] for s in frozen['calibration']['selections']
          for seed in protocol['evaluation_seeds']
          for steps,frequencies in [(protocol['nominal_substeps'],protocol['frequencies_Hz']),(protocol['precision_substeps'],protocol['primary_frequencies_Hz'])]
          for freq in frequencies}
key=lambda r:(r['release'],r['active'],r['seed'],r['frequency_Hz'],r['steps'])
require_coverage(rows,expected,key);lookup={key(r):r for r in rows}
for row in rows:
    cfg=configs[row['label']];wanted=(frozen['executable_sha256'] if row['release']=='stp' else frozen['build_record']['static_executable_sha256'])
    if cfg['scientific_file_sha256']!=frozen['scientific_file_sha256'] or cfg['executable_sha256']!=wanted:raise ValueError('Run scientific identity mismatch')
    if row['input_spikes']!=5*row['active']:raise ValueError('Input delivery count mismatch')
    np.testing.assert_allclose(np.mean(np.asarray(row['cell_ratios'],dtype=np.float32)),row['mean_ratios'][-1],rtol=0,atol=0)
expected_pairs={(r,a,s,f) for r,a,s,f,steps in expected if steps==protocol['precision_substeps']}
require_coverage(checks,expected_pairs,lambda r:(r['release'],r['active'],r['seed'],r['frequency_Hz']))
for check in checks:
    k=(check['release'],check['active'],check['seed'],check['frequency_Hz'])
    low=lookup[k+(protocol['nominal_substeps'],)];high=lookup[k+(protocol['precision_substeps'],)]
    ratio=abs(high['mean_ratios'][-1]-low['mean_ratios'][-1]);peak=float(np.max(np.abs(np.array(high['mean_peaks_mV'])-np.array(low['mean_peaks_mV']))))
    passed=(ratio<=protocol['numerical_gates']['max_ratio_absolute_difference'] and peak<=protocol['numerical_gates']['max_EPSP_peak_difference_mV'] and high['eligible']==low['eligible'] and high['spikes']==low['spikes'])
    if check['pass']!=passed:raise ValueError('Numerical gate mismatch')
for comparison in results['comparisons']:
    group=[r for r in rows if r['release']==comparison['release'] and r['active']==comparison['active_afferents'] and r['frequency_Hz']==comparison['frequency_Hz'] and r['steps']==protocol['nominal_substeps']]
    np.testing.assert_allclose(np.mean([r['mean_ratios'][-1] for r in group]),comparison['model_mean_ratio'],rtol=0,atol=1e-7)
    lower,upper=comparison['conservative_source_interval'];passed=all(r['eligible'] for r in group) and lower<=comparison['model_mean_ratio']<=upper
    if passed!=comparison['inside_compatibility_band']:raise ValueError('Band gate mismatch')
for release in ['stp','static']:
    for level in protocol['calibration_amplitudes_mV']:
        primary=[r for r in results['primary'] if r['release']==release and r['target_single_EPSP_mV']==level]
        passed=setup_pass(primary,protocol['primary_frequencies_Hz'],all(r['pass'] for r in checks if r['release']==release))
        if results['setup_level_passes'][release][str(level)]!=passed:raise ValueError('Setup gate mismatch')
validation=json.loads((ROOT/'simulators/carlsim4/validation/evidence/corrected.json').read_text())
names={f'silent-{n}' for n in [0,1,31,91,255]}|{f'components-stp{stp}-rise{rise}-order{order}' for stp in [False,True] for rise in [0,2] for order in [0,1,2]}|{'pure-static','reset-repeat'}
require_coverage(validation['results'],{(mode,name) for mode in ['cpu','gpu'] for name in names},lambda r:(r['mode'],r['case']))
if validation['spec_sha256']!=sha(ROOT/'simulators/carlsim4/validation/spec.json') or validation['oracle_sha256']!=sha(ROOT/'simulators/carlsim4/validation/oracle.py'):raise ValueError('Validation source identity mismatch')
if validation['library_sha256']!=frozen['build_record']['library_sha256']:raise ValueError('Validation library identity mismatch')
if not validation['passed'] or not all(r['pass_oracle'] for r in validation['results']):raise ValueError('Independent backend validation failed')
print(f'Verified {len(rows)} corrected runs, {len(checks)} numerical pairs, independent backend gates and complete setup coverage.')
print('Compact integrity does not replace raw-monitor reanalysis or biological validation.')

metadata=load('evidence/metadata_mapping.json')
if set(metadata['runs'])!=set(configs):raise ValueError('Metadata recovery is not one-to-one')
for row in rows:
    mapping=metadata['runs'][row['label']]
    base={k:v for k,v in row.items() if k!='release'}
    values_sha=hashlib.sha256(json.dumps(base,sort_keys=True).encode()).hexdigest()
    if mapping['release']!=row['release'] or mapping['configuration_sha256']!=row['configuration_sha256'] or mapping['unchanged_measurement_values_sha256']!=values_sha:raise ValueError('Metadata recovery changed measurements or assignment')
