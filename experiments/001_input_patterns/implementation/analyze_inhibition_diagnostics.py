from pathlib import Path
import numpy as np,json
root=Path(__file__).resolve().parent
out=[]
for prefix,gains,reversal in [('physiology-default',[0,1,10,100],-70),('physiology-egaba77p8',[0,1,10,100,180,250,1000],-77.8)]:
 control=None
 for gain in gains:
  run=root/f'runs/{prefix}-CA3_Pyramidal-gain{gain}'
  if not (run/'exit-status.txt').exists():continue
  assert (run/'exit-status.txt').read_text().strip()=='0'
  a=np.fromfile(run/'results/n_CA2_Pyramidal.dat',dtype=[('t','<u4'),('id','<u4'),('v','<f4'),('u','<f4'),('I','<f4')],offset=24)
  assert len(a)==19200
  v=np.full((128,150),np.nan);v[a['id'],a['t']]=a['v'];assert np.isfinite(v).all()
  if gain==0:control=v
  delta=(v-control).mean(0)
  spikes=((run/'results/spk_CA2_Pyramidal.dat').stat().st_size-20)//8
  out.append({'reversal_mV':reversal,'gain':gain,'min_voltage_difference_mV':float(delta[50:].min()),'min_mean_voltage_mV':float(v.mean(0)[50:].min()),'mean_cell_peak_response_mV':float((v[:,50:110].max(1)-v[:,40:50].mean(1)).mean()),'CA2_Pyramidal_spikes':spikes,'eligible_subthreshold':spikes==0,'target_error_mV':abs(float(delta[50:].min())+13.8),'run':str(run.relative_to(root))})
candidates=[x for x in out if x['reversal_mV']==-77.8 and x['gain'] in [100,180,250] and x['eligible_subthreshold']]
summary={'status':'Exploratory calibration; not independent validation','results':out,'selected_tested_candidate':min(candidates,key=lambda x:x['target_error_mV']) if candidates else None,'selection_rule':'Nearest tested non-spiking inhibitory difference to -13.8mV. Functional outcomes are not selection criteria.','limitations':['Reversal is assumed from recording recipe, not measured EGABAa.','Aggregate inhibitory gain is fitted, not exported or a measured synaptic conductance.','Very large gains warn about missing biology or an unsuitable fitted model.','Numerical stability and held-out physiology must pass before a functional claim.']}
(root/'inhibition-diagnostic-summary.json').write_text(json.dumps(summary,indent=2));print(json.dumps(summary,indent=2))
