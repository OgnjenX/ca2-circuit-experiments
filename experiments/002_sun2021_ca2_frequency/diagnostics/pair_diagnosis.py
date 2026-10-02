from pathlib import Path
import sys,json,argparse
import numpy as np
root=Path(__file__).resolve().parents[3];sys.path.insert(0,str(root/'src'))
from ca2lab.slice import read_voltage_window
h=root/'experiments/003_corrected_ca2_frequency';parser=argparse.ArgumentParser();parser.add_argument('--workspace',type=Path,required=True);args=parser.parse_args();w=args.workspace.resolve();rows=json.load(open(h/'evidence/run_measurements.json'));checks=json.load(open(h/'evidence/numerical_checks.json'));lookup={(r['release'],r['active'],r['seed'],r['frequency_Hz'],r['steps']):r for r in rows};result=[]
for c in checks:
 key=(c['release'],c['active'],c['seed'],c['frequency_Hz']);lo=lookup[key+(20,)];hi=lookup[key+(40,)];tr=[];first=[]
 for r in [lo,hi]:
  directory=w/'runs'/r['label'];cfg=json.load(open(directory/'configuration.json'));v=read_voltage_window(directory/'results/n_CA2_Pyramidal.dat',128,4950,cfg['duration_ms']);tr.append(v);first.append(v[:,151:cfg['pulses_ms'][1]+1-4950].max(axis=1)-v[:,50:150].mean(axis=1))
 delta=np.array(hi['cell_ratios'])-np.array(lo['cell_ratios']);low=(np.minimum(*first)<.05);responsive=~low
 result.append({**c,'spikes20':lo['spikes'],'spikes40':hi['spikes'],'eligible20':lo['eligible'],'eligible40':hi['eligible'],'both_eligible_nonspiking':lo['eligible'] and hi['eligible'] and lo['spikes']==hi['spikes']==0,'failed_components':{'mean_ratio':c['mean_ratio_difference']>.05,'mean_peaks':c['max_mean_peak_difference_mV']>.1,'eligibility':lo['eligible']!=hi['eligible'],'spike_count':lo['spikes']!=hi['spikes']},'max_voltage_waveform_difference_mV':float(np.max(np.abs(tr[0]-tr[1]))),'low_response_cells':int(low.sum()),'signed_mean_ratio_change_low_cells_contribution':float(delta[low].sum()/128),'signed_mean_ratio_change_responsive_cells_contribution':float(delta[responsive].sum()/128),'responsive_mean_ratio_change':float(delta[responsive].mean()),'max_responsive_voltage_waveform_difference_mV':float(np.max(np.abs(tr[0][responsive]-tr[1][responsive])))})
record={'post_outcome_diagnostic_only':True,'frozen_scores_unchanged':True,'low_response_threshold_mV':.05,'pairs':result}
(h/'evidence/numerical_failure_diagnostics.json').write_text(json.dumps(record,indent=2)+'\n')
for release in ['stp','static']:
 subset=[x for x in result if x['release']==release];valid=[x for x in subset if x['both_eligible_nonspiking']];print(release,'both eligible',len(valid),'failed',sum(not x['pass'] for x in valid));print('eligible rows',[(x['seed'],x['active'],x['frequency_Hz'],x['pass'],x['mean_ratio_difference'],x['max_mean_peak_difference_mV'],x['max_voltage_waveform_difference_mV'],x['low_response_cells'],x['signed_mean_ratio_change_low_cells_contribution'],x['signed_mean_ratio_change_responsive_cells_contribution']) for x in valid]);print('failed components counts',{k:sum(x['failed_components'][k] for x in subset) for k in ['mean_ratio','mean_peaks','eligibility','spike_count']})
