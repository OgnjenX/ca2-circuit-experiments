"""Portable compact-evidence checks; never integrate a neuron or reopen primary gates."""
import argparse
import csv
import hashlib
import json
import math
import struct
from pathlib import Path
import subprocess
import sys

HERE=Path(__file__).resolve().parent
ASSAY=HERE.parent
ROOT=ASSAY.parents[1]
PREFIX=HERE/'004_prefix_diagnostic'
POSTHOC=HERE/'posthoc_biological_comparison'
VARIANTS=('dop853_loose','dop853_tight','rk4_float64_exact_coefficients',
          'rk4_float64_matched_float32_coefficients','rk4_float32_explicit_no_fma')


def require(condition,message):
    if not condition:
        raise ValueError(message)


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load(path):
    return json.loads(Path(path).read_text())


def git_bytes(commit,path):
    return subprocess.check_output(['git','show',f'{commit}:{path.relative_to(ROOT)}'],cwd=ROOT)


def ancestor(commit):
    subprocess.run(['git','merge-base','--is-ancestor',commit,'HEAD'],cwd=ROOT,check=True)


def finite(value):
    require(not isinstance(value,bool) and isinstance(value,(int,float)) and math.isfinite(value),
            'Nonfinite or nonnumeric compact telemetry')
    return value


def check_prefix(record,manifest,protocol,freeze):
    require(record['frozen_diagnostic_commit']==freeze,'Prefix diagnostic freeze differs')
    require(record['source_freeze_commit']==manifest['source_freeze_commit']==protocol['source_freeze_commit'],
            'Original source freeze differs')
    require(record['native_input_sha256']==manifest['native_sha256'],'Native input identity differs')
    require(record['window_ms']==protocol['window_ms']==[0,858.4875],'Prefix window differs')
    require(record['sample_count']==68680,'Prefix sample count differs')
    require(record['native_first_reset_end_ms']==protocol['native_first_reset_end_ms']==858.5,
            'Native first-reset end differs')
    require(abs(record['native_first_reset_detection_ms']-858.4875)<1e-10,'Native reset detection clock differs')
    require(record['controls']==[[1e-9,1e-10,.5],[1e-11,1e-12,.1]],'Reference controls differ')
    require(set(record['state_csv_sha256'])=={label+'.csv' for label in VARIANTS},'Saved variant coverage differs')
    for filename,sha in record['state_csv_sha256'].items():
        require(isinstance(sha,str) and len(sha)==64 and all(c in '0123456789abcdef' for c in sha),
                'Invalid state CSV digest')
        # Large state CSVs may remain in an ignored workspace; portable CI checks compact evidence.
        if (PREFIX/filename).exists():
            require(digest(PREFIX/filename)==sha,'Present state CSV changed')
    labels={'native',*VARIANTS}
    brackets=record['first_threshold_brackets']
    require(set(brackets)==labels,'First-threshold bracket coverage differs')
    for label,bracket in brackets.items():
        if bracket is None:
            continue
        lo,hi=map(finite,bracket['bracket_ms'])
        require(0<=lo<hi<=858.4875+1e-10 and abs(hi-lo-.0125)<1e-10,'Invalid threshold bracket')
        require(lo<=finite(bracket['linear_interpolation_ms'])<=hi,'Crossing estimate outside bracket')
    require(brackets['native'] is not None,'Native first-crossing bracket missing')
    common=min([858.4875]+[b['bracket_ms'][0] for b in brackets.values() if b is not None])
    require(abs(record['valid_comparison_end_ms']-common)<1e-10,'Common prethreshold end differs')
    expected_comparisons={f'native_vs_{v}' for v in VARIANTS}|{
        'dop853_tolerance_refinement','rk4_float64_exact_vs_dop853_tight',
        'rk4_float64_matched_vs_dop853_tight','rk4_coefficient_rounding','rk4_float32_operation_rounding'}
    require(set(record['comparisons'])==expected_comparisons,'Declared telemetry contrast coverage differs')
    for contrast,components in record['comparisons'].items():
        require(set(components)=={'voltage_mV','recovery_pA'},'Telemetry component coverage differs')
        for component in components.values():
            maximum=finite(component['max_abs']); rms=finite(component['rms'])
            endpoint=finite(component['signed_endpoint_difference'])
            require(0<=rms<=maximum+1e-12 and abs(endpoint)<=maximum+1e-12,'Telemetry magnitudes incoherent')
            require(component['first_exceedance_threshold']==1e-5,'Descriptive threshold changed')
            time=component['first_exceedance_time_ms']; difference=component['first_exceedance_signed_difference']
            if maximum<=1e-5:
                require(time is None and difference is None,'Manufactured threshold exceedance')
            else:
                require(time is not None and difference is not None,'Missing threshold exceedance')
                require(0<=finite(time)<=common+1e-10 and abs(time*80-round(time*80))<1e-7,
                        'First-exceedance time outside common sampled prefix')
                require(1e-5<abs(finite(difference))<=maximum+1e-12,'First-exceedance magnitude incoherent')
    reliable=all(c['max_abs']<=1e-7 for c in record['comparisons']['dop853_tolerance_refinement'].values())
    require(record['reference_reliable_for_drift_attribution'] is reliable,'Reference reliability flag differs')
    checkpoints=record['checkpoints']
    require(set(checkpoints)==labels,'Checkpoint variant coverage differs')
    for label,rows in checkpoints.items():
        require([r['time_ms'] for r in rows]==protocol['checkpoints_ms'],'Checkpoint times differ')
        for row in rows:
            finite(row['v_mV']); finite(row['u_pA'])
            require(row['within_common_prethreshold_prefix'] is (row['time_ms']<=common),
                    'Checkpoint common-threshold label differs')
    metadata=record['actual_native_metadata']
    sys.path.insert(0,str(ASSAY/'preparation'))
    from build_driver import check_metadata
    source=load(ASSAY/'revisions/002/preregistration_manifest.json')
    require(check_metadata(json.dumps(metadata),80,100,source['runtime_pins'])==metadata,
            'Prefix native metadata differs from original frozen identity')
    rounded=lambda value:struct.unpack('f',struct.pack('f',value))[0]
    expected_coefficients={'exact_inverse_C':1/metadata['parameters_float32']['C'],
                           'matched_float32_inverse_C':rounded(1/metadata['parameters_float32']['C']),
                           'exact_dt_ms':1/80,'matched_float32_dt_ms':rounded(1/80),
                           'exact_one_sixth':1/6,'matched_float32_one_sixth':rounded(1/6)}
    for name,value in expected_coefficients.items():
        require(record['coefficient_handling'][name]==value,f'Coefficient identity differs: {name}')
    for rows in checkpoints.values():
        require(rows[0]['v_mV']==-70 and rows[0]['u_pA']==metadata['initial_u_float32_pA'],
                'Prefix initial states differ')
    return reliable


def check_posthoc(numerical,protocol):
    require(numerical['passed'] is False,'Original primary numerical gate was reopened')
    records=numerical['records']
    grid=[(r['metadata']['steps_per_ms'],r['metadata']['step_current_pA']) for r in records]
    require(len(grid)==33 and set(grid)=={(s,i) for s in (20,40,80) for i in range(0,1001,100)},
            'Original retained native record grid incomplete')
    finest={r['metadata']['step_current_pA']:r for r in records if r['metadata']['steps_per_ms']==80}
    target=load(ASSAY/'revisions/002/target_data.json')
    sys.path.insert(0,str(ASSAY/'revisions/002'))
    from analyze import scoring_bounds
    expected=scoring_bounds({i:r['crossing_audit']['raw_counts']['pulse'] for i,r in finest.items()},target['rows'])
    for row in expected['rows']:
        audit=finest[row['current_pA']]['crossing_audit']
        row.update(whole_recording_count=audit['whole_trace_raw'],postpulse_count=audit['raw_counts']['post'])
    expected['primary_all_current_bounds']['interpretation']='POST-HOC conditional figure-reading bounds, not confidence intervals, restored primary scores or biological equivalence.'
    actual=load(POSTHOC/'comparison.json')
    require(actual['primary_numerical_pass'] is False and 'post-hoc' in actual['status'].lower()
            and 'exploratory' in actual['status'].lower(),'Exploratory scope or failed gate changed')
    require(actual['source_result_commit']==protocol['original_result_commit'],'Exploratory original result commit differs')
    require(actual['rows']==expected['rows'],'Exploratory ten-row counts/residual bounds differ')
    require(actual['exploratory_all_ten_conditional_bounds']==expected['primary_all_current_bounds'],
            'Exploratory conditional metrics differ')
    require(actual['exploratory_nine_visible_mean_summary']==expected['secondary_visible_mean_point_summary'],
            'Exploratory visible-mean metrics differ')
    require(actual['input_sha256']=={p.name:digest(p) for p in
            (ASSAY/'results/numerical_checks.json',ASSAY/'revisions/002/target_data.json')},
            'Exploratory input hashes differ')
    require(actual['frozen_100pA_interval_unchanged']==[0,1.2] and actual['rows'][0]['paper_mean_Hz'] is None
            and actual['rows'][0]['paper_mean_interval_Hz']==[0,1.2],'Hidden mean was imputed or interval replaced')
    with (POSTHOC/'comparison.csv').open() as stream:
        saved=list(csv.reader(stream))
    expected_csv=[['current_pA','native_pulse_count','paper_mean_Hz','paper_low_Hz','paper_high_Hz',
                   'native_minus_paper_low','native_minus_paper_high','visible_mean_difference','whole_recording_count']]
    for row in expected['rows']:
        values=[row['current_pA'],row['model_count_1s'],row['paper_mean_Hz'],*row['paper_mean_interval_Hz'],
                *row['residual_interval_Hz'],row['visible_mean_residual_Hz'],row['whole_recording_count']]
        expected_csv.append(['' if v is None else str(v) for v in values])
    require(saved==expected_csv,'Exploratory CSV differs from recomputed ten rows')


def main(allow_pending=False):
    numerical=load(ASSAY/'results/numerical_checks.json')
    require(numerical['passed'] is False,'Original numerical gate must remain failed')
    require(not any((ASSAY/'results'/name).exists() for name in ('comparison.json','comparison.csv','comparison.png')),
            'Original gated primary score files unexpectedly exist')
    needed=[PREFIX/'preregistration_manifest.json',PREFIX/'prefix_results.json',HERE/'evidence_manifest.json']
    missing=[str(p.relative_to(HERE)) for p in needed if not p.is_file()]
    if missing:
        if allow_pending:
            print(json.dumps({'addenda_verified':False,'original_primary_passed':False,'pending':missing},indent=2))
            return
        raise ValueError(f'Addendum evidence pending: {missing}')
    manifest=load(needed[0]); protocol=load(PREFIX/'protocol.json'); review=load(PREFIX/'review.json')
    record=load(needed[1]); freeze=record['frozen_diagnostic_commit']
    for commit in (freeze,protocol['source_freeze_commit'],protocol['original_result_commit']):
        ancestor(commit)
    for relative in set(manifest['sha256'])|{'addenda/004_prefix_diagnostic/preregistration_manifest.json'}:
        path=ASSAY/relative
        require(git_bytes(freeze,path)==path.read_bytes(),f'Prefix frozen file changed: {relative}')
        if relative in manifest['sha256']:
            require(digest(path)==manifest['sha256'][relative],f'Prefix manifest digest differs: {relative}')
    require(review['approved_prefix_diagnostic_execution'] is True,'Prefix independent review not approved')
    require(review['reviewed_prefix_py_sha256']==digest(PREFIX/'prefix.py'),'Reviewed prefix source changed')
    require(git_bytes(protocol['original_result_commit'],ASSAY/'results/numerical_checks.json')
            ==(ASSAY/'results/numerical_checks.json').read_bytes(),'Original numerical result changed')
    source_manifest=ASSAY/'revisions/002/preregistration_manifest.json'
    require(git_bytes(protocol['source_freeze_commit'],source_manifest)==source_manifest.read_bytes(),
            'Original source manifest changed')
    for relative,sha in load(source_manifest)['sha256'].items():
        require(digest(ASSAY/relative)==sha,f'Original source changed: {relative}')
    evidence=load(needed[2])
    required={'004_prefix_diagnostic/prefix_results.json',*[f'posthoc_biological_comparison/{name}' for name in
              ('comparison.json','comparison.csv','comparison.png','report.md')]}
    require(required<=set(evidence['sha256']),'Compact addendum evidence coverage incomplete')
    for relative,sha in evidence['sha256'].items():
        path=(HERE/relative).resolve()
        require(path.is_relative_to(HERE.resolve()),'Evidence path escapes addenda')
        require(digest(path)==sha,f'Addendum evidence changed: {relative}')
    for key,expected in [('frozen_diagnostic_commit',freeze),('source_freeze_commit',protocol['source_freeze_commit']),
                         ('original_result_commit',protocol['original_result_commit'])]:
        require(evidence[key]==expected,f'Addendum evidence commit pin differs: {key}')
    reliable=check_prefix(record,manifest,protocol,freeze)
    check_posthoc(numerical,protocol)
    print(json.dumps({'addenda_verified':True,'frozen_diagnostic_commit':freeze,
                      'original_primary_passed':False,'reference_reliable_for_drift_attribution':reliable,
                      'scope':'Compact post-hoc evidence consistency only; no new integration or restored primary gate.'},indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--allow-pending',action='store_true')
    main(parser.parse_args().allow_pending)
