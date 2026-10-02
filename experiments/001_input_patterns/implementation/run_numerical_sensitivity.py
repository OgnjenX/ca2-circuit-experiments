from pathlib import Path
import json,time,subprocess,sys
from sensitivity_io import execute
from replay_reset_trial import prepare
r=Path(__file__).resolve().parent;p=json.loads((r/'frozen-task-protocol.json').read_text());assert (r/'reset-task-execution-complete.json').exists(),'Nominal execution must complete first.'
b=r/'model/sensitivity/circuit-nominal'
for index,t in enumerate(p['stimulus_definition']['trials']):
 replays=r/'replays/reset-task-v1'/t['name'];base=r/'runs/sensitivity/readout-rk80'/t['name']
 for condition in ['intact','blocked','scrambled']:execute(base/condition,b,'readout',t['network_seed'],replays/condition,steps=80)
 print(f'readout-rk80: {index+1}/80 verified',flush=True)
trials=[t for t in p['stimulus_definition']['trials'] if t['network_seed']==31]
for index,t in enumerate(trials):
 base=r/'runs/sensitivity/full-rk80'/t['name'];inputs=r/'stimuli/reset-task-v1'/t['name'];execute(base/'core',b,'core',31,inputs,steps=80)
 replays=r/'replays/sensitivity/full-rk80'/t['name']
 if not replays.exists():prepare(base/'core',replays,t['name'])
 for condition in ['intact','blocked','scrambled']:execute(base/condition,b,'readout',31,replays/condition,steps=80)
 print(f'full-rk80: {index+1}/16 verified',flush=True)
subprocess.run([sys.executable,str(r/'run_variant_precision.py')],check=True,cwd=r)
(r/'numerical-sensitivity-execution-complete.json').write_text(json.dumps({'complete':True,'readout_trials':80,'full_trials':16,'variant_precision_trials':8,'completed_unix':time.time()},indent=2))
