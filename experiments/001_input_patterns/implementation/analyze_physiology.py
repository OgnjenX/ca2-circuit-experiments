from pathlib import Path
import json,struct
import numpy as np
root=Path(__file__).resolve().parent
results=[]
for pathway in ['MEC_LII_Stellate','CA3_Pyramidal']:
 traces={}; counts={}
 for gain in [0,1]:
  run=root/f'runs/physiology-default-{pathway}-gain{gain}'
  assert (run/'exit-status.txt').read_text().strip()=='0'
  p=run/'results/n_CA2_Pyramidal.dat'
  a=np.fromfile(p,dtype=[('t','<u4'),('id','<u4'),('v','<f4'),('u','<f4'),('I','<f4')],offset=24)
  assert len(a)==150*128 and np.isfinite(a['v']).all()
  v=np.full((128,150),np.nan);v[a['id'],a['t']]=a['v'];assert np.isfinite(v).all()
  traces[gain]=v
  counts[gain]={}
  for name in ['CA2_Pyramidal','CA2_Basket','CA2_Wide_Arbor_Basket','CA2_Bistratified','CA2_SP_SR']:
   p=run/f'results/spk_{name}.dat'; counts[gain][name]=(p.stat().st_size-20)//8
 difference=traces[1]-traces[0]
 difference-=difference[:,40:50].mean(axis=1)[:,None]
 pop_difference=difference.mean(axis=0)
 results.append({'pathway':pathway,'spikes_by_gain':counts,'baseline_mV':float(traces[1][:,40:50].mean()),'gain0_mean_cell_peak_EPSP_mV':float((traces[0][:,50:110].max(axis=1)-traces[0][:,40:50].mean(axis=1)).mean()),'gain1_mean_cell_peak_response_mV':float((traces[1][:,50:110].max(axis=1)-traces[1][:,40:50].mean(axis=1)).mean()),'inhibition_difference_population_min_mV':float(pop_difference[50:150].min()),'inhibition_difference_population_max_mV':float(pop_difference[50:150].max()),'difference_definition':'intact minus GABA-blocked voltage, baseline-corrected; minimum of population-mean waveform over 50-149ms','traces':{str(g):v.mean(axis=0).tolist() for g,v in traces.items()},'difference_mean_trace':pop_difference.tolist()})
out={'results':results,'reference':'https://pmc.ncbi.nlm.nih.gov/articles/PMC2905041/','CA3_reference_inhibitory_difference_mV':-13.8,'CA3_reference_SEM_mV':2.4,'MEC_LII_inhibitory_target':None,'warning':'Published -3.7mV EC inhibition refers to LIII, not the simulated MEC LII pathway. Gain zero is a modeled removal of all CA2 inhibitory outgoing synaptic weights; no intrinsic parameters changed. This is an aggregate comparison, not a matched slice reconstruction.'}
(root/'physiology-default-results.json').write_text(json.dumps(out,indent=2))
for r in results: print(json.dumps({k:v for k,v in r.items() if 'trace' not in k}))
