"""Independent bounded numerical-record review; no integration or biological target.

For an extracted raw archive, pass --record <numerical_checks.json>,
--raw-root <directory containing workspaces/> and --output <new review.json>.
"""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
ASSAY = ROOT/'experiments/003_whitebirch_intrinsic'
PATH = ROOT/'data/workspaces/003-whitebirch-numerics-v2/numerical_checks.json'


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def counts(times):
    return tuple(sum(test(t) for t in times) for test in (
        lambda t: 0 <= t < 100, lambda t: 100 <= t < 1100, lambda t: 1100 <= t <= 1200))


def comparison(left, right, key, reset_u=True):
    a, b = left[key], right[key]
    aa, bb = [e['time_ms'] for e in a], [e['time_ms'] for e in b]
    stable = (len(a) == len(b) and counts(aa) == counts(bb)
              and all(x < y for x, y in zip(aa, aa[1:]))
              and all(x < y for x, y in zip(bb, bb[1:])))
    error = max((abs(x-y) for x, y in zip(aa, bb)), default=0) if len(a) == len(b) else None
    reset_stable = len(left['events']) == len(right['events'])
    reset_error = (max((abs(x['u_before']-y['u_before']) for x, y in zip(left['events'], right['events'])), default=0)
                   if reset_u and reset_stable else None)
    passed = bool(stable and error is not None and error < .05
                  and (not reset_u or (reset_stable and reset_error < .01)))
    return {'stable_counts_order_and_phases':stable, 'max_time_error_ms':error,
            'max_reset_u_before_error_pA':reset_error, 'pass':passed}


def review(record_path=PATH, raw_root=None, output=None):
    def raw_path(path):
        recorded = Path(path)
        if raw_root is None:
            return recorded
        parts = recorded.parts
        if 'workspaces' not in parts:
            raise ValueError(f'Recorded raw path lacks workspaces segment: {path}')
        return raw_root / Path(*parts[parts.index('workspaces'):])

    record = json.loads(record_path.read_text())
    assert record['frozen_commit'] == '233b068cb7e22663b9ce551806e4a4e573a63872'
    assert record['recovery_commit'] == '80049ab001aa6c4e444edb0bab018ded1897a8a9'
    assert record['serializer_recovery_only'] is True
    assert record['criteria'] == {'event_time_error_strictly_below_ms':.05,
                                 'same_grid_reset_u_error_strictly_below_pA':.01,
                                 'holding_voltage_error_at_most_mV':.002}
    for path, expected in record['raw_file_sha256'].items():
        assert digest(raw_path(path)) == expected, path
    rows = record['records']; assert len(rows) == 33
    by_grid = {(r['metadata']['steps_per_ms'],r['metadata']['step_current_pA']):r for r in rows}
    assert set(by_grid) == {(n,c) for n in (20,40,80) for c in range(0,1001,100)}
    details=[]
    for row in rows:
        m=row['metadata']; refs=[json.loads(raw_path(p).read_text()) for p in row['reference_raw_files']]
        for ref,controls in zip(refs,[(1e-9,1e-10,.5),(1e-11,1e-12,.1)]):
            assert ref['parameters']==m['parameters_float32']
            assert ref['step_current_pA']==m['step_current_pA']
            assert ref['substeps_per_ms']==m['steps_per_ms'] and ref['dt_ms']==1/m['steps_per_ms']
            assert (ref['rtol'],ref['atol'],ref['max_step_ms'])==controls
            assert ref['holding']=={'v_mV':-70.,'u_pA':m['initial_u_float32_pA'],'Ihold_pA':m['holding_float32_pA']}
            assert ref['hardcoded_Izh_ref']==1
            assert [s['time_ms'] for s in ref['boundary_states']]==[0.,100.,1100.,1200.]
            for event in ref['events']:
                last=(event['clock_index']+1)%m['steps_per_ms']==0
                assert event['v_before']>ref['parameters']['Vpeak'] and event['v_after']==ref['parameters']['Vmin']
                assert abs(event['u_after']-event['u_before']-ref['parameters']['d'])<1e-7
                assert event['refractory_counter_after']==(1 if last else 2)
        checks={
            'reference_refinement_crossings':comparison(refs[0],refs[1],'crossings'),
            'reference_refinement_detections':comparison(refs[0],refs[1],'events'),
            'same_grid_crossings':comparison(row,refs[1],'crossings'),
            'same_grid_detections':comparison(row,refs[1],'events')}
        for key,value in checks.items(): assert value==row[key], (m['steps_per_ms'],m['step_current_pA'],key)
        assert row['trace_rules_pass'] and not row['reset_rule_errors'] and row['holding_check_pass']
        assert row['reference_reset_audit']['pass']
        for label in ('crossing_audit','detection_audit'):
            assert not row[label]['ISIs_below_6ms']
            assert tuple(row[label]['raw_counts'][x] for x in ('pre','pulse','post'))==counts([e['time_ms'] for e in row['crossings' if label=='crossing_audit' else 'events']])
        details.append({'steps_per_ms':m['steps_per_ms'],'current_pA':m['step_current_pA'],**checks})
    refinements=[]
    for current in range(0,1001,100):
        for coarse,fine in ((20,40),(40,80),(20,80)):
            a,b=by_grid[coarse,current],by_grid[fine,current]
            crossings=comparison(a,b,'crossings',False); detections=comparison(a,b,'events',False)
            refinements.append({'current_pA':current,'steps_per_ms':[coarse,fine],'crossings':crossings,
                                'detections':detections,'pass':crossings['pass'] and detections['pass']})
    assert refinements==record['production_timestep_refinements']
    primary=all(r['same_grid_crossings']['pass'] and r['same_grid_detections']['pass'] for r in rows) and all(r['pass'] for r in refinements)
    assert primary is record['passed']
    diagpath=record_path.parent/'immediate_diagnostic.json'; assert digest(diagpath)==record['immediate_diagnostic_sha256']
    diag=json.loads(diagpath.read_text());assert diag['passed'] and len(diag['records'])==11
    for path,expected in diag['rawhashes'].items(): assert digest(raw_path(path))==expected
    for d in diag['records']:
        refs=[json.loads(raw_path(p).read_text()) for p in d['rawpaths']]
        assert comparison(refs[0],refs[1],'events')==d['refinement']
        assert d['refinement_pass']
        assert all(abs(e['v_before']-refs[1]['parameters']['Vpeak'])<1e-7 and e['v_after']==refs[1]['parameters']['Vmin']
                   and abs(e['u_after']-e['u_before']-refs[1]['parameters']['d'])<1e-9 for e in refs[1]['events'])
    post_currents=sorted({r['metadata']['step_current_pA'] for r in rows if r['crossing_audit']['raw_counts']['post']})
    pulse_stable=all(len({by_grid[n,c]['crossing_audit']['raw_counts']['pulse'] for n in (20,40,80)})==1 for c in range(0,1001,100))
    result={'kind':'Independent bounded final numerical review','scientific_freeze':record['frozen_commit'],
            'serialization_recovery_freeze':record['recovery_commit'],'numerical_record_sha256':digest(record_path),
            'auditor_source':'experiments/003_whitebirch_intrinsic/results/audit_numerical_record.py','auditor_sha256':digest(__file__),
            'native_and_clock_reference_hashes_verified':len(record['raw_file_sha256']),
            'same_grid_crossing_failures':sum(not r['same_grid_crossings']['pass'] for r in rows),
            'same_grid_detection_failures':sum(not r['same_grid_detections']['pass'] for r in rows),
            'same_grid_crossing_time_failures':sum(r['same_grid_crossings']['max_time_error_ms'] is None or r['same_grid_crossings']['max_time_error_ms'] >= .05 for r in rows),
            'same_grid_detection_time_failures':sum(r['same_grid_detections']['max_time_error_ms'] is None or r['same_grid_detections']['max_time_error_ms'] >= .05 for r in rows),
            'same_grid_pre_reset_u_failures':sum(r['same_grid_detections']['max_reset_u_before_error_pA'] is None or r['same_grid_detections']['max_reset_u_before_error_pA'] >= .01 for r in rows),
            'production_timestep_failed_comparisons':sum(not r['pass'] for r in refinements),
            'production_timestep_crossing_time_failures':sum(r['crossings']['max_time_error_ms'] is None or r['crossings']['max_time_error_ms'] >= .05 for r in refinements),
            'production_timestep_detection_time_failures':sum(r['detections']['max_time_error_ms'] is None or r['detections']['max_time_error_ms'] >= .05 for r in refinements),
            'max_cross_grid_crossing_difference_ms':max(r['crossings']['max_time_error_ms'] for r in refinements),
            'max_cross_grid_detection_difference_ms':max(r['detections']['max_time_error_ms'] for r in refinements),
            'all33_structural_and_reference_reset_refinement_checks_pass':True,'pulse_counts_stable_all3_grids':pulse_stable,
            'currents_with_postpulse_crossings_pA':post_currents,'no_ISI_below6ms':True,
            'comparability_unresolved':record['comparability_unresolved'],'primary_numerical_pass':primary,
            'immediate_diagnostic_pass':diag['passed'],'independent_same_grid_comparisons':details,
            'interpretation':'Primary fails frozen event-time/reset-recovery numerical gates. Stable counts and structural fidelity do not waive those failures. Immediate diagnostic passes its own numerical gates but cannot replace primary or support primary biological scoring.',
            'limits':['No biological target values or biological score inspected.','CSV structural evidence comes from prior independent runtime audit; this audit independently recomputes comparison metrics from recorded events and pinned raw references, without integrating any neuron.','Detector compatibility remains unresolved because recording-wide versus pulse counts include postpulse events.']}
    (output or ASSAY/'results/numerical_review.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ('independent_same_grid_comparisons','limits')},indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--record',type=Path,default=PATH)
    parser.add_argument('--raw-root',type=Path)
    parser.add_argument('--output',type=Path)
    args=parser.parse_args()
    if args.output is not None and args.output.exists():
        parser.error('--output must name a fresh user file')
    review(args.record.resolve(),args.raw_root.resolve() if args.raw_root else None,
           args.output.resolve() if args.output else None)
