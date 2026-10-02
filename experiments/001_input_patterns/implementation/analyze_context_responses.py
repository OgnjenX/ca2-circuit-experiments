from pathlib import Path
import json,itertools
import numpy as np
from task_io import spikes,COUNTS
r=Path(__file__).resolve().parent
assert (r/'sensitivity-execution-complete.json').exists() and (r/'numerical-sensitivity-execution-complete.json').exists()
trials=json.loads((r/'frozen-task-protocol.json').read_text())['stimulus_definition']['trials'];plan=json.loads((r/'sensitivity-plan.json').read_text());groups=['CA2_Pyramidal','CA2_Basket','CA2_Wide_Arbor_Basket','CA2_Bistratified','CA2_SP_SR']
specs=[('nominal',trials,r/'runs/reset-task-v1')]
for s in plan['core_variants']:
 label=f'egaba{str(abs(s["GABAa_reversal_mV"])).replace(".","p")}-gain{s["pyramidal_inhibitory_gain"]}';specs.append((label,[t for t in trials if t['network_seed']==31],r/'runs/sensitivity'/label))
specs.append(('full-rk80',[t for t in trials if t['network_seed']==31],r/'runs/sensitivity/full-rk80'))
variants=[]
for label,chosen,root in specs:
 rows=[]
 for t in chosen:
  run=root/t['name']/'core';assert (run/'exit-status.txt').read_text().strip()=='0'
  for population in groups:
   a=spikes(run/'results',population);evoked=(a['t']>=50)&(a['t']<250);rows.append({'network_seed':t['network_seed'],'context':t['context'],'identity':t['identity'],'repeat':t['repeat'],'population':population,'spikes':int(evoked.sum()),'rate_Hz_per_cell':float(evoked.sum()/COUNTS[population]/.2)})
 summaries=[]
 for population in groups:
  seeds=sorted({t['network_seed'] for t in chosen});pairs=[]
  for seed in seeds:
   rates=[float(np.mean([a['rate_Hz_per_cell'] for a in rows if a['network_seed']==seed and a['population']==population and a['context']==context])) for context in [0,1]]
   pairs.append({'network_seed':seed,'cortex_only_rate':rates[0],'CA3_present_rate':rates[1],'difference_Hz_per_cell':rates[1]-rates[0],'ratio_CA3_present_to_cortex_only':rates[1]/rates[0] if rates[0] else None})
  difference=np.array([a['difference_Hz_per_cell'] for a in pairs]);ci=None
  if len(seeds)>1:
   boot=np.array([difference[list(i)].mean() for i in itertools.product(range(5),repeat=5)]);ci=np.quantile(boot,[.025,.975]).tolist()
  summaries.append({'population':population,'paired_network_results':pairs,'mean_rate_difference':float(difference.mean()),'descriptive_bootstrap95_interval':ci})
 variants.append({'label':label,'trials':len(chosen),'summaries':summaries})
out={'variants':variants,'limits':['Descriptive context comparison: cortical pulse jitter is separately drawn in the two contexts, so this is not an exact matched-input counterfactual for adding CA3.','CA2 gain was fitted to CA3 inhibition; suppression is conditional on that fit, not independent discovery or evidence of animal function.','Core parameter and full numerical sensitivity use only seed31; no interval or network-population robustness claim there.','Counts include all modeled cells; rates refer to the200msresponse window, not sustained in-vivo firing.']};(r/'context-response-results.json').write_text(json.dumps(out,indent=2));print('Six core variants analyzed for context-dependent response rates.')
