from pathlib import Path
import json,struct
import numpy as np
root=Path(__file__).resolve().parent;design=json.loads((root/'calibration-v3-design.json').read_text())
dtype=np.dtype([('t','<u4'),('id','<u4'),('v','<f4'),('u','<f4'),('I','<f4')]);results=[]
for case in design['cases']:
 run=root/('runs/calibration-v3-'+case['case']);assert (run/'exit-status.txt').read_text().strip()=='0'
 p=run/'results/n_CA2_Pyramidal.dat';magic,version,x,y,z,maxmon=struct.unpack('<ifiiii',p.read_bytes()[:24]);assert magic==206661979 and x*y*z==128
 a=np.fromfile(p,dtype=dtype,offset=24);assert len(a)==150*128 and np.isfinite(a['v']).all()
 values=np.full((128,150),np.nan);values[a['id'],a['t']]=a['v'];assert np.isfinite(values).all()
 baseline=values[:,40:50].mean(axis=1);amplitude=values[:,50:110].max(axis=1)-baseline
 spike_events=list(struct.iter_unpack('<ii',(run/'results/spk_CA2_Pyramidal.dat').read_bytes()[20:]));nspikes=len(spike_events)
 result=dict(case);result.update(mean_peak_mV=float(amplitude.mean()),sd_across_model_cells_mV=float(amplitude.std(ddof=1)),min_peak_mV=float(amplitude.min()),max_peak_mV=float(amplitude.max()),spikes=nspikes,baseline_mean_mV=float(baseline.mean()),eligible_subthreshold=nspikes==0,error_from_target_mV=float(abs(amplitude.mean()-case['target_EPSP_mV'])))
 results.append(result)
selected={}
for path in ['MEC_LII_Stellate','CA3_Pyramidal']:
 candidates=[r for r in results if r['pathway']==path and r['eligible_subthreshold']]
 if candidates:selected[path]=min(candidates,key=lambda r:r['error_from_target_mV'])
summary={'design':design,'results':results,'selected':selected,'note':'Selected nearest tested subthreshold input counts, not an independent validation. Do not interpret model-cell spread as experimental SEM.'}
(root/'calibration-v3-results.json').write_text(json.dumps(summary,indent=2));print(json.dumps({'results':results,'selected':selected},indent=2))
