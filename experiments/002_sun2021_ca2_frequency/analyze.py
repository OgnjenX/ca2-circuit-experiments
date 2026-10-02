"""Score the frozen assay and export compact, inspectable scientific evidence."""

import argparse
from collections import defaultdict
import json
from pathlib import Path
import sys

import numpy as np

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'src'))
from ca2lab.benchmark import setup_pass
from ca2lab.monitors import read_spikes
from ca2lab.slice import measure_epsps,read_voltage_window
from experiment import load,save,sha,verify_frozen


def analyze(workspace):
    frozen=verify_frozen(workspace)
    if sha(HERE/'analyze.py') != frozen['analysis_sha256']:
        raise ValueError('Analysis changed after freeze')
    protocol=load(HERE/'protocol.json')
    record=load(workspace/'measurements.json')
    if record['frozen_sha256'] != sha(HERE/'frozen_configuration.json'):
        raise ValueError('Measurement batch refers to a different freeze')
    measurements=record['runs']
    expected=2*len(protocol['calibration_amplitudes_mV'])*len(protocol['evaluation_seeds'])*(
        len(protocol['frequencies_Hz'])+len(protocol['primary_frequencies_Hz']))
    if len(measurements)!=expected:
        raise ValueError('Incomplete assay coverage')
    expected_keys={(release,selection['selected']['active'],seed,frequency,steps)
                   for release in ['stp','static']
                   for selection in frozen['calibration']['selections']
                   for seed in protocol['evaluation_seeds']
                   for steps,frequencies in [(protocol['nominal_substeps'],protocol['frequencies_Hz']),
                                             (protocol['precision_substeps'],protocol['primary_frequencies_Hz'])]
                   for frequency in frequencies}
    actual_keys=[(r['release'],r['active'],r['seed'],r['frequency_Hz'],r['steps']) for r in measurements]
    if len(set(actual_keys)) != len(actual_keys) or set(actual_keys) != expected_keys:
        raise ValueError('Duplicate or incorrect assay coverage')
    compact=HERE/'evidence'
    compact.mkdir(exist_ok=True)
    verified=[]
    conventions=[]
    # Independently re-read every run instead of trusting the incremental summaries.
    for result in measurements:
        directory=workspace/'runs'/result['label']
        cfg=load(directory/'configuration.json')
        if sha(directory/'configuration.json')!=result['configuration_sha256']:
            raise ValueError('Run configuration changed')
        expected_executable=(frozen['executable_sha256'] if result['release']=='stp' else frozen['build_record']['static_executable_sha256'])
        if cfg['executable_sha256']!=expected_executable:
            raise ValueError('Run executable differs from frozen executable')
        if cfg['scientific_file_sha256']!=frozen['scientific_file_sha256']:
            raise ValueError('Run source differs from frozen scientific sources')
        for name,digest in result['raw_sha256'].items():
            if sha(directory/'results'/name)!=digest:
                raise ValueError('Raw record changed')
        voltage=read_voltage_window(directory/'results/n_CA2_Pyramidal.dat',128,4950,cfg['duration_ms'])
        measured=measure_epsps(voltage,4950,cfg['pulses_ms'])
        np.testing.assert_allclose(measured['mean_ratios'],result['mean_ratios'],rtol=0,atol=1e-7)
        np.testing.assert_allclose(measured['mean_peaks_mV'],result['mean_peaks_mV'],rtol=0,atol=1e-7)
        spikes=read_spikes(directory/'results/spk_CA2_Pyramidal.dat',128,cfg['duration_ms'])
        delivered=read_spikes(directory/'results/spk_MEC_LII_Stellate.dat',10818,cfg['duration_ms'])
        actual={(int(row['t']),int(row['id'])) for row in delivered}
        expected_events={(t,cell) for t in cfg['pulses_ms'] for cell in range(cfg['active'])}
        if actual!=expected_events or len(spikes)!=result['spikes']:
            raise ValueError('Spike monitor inconsistency')
        eligibility=(len(spikes)==0 and abs(measured['baseline_mV']+70)<.05
                     and measured['max_baseline_drift_mV']<.01)
        if eligibility != result['eligible']:
            raise ValueError('Eligibility does not match raw records')
        # Convention sensitivity: incremental peaks relative to each pre-pulse value.
        pulses=cfg['pulses_ms'];base=voltage[:,pulses[0]-4950-100:pulses[0]-4950].mean(axis=1)
        peak_vectors=[];increments=[]
        for i,t in enumerate(pulses):
            begin=t+1-4950
            end=(pulses[i+1]+1 if i+1<len(pulses) else t+100)-4950
            peak=voltage[:,begin:end].max(axis=1)
            peak_vectors.append(peak-base)
            increments.append(peak-voltage[:,t-4950-1])
        incremental=float(np.mean(np.asarray(increments)[-1]/np.asarray(increments)[0]))
        convention={'label':result['label'],'baseline_ratio':result['mean_ratios'][-1],
                    'incremental_ratio':incremental,'not_used_for_primary_scoring':True}
        conventions.append(convention)
        verified.append(result)
    grouped=defaultdict(list)
    by_key={}
    for row in verified:
        by_key[(row['release'],row['active'],row['seed'],row['frequency_Hz'],row['steps'])]=row
        if row['steps']==protocol['nominal_substeps']:
            grouped[(row['release'],row['active'],row['frequency_Hz'])].append(row)
    numerical=[]
    for row in verified:
        if row['steps']!=protocol['precision_substeps']:
            continue
        nominal=by_key[(row['release'],row['active'],row['seed'],row['frequency_Hz'],protocol['nominal_substeps'])]
        difference=abs(row['mean_ratios'][-1]-nominal['mean_ratios'][-1])
        cell_difference=float(np.max(np.abs(np.array(row['cell_ratios'])-np.array(nominal['cell_ratios']))))
        peak_difference=float(np.max(np.abs(np.array(row['mean_peaks_mV'])-np.array(nominal['mean_peaks_mV']))))
        passed=(difference<=protocol['numerical_gates']['max_ratio_absolute_difference']
                and peak_difference<=protocol['numerical_gates']['max_EPSP_peak_difference_mV']
                and row['eligible']==nominal['eligible'] and row['spikes']==nominal['spikes'])
        numerical.append({'release':row['release'],'active':row['active'],'seed':row['seed'],'frequency_Hz':row['frequency_Hz'],
                          'mean_ratio_difference':difference,'max_cell_ratio_difference':cell_difference,
                          'max_mean_peak_difference_mV':peak_difference,'pass':passed})
    source={point['frequency_Hz']:point for point in load(HERE/'source_targets.json')['points']}
    comparisons=[]
    levels={s['selected']['active']:s['target_amplitude_mV'] for s in frozen['calibration']['selections']}
    for (release,active,frequency),rows in sorted(grouped.items()):
        values=[r['mean_ratios'][-1] for r in rows]
        lower,upper=source[frequency]['interval']
        model_mean=float(np.mean(values))
        eligible=all(r['eligible'] for r in rows)
        comparisons.append({'release':release,'target_single_EPSP_mV':levels[active],'active_afferents':active,
                            'frequency_Hz':frequency,'model_mean_ratio':model_mean,
                            'model_seed_min':min(values),'model_seed_max':max(values),
                            'source_mean_ratio':source[frequency]['mean'],
                            'conservative_source_interval':[lower,upper],
                            'absolute_error':abs(model_mean-source[frequency]['mean']),
                            'relative_error':(model_mean-source[frequency]['mean'])/source[frequency]['mean'],
                            'eligible_all_seeds':eligible,
                            'inside_compatibility_band':eligible and lower<=model_mean<=upper,
                            'all_seeds_below_band':eligible and max(values)<lower,
                            'all_seeds_above_band':eligible and min(values)>upper,
                            'model_seeds':[r['seed'] for r in rows],
                            'mean_first_EPSP_mV':float(np.mean([r['mean_peaks_mV'][0] for r in rows]))})
    primary=[r for r in comparisons if r['frequency_Hz'] in protocol['primary_frequencies_Hz']]
    numerical_pass=all(r['pass'] for r in numerical)
    level_passes={release:{str(level):setup_pass(
        [r for r in primary if r['release']==release and r['target_single_EPSP_mV']==level],
        protocol['primary_frequencies_Hz'],
        all(r['pass'] for r in numerical if r['release']==release))
        for level in protocol['calibration_amplitudes_mV']} for release in ['stp','static']}
    robust_miss=(numerical_pass and all(
        any((r['all_seeds_below_band'] or r['all_seeds_above_band'])
            for r in primary if r['release']=='stp' and r['target_single_EPSP_mV']==level)
        for level in protocol['calibration_amplitudes_mV']))
    summary={'frozen_configuration_sha256':sha(HERE/'frozen_configuration.json'),
             'run_count':len(verified),'nominal_run_count':sum(r['steps']==protocol['nominal_substeps'] for r in verified),
             'precision_pair_count':len(numerical),'numerical_pass':numerical_pass,
             'eligible_run_count':sum(r['eligible'] for r in verified),
             'comparisons':comparisons,'primary':primary,'setup_level_passes':level_passes,
             'robust_conditional_mismatch':robust_miss,
             'scope':'Selected CA2 APV frequency response in a reduced direct-input assay with a cross-figure amplitude assumption.',
             'full_paper_replication_established':False,
             'source_bands':'Conservative approximate mean-compatibility bands from digitized graph, not exact confidence/prediction intervals.',
             'unresolved':['Exact Figure 5 APV initial amplitude','Deployed Hippocampome physiology-source ancestry','Authors EPSP analysis convention','Dendritic and recurrent circuit mechanisms omitted']}
    save(compact/'results.json',summary)
    save(compact/'numerical_checks.json',numerical)
    save(compact/'run_measurements.json',verified)
    save(compact/'measurement_conventions.json',conventions)
    save(compact/'run_configurations.json',{r['label']:load(workspace/'runs'/r['label']/'configuration.json') for r in verified})
    # Export trace samples used by the figure, preserving every monitored cell.
    trace_records=[]
    for active,level in sorted(levels.items()):
        row=by_key[('stp',active,protocol['evaluation_seeds'][0],50,protocol['nominal_substeps'])]
        cfg=load(workspace/'runs'/row['label']/'configuration.json')
        voltage=read_voltage_window(workspace/'runs'/row['label']/'results/n_CA2_Pyramidal.dat',128,4950,cfg['duration_ms'])
        base=voltage[:,50:150].mean(axis=1)
        first=voltage[:,151:171].max(axis=1)-base
        normalized=((voltage[:,140:]-base[:,None])/first[:,None]).mean(axis=0)
        trace_records.append({'target_single_EPSP_mV':level,'seed':protocol['evaluation_seeds'][0],
                              'time_from_first_pulse_ms':list(range(-10,cfg['duration_ms']-5100)),
                              'normalized_mean_voltage':normalized.tolist()})
    save(compact/'trace_samples.json',trace_records)
    null=[]
    for selection in frozen['calibration']['selections']:
        active=selection['selected']['active'];level=selection['target_amplitude_mV']
        kernels=[]
        for seed in protocol['calibration_seeds']:
            directory=workspace/'runs'/f'cal-n{active}-s{seed}'
            record=load(directory/'measurement.json')
            for name,digest in record['raw_sha256'].items():
                if sha(directory/'results'/name)!=digest: raise ValueError('Calibration raw record changed')
            voltage=read_voltage_window(directory/'results/n_CA2_Pyramidal.dat',128,4950,5200)
            base=voltage[:,50:150].mean(axis=1)
            kernels.append(voltage[:,150:]-base[:,None])
        kernel=np.mean(kernels,axis=0)
        for frequency in protocol['frequencies_Hz']:
            pulses=[5100+round(k*1000/frequency) for k in range(5)]
            duration=pulses[-1]+100
            voltage=np.full((128,duration-4950),-70.,dtype=np.float64)
            for pulse in pulses:
                start=pulse-4950;end=min(start+kernel.shape[1],voltage.shape[1])
                voltage[:,start:end]+=kernel[:,:end-start]
            result=measure_epsps(voltage,4950,pulses)
            source_point=source[frequency]
            null.append({'level':level,'frequency_Hz':frequency,'mean_ratio':result['mean_ratios'][-1],
                         'source_mean_ratio':source_point['mean'],
                         'absolute_error':abs(result['mean_ratios'][-1]-source_point['mean']),
                         'construction':'Calibration single-pulse kernels only; 100ms support, zero thereafter; no train fits'})
    save(compact/'linear_null.json',null)
    print(json.dumps({'primary':primary,'numerical_pass':numerical_pass,
                      'robust_conditional_mismatch':robust_miss},indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace',type=Path,required=True)
    analyze(parser.parse_args().workspace.resolve())
