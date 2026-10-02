from pathlib import Path
import json,struct
import numpy as np
from task_io import voltage
r=Path(__file__).resolve().parent;criteria=json.loads((r/'pyramidal-train-validation-criteria.json').read_text())
dtype=np.dtype([('t','<u4'),('id','<u4'),('v','<f4'),('u','<f4'),('I','<f4')]);names=['CA2_Pyramidal','CA2_Basket','CA2_Wide_Arbor_Basket','CA2_Bistratified','CA2_SP_SR'];results={};numerics={};physiology={}
for pathway in ['CA3_Pyramidal','MEC_LII_Stellate']:
 results[pathway]={}
 for label in ['blocked','fitted','fitted-rk40']:
  run=r/f'runs/pyramidal-train-validation-{pathway}-{label}'
  if not (run/'exit-status.txt').exists():continue
  assert (run/'exit-status.txt').read_text().strip()=='0'
  counts={};active={};first={}
  for name in names:
   a=np.fromfile(run/f'results/spk_{name}.dat',dtype=[('t','<i4'),('id','<i4')],offset=20);assert (a['t']>=0).all() and (a['t']<250).all()
   counts[name]=len(a);active[name]=len(np.unique(a['id']));first[name]=int(a['t'].min())-50 if len(a) else None
  delivered={}
  for name in ['MEC_LII_Stellate','CA3_Pyramidal']:
   a=np.fromfile(run/f'results/spk_{name}.dat',dtype=[('t','<i4'),('id','<i4')],offset=20)
   expected=[tuple(map(int,line.split())) for line in (r/f'stimuli/physiology-trains/{pathway}/{name}.txt').read_text().splitlines()]
   actual=list(zip(a['t'].tolist(),a['id'].tolist()));delivered[name]=sorted(actual)==sorted(expected);assert delivered[name]
  a=np.fromfile(run/'results/n_CA2_Pyramidal.dat',dtype=dtype,offset=24)
  assert len(a)==250*128 and np.isfinite(a['v']).all()
  v=np.full((128,250),np.nan);v[a['id'],a['t']]=a['v'];assert np.isfinite(v).all()
  monitored={name:voltage(run/'results',name).shape[0] for name in names}
  results[pathway][label]={'monitored_cells_finite_all_CA2':monitored,'spike_count':counts,'active_cells':active,'first_spike_latency_ms':first,'input_delivery_exact':delivered,'complete_finite_voltage':True,'mean_voltage_trace':v.mean(0).tolist(),'min_mean_voltage_mV':float(v.mean(0)[50:].min()),'max_mean_voltage_mV':float(v.mean(0)[50:].max())}
 if all(k in results[pathway] for k in ['fitted','fitted-rk40']):
  a,b=results[pathway]['fitted'],results[pathway]['fitted-rk40'];pop={}
  for name in names:
   x,y=a['spike_count'][name],b['spike_count'][name];fraction=abs(x-y)/max(x,y,1);passed=(abs(x-y)<=1 if max(x,y)<=1 else fraction<=.05)
   pop[name]={'rk20':x,'rk40':y,'relative_difference':fraction,'pass':passed}
  la,lb=a['first_spike_latency_ms']['CA2_Pyramidal'],b['first_spike_latency_ms']['CA2_Pyramidal'];same=(la is None)==(lb is None);latency=(la is None and lb is None) or (la is not None and lb is not None and abs(la-lb)<=1)
  numerics[pathway]={'populations':pop,'same_pyramidal_active_or_silent':same,'first_latency_pass':latency,'pass':all(p['pass'] for p in pop.values()) and same and latency}
 if pathway=='CA3_Pyramidal' and all(k in results[pathway] for k in ['blocked','fitted']):
  x=results[pathway]['blocked']['spike_count']['CA2_Pyramidal'];y=results[pathway]['fitted']['spike_count']['CA2_Pyramidal']
  physiology={'blocked_spikes':x,'fitted_spikes':y,'qualitative_suppression_pass':x>0 and y<x,'zero_fitted_spikes_matches_published_silence':y==0,'relative_suppression':1-y/x if x else None}
out={'complete':all(len(x)==3 for x in results.values()),'criteria':criteria,'results':results,'numerical_checks':numerics,'CA3_physiology_check':physiology,'limitations':['Neuron counts are model observations, not experimental replicates.','Inhibitory gain100 is fitted and extremely large, not a measured estimate.','The recording recipe estimates ECl, not directly measured EGABA.','A successful qualitative check does not establish a validated biological CA2 model.','CARLsim subsecond console summaries divide by an integer zero duration and show NaN rates; measurements here come from complete binary spike and voltage monitors.']}
(r/'pyramidal-train-validation-results.json').write_text(json.dumps(out,indent=2));print(json.dumps({'complete':out['complete'],'numerics':numerics,'physiology':physiology,'counts':{p:{k:x['spike_count']['CA2_Pyramidal'] for k,x in d.items()} for p,d in results.items()}},indent=2))
