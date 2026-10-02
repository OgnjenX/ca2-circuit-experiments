from pathlib import Path
import json,time
import numpy as np
from sensitivity_io import execute
from replay_reset_trial import prepare
from task_io import spikes,voltage
r=Path(__file__).resolve().parent;p=json.loads((r/'frozen-task-protocol.json').read_text());plan=json.loads((r/'sensitivity-plan.json').read_text());results=[]
assert (r/'sensitivity-execution-complete.json').exists()
trials=[t for t in p['stimulus_definition']['trials'] if t['network_seed']==31 and t['identity']==0 and t['repeat']==0]
assert len(trials)==2
def compare(low,high,mode):
 groups=['CA2_Pyramidal','CA2_Basket','CA2_Wide_Arbor_Basket','CA2_Bistratified','CA2_SP_SR'] if mode=='core' else ['CA1_Pyramidal','CA1_Basket','CA1_Bistratified'];checks={}
 for name in groups:
  a,b=[spikes(run/'results',name) for run in [low,high]];x,y=len(a),len(b);fraction=abs(x-y)/max(x,y,1);checks[name]={'rk40':x,'rk80':y,'relative_difference':fraction,'pass':abs(x-y)<=1 if max(x,y)<=1 else fraction<=.05}
 a,b=[spikes(run/'results',groups[0]) for run in [low,high]];latency=(not len(a) and not len(b)) or (len(a)>0 and len(b)>0 and abs(int(a['t'].min())-int(b['t'].min()))<=1)
 rms=None
 if mode=='readout':
  v=[voltage(run/'results','CA1_Pyramidal') for run in [low,high]];vf=[np.stack([x[:,start:start+50].mean(1)-x[:,40:50].mean(1) for start in [50,100,150,200]],1) for x in v];rms=float(np.sqrt(np.mean((vf[0]-vf[1])**2)))
 return {'population_count_checks':checks,'first_pyramidal_latency_pass':bool(latency),'voltage_feature_RMS_difference_mV':rms,'pass':bool(all(a['pass'] for a in checks.values()) and latency and (rms is None or rms<=.5))}
for spec in plan['core_variants']:
 reversal=spec['GABAa_reversal_mV'];gain=spec['pyramidal_inhibitory_gain'];label=f'egaba{str(abs(reversal)).replace(".","p")}-gain{gain}';binary=r/'model/sensitivity'/('circuit-nominal' if reversal==-77.8 else f'circuit-egaba{int(abs(reversal))}')
 for t in trials:
  base=r/'runs/sensitivity'/f'precision-{label}'/t['name'];old=r/'runs/sensitivity'/label/t['name'];inputs=r/'stimuli/reset-task-v1'/t['name'];execute(base/'core',binary,'core',31,inputs,gain=gain,reversal=reversal,steps=80)
  replays=r/'replays/sensitivity'/f'precision-{label}'/t['name']
  if not replays.exists():prepare(base/'core',replays,t['name'])
  checks={'core':compare(old/'core',base/'core','core')}
  for condition in ['intact','blocked','scrambled']:
   execute(base/condition,binary,'readout',31,replays/condition,gain=gain,reversal=reversal,steps=80);checks[condition]=compare(old/condition,base/condition,'readout')
  results.append({'variant':label,'trial':t['name'],'context':t['context'],'checks':checks,'pass':all(a['pass'] for a in checks.values())});print(f'{label} context{t["context"]}: precision checks recorded.',flush=True)
out={'complete':True,'pass':all(a['pass'] for a in results),'results':results,'criteria':'Same pre-existing5%population-count/1msfirst-pyramidal-latency/0.5mVvoltage-featureRMS criteria; <=1difference tolerated onlywhen bothcounts<=1.','scope':'Two preselected seed31 identity0repeat0 trials per core variant, covering both contexts. Both core and readout use80substeps; matched nominal-variant runs use40. This spot check does not test full classifier robustness or all parameter networks.','completed_unix':time.time()};(r/'variant-precision-results.json').write_text(json.dumps(out,indent=2))
