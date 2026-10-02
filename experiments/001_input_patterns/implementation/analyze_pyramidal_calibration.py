from pathlib import Path
import json
import numpy as np
r=Path(__file__).resolve().parent;design=json.loads((r/'pyramidal-inhibition-calibration-design.json').read_text());out=[];control=None
for gain in design['gain_candidates']:
 run=r/f'runs/physiology-egaba77p8-pyr-CA3_Pyramidal-gain{gain}'
 if not (run/'exit-status.txt').exists():continue
 assert (run/'exit-status.txt').read_text().strip()=='0'
 a=np.fromfile(run/'results/n_CA2_Pyramidal.dat',dtype=[('t','<u4'),('id','<u4'),('v','<f4'),('u','<f4'),('I','<f4')],offset=24);assert len(a)==150*128
 v=np.full((128,150),np.nan);v[a['id'],a['t']]=a['v'];assert np.isfinite(v).all()
 if gain==0:control=v
 delta=(v-control).mean(0);n=((run/'results/spk_CA2_Pyramidal.dat').stat().st_size-20)//8
 out.append({'gain':gain,'mean_waveform_min_inhibitory_difference_mV':float(delta[50:].min()),'mean_cell_min_inhibitory_difference_mV':float((v-control)[:,50:].min(1).mean()),'target_error_mV':abs(float(delta[50:].min())+13.8),'spikes':n,'eligible':n==0,'min_mean_voltage_mV':float(v.mean(0)[50:].min()),'complete_finite_voltage':True})
candidates=[x for x in out if x['gain']>0 and x['eligible']]
summary={'design':design,'complete':len(out)==len(design['gain_candidates']),'results':out,'selected':min(candidates,key=lambda x:x['target_error_mV']) if candidates else None,'note':'Calibration, not independent validation. Model neurons are not animal replicates. Extreme gain is a model-adequacy warning.'}
(r/'pyramidal-calibration-results.json').write_text(json.dumps(summary,indent=2));print(json.dumps({k:v for k,v in summary.items() if k!='design'},indent=2))
