"""Descriptive post-outcome sensitivity audit; never changes frozen scores or exclusions."""
import argparse,json,sys
from pathlib import Path
import numpy as np
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];sys.path.insert(0,str(ROOT/'src'))
from ca2lab.slice import read_voltage_window
from experiment import load,save,sha,verify_frozen
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--workspace',type=Path,required=True);a=p.parse_args();w=a.workspace.resolve();frozen=verify_frozen(w)
rows=load(HERE/'evidence/run_measurements.json');checks=load(HERE/'evidence/numerical_checks.json');diagnostics=[]
for row in rows:
    directory=w/'runs'/row['label'];cfg=load(directory/'configuration.json')
    for name,digest in row['raw_sha256'].items():
        if sha(directory/'results'/name)!=digest:raise ValueError('Raw record changed')
    v=read_voltage_window(directory/'results/n_CA2_Pyramidal.dat',128,4950,cfg['duration_ms']);base=v[:,50:150].mean(axis=1);end=cfg['pulses_ms'][1]+1-4950
    first=v[:,151:end].max(axis=1)-base
    diagnostics.append({'label':row['label'],'release':row['release'],'frequency_Hz':row['frequency_Hz'],'seed':row['seed'],'active':row['active'],'steps':row['steps'],'eligible':row['eligible'],'spikes':row['spikes'],'first_peak_min_mV':float(first.min()),'first_peak_max_mV':float(first.max()),'cells_first_peak_below_0_05mV':int(np.sum(first<.05))})
lookup={(r['release'],r['active'],r['seed'],r['frequency_Hz'],r['steps']):r for r in rows}
first_differences=[]
for row in rows:
    if row['release']!='stp':continue
    other=lookup[('static',row['active'],row['seed'],row['frequency_Hz'],row['steps'])]
    first_differences.append(abs(row['mean_peaks_mV'][0]-other['mean_peaks_mV'][0]))
record={'post_outcome_descriptive_audit':True,'primary_scoring_changed':False,'low_response_threshold_is_diagnostic_only_mV':.05,'per_run':diagnostics,'matched_first_peak_max_mean_difference_mV':max(first_differences),'numerical_failures':[r for r in checks if not r['pass']],'excluded_runs':[r for r in diagnostics if not r['eligible']],'interpretation':'All-cell mean ratios retain the original convention. Near-zero first responses can make individual ratios unstable. Spiking runs do not represent EPSP compatibility regardless of apparent mean ratios.'}
save(HERE/'evidence/review_diagnostics.json',record);print('Descriptive audit saved; frozen primary scores unchanged.')
