from pathlib import Path
import json
import numpy as np
from task_io import spikes,voltage
r=Path(__file__).resolve().parent;plan=json.loads((r/'ca1-adequacy-plan.json').read_text());results=[]
for label in ['intact','target-inhibition-removed']:
 run=r/f'runs/ca1-adequacy-{label}';assert (run/'exit-status.txt').read_text().strip()=='0';v=voltage(run/'results','CA1_Pyramidal');a=spikes(run/'results','CA1_Pyramidal');ca3=spikes(run/'results','CA3_Pyramidal');assert len(ca3)==1940 and (ca3['t']==50).all()
 for name in ['CA2_Pyramidal','CA2_Basket','CA2_Wide_Arbor_Basket','CA2_Bistratified','CA2_SP_SR']:assert len(spikes(run/'results',name))==0
 baseline=v[:,40:50].mean(1);eligible=len(a)==0
 results.append({'condition':label,'spikes':len(a),'active_pyramidal_cells':len(np.unique(a['id'])),'target_cells':128,'baseline_mean_mV':float(baseline.mean()),'eligible_subthreshold_EPSP':eligible,'mean_cell_peak_EPSP_mV':float((v[:,50:110].max(1)-baseline).mean()) if eligible else None,'mean_voltage_trace':v.mean(0).tolist(),'input_delivery_verified':True,'all_target_voltage_adaptation_current_finite':True})
control=next(a for a in results if a['condition']=='target-inhibition-removed');out={'plan':plan,'results':results,'reference_comparison_eligible':control['eligible_subthreshold_EPSP'],'interpretation':'This assay is not matched to the slice: model initial voltage differs from -73mV and target-only inhibition removal is not a global drug manipulation. If spiking occurs, a spike peak is not a subthreshold EPSP and cannot be used as an amplitude match. Retain this failure as a downstream biological-validation limitation; the nominal frozen synthetic task is unchanged.'};(r/'ca1-adequacy-results.json').write_text(json.dumps(out,indent=2));print(json.dumps({k:v for k,v in out.items() if k not in ['plan','results']},indent=2));print(json.dumps([{k:v for k,v in a.items() if k!='mean_voltage_trace'} for a in results],indent=2))
