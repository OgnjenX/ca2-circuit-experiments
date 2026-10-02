"""Independent saved-state audit of prefix result; never integrates a neuron."""
import csv
import hashlib
import json
from pathlib import Path
import numpy as np

ROOT=Path(__file__).resolve().parents[4]
HERE=Path(__file__).resolve().parent
RAW=ROOT/'data/workspaces/003-whitebirch-prefix-diagnostic-v1'
NATIVE=ROOT/'data/workspaces/003-whitebirch-gpu-pre-freeze-v7/traces/rk80_step100.csv'


def digest(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load(path):
    with Path(path).open() as stream:
        rows=list(csv.reader(stream))
    return np.array([[float(v) for v in row] for row in rows[1:]])


def metrics(times,left,right):
    delta=left-right;result={}
    for column,name in enumerate(('voltage_mV','recovery_pA')):
        values=delta[:,column];exceed=np.nonzero(abs(values)>1e-5)[0]
        j=int(exceed[0]) if len(exceed) else None
        result[name]={'max_abs':float(max(abs(values))),'rms':float(np.sqrt(np.dot(values,values)/len(values))),
                     'signed_endpoint_difference':float(values[-1]),'first_exceedance_threshold':1e-5,
                     'first_exceedance_time_ms':float(times[j]) if j is not None else None,
                     'first_exceedance_signed_difference':float(values[j]) if j is not None else None}
    return result


def close(actual,expected):
    if isinstance(actual,dict):
        assert set(actual)==set(expected)
        for key in actual:close(actual[key],expected[key])
    elif actual is None:assert expected is None
    else:assert abs(actual-expected)<=1e-12+abs(expected)*2e-14,(actual,expected)


def review():
    result=json.loads((HERE/'prefix_results.json').read_text())
    assert result==json.loads((RAW/'prefix_results.json').read_text())
    assert result['frozen_diagnostic_commit']=='bff3d5ffd1e08ac46dbea3b95e9cade94f9f99bc'
    manifest=json.loads((HERE/'preregistration_manifest.json').read_text())
    for name,sha in manifest['sha256'].items():assert digest(ROOT/'experiments/003_whitebirch_intrinsic'/name)==sha
    for name,sha in result['native_input_sha256'].items():assert digest(NATIVE.parent/name)==sha
    states={};times=None
    for name,sha in result['state_csv_sha256'].items():
        path=RAW/name;assert digest(path)==sha
        data=load(path);assert data.shape==(68680,3) and np.isfinite(data).all()
        if times is None:times=data[:,0]
        else:assert np.array_equal(times,data[:,0])
        states[path.stem]=data[:,1:]
    native_full=load(NATIVE);assert np.array_equal(times,native_full[:68680,0])
    states['native']=native_full[:68680,1:3]
    assert not np.any(native_full[:68680,3:])
    assert native_full[68680,0]==858.5 and native_full[68680,4]==1
    peak=result['actual_native_metadata']['parameters_float32']['Vpeak'];brackets={}
    for label,values in states.items():
        crossings=[j for j in range(len(times)-1) if values[j,0]<=peak<values[j+1,0]]
        if crossings:
            j=crossings[0];f=(peak-values[j,0])/(values[j+1,0]-values[j,0]);bracket={'bracket_ms':[float(times[j]),float(times[j+1])],
                'linear_interpolation_ms':float(times[j]+f*(times[j+1]-times[j]))}
        else:bracket=None
        brackets[label]=bracket
        assert bracket==result['first_threshold_brackets'][label]
    common=min([858.4875]+[b['bracket_ms'][0] for b in brackets.values() if b]);assert common==result['valid_comparison_end_ms']
    mask=times<=common;assert all(np.all(values[mask,0]<peak) for values in states.values())
    pairs={f'native_vs_{label}':('native',label) for label in states if label!='native'}
    pairs.update(dop853_tolerance_refinement=('dop853_loose','dop853_tight'),
                 rk4_float64_exact_vs_dop853_tight=('rk4_float64_exact_coefficients','dop853_tight'),
                 rk4_float64_matched_vs_dop853_tight=('rk4_float64_matched_float32_coefficients','dop853_tight'),
                 rk4_coefficient_rounding=('rk4_float64_exact_coefficients','rk4_float64_matched_float32_coefficients'),
                 rk4_float32_operation_rounding=('rk4_float32_explicit_no_fma','rk4_float64_matched_float32_coefficients'))
    independently={name:metrics(times[mask],states[a][mask],states[b][mask]) for name,(a,b) in pairs.items()}
    close(independently,result['comparisons'])
    for label,rows in result['checkpoints'].items():
        for row in rows:
            j=round(row['time_ms']*80)
            assert row['v_mV']==states[label][j,0] and row['u_pA']==states[label][j,1]
            assert row['within_common_prethreshold_prefix']==(row['time_ms']<=common)
    reliable=all(x['max_abs']<=1e-7 for x in independently['dop853_tolerance_refinement'].values())
    assert reliable is result['reference_reliable_for_drift_attribution']
    key=lambda name,component:independently[name][component]['max_abs']
    report={'review_kind':'Independent raw-state prefix diagnostic result review','frozen_diagnostic_commit':result['frozen_diagnostic_commit'],
            'result_sha256':digest(HERE/'prefix_results.json'),'auditor_sha256':digest(__file__),
            'five_state_csv_and_four_native_hashes_verified':True,'all68680_native_and_method_times_match':True,
            'all10_comparison_metrics_independently_recomputed':True,'all_checkpoint_and_crossing_bracket_records_verified':True,
            'common_prethreshold_end_ms':common,'every_common_prefix_voltage_strictly_below_Vpeak':True,
            'DOP_reference_refinement_reliable':reliable,
            'standard_float64_RK4_vs_tight_DOP_max_voltage_mV':key('rk4_float64_exact_vs_dop853_tight','voltage_mV'),
            'matched_float64_RK4_vs_tight_DOP_max_voltage_mV':key('rk4_float64_matched_vs_dop853_tight','voltage_mV'),
            'native_vs_tight_DOP_max_voltage_mV':key('native_vs_dop853_tight','voltage_mV'),
            'native_vs_tight_DOP_max_recovery_pA':key('native_vs_dop853_tight','recovery_pA'),
            'native_vs_explicit_float32_max_voltage_mV':key('native_vs_rk4_float32_explicit_no_fma','voltage_mV'),
            'native_vs_explicit_float32_max_recovery_pA':key('native_vs_rk4_float32_explicit_no_fma','recovery_pA'),
            'interpretation':'In this100pA condition before first threshold crossing, standard float64 RK4 truncation and joint coefficient rounding differences are much smaller than native-versus-float64 drift. Explicit scalar float32 rounding closely tracks native states, supporting operation-level float32 rounding as the dominant observed contributor here. This does not identify exact compiler FMA choices or demonstrate equivalence for other conditions, post-reset trajectories or firing outcomes.',
            'preservation':'Original numerical failure remains a failure. No gate relaxation, new integration, parameter/current/backend edits or biological scoring in this audit.',
            'limitations':['One selected post hoc condition and prethreshold window only.','Promoted coefficients change three constants jointly.','No-FMA scalar variant is not claimed exact GPU arithmetic equivalence.','Saved smooth extensions beyond crossing are not interpreted as reset trajectories.']}
    (HERE/'result_review.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))


if __name__=='__main__':review()
