from pathlib import Path
import json,time
from sensitivity_io import execute
from replay_reset_trial import prepare
r=Path(__file__).resolve().parent
assert (r/'numerical-sensitivity-execution-complete.json').exists()
plan=json.loads((r/'stimuli/generalization/configuration.json').read_text())
b=r/'model/sensitivity/circuit-nominal'
for index,t in enumerate(plan['cases']):
 base=r/'runs/generalization'/t['name'];inputs=r/'stimuli/generalization'/t['name']
 execute(base/'core',b,'core',t['network_seed'],inputs)
 replays=r/'replays/generalization'/t['name']
 if not replays.exists():prepare(base/'core',replays,t['name'])
 for condition in ['intact','blocked','scrambled']:execute(base/condition,b,'readout',t['network_seed'],replays/condition)
 print(f'generalization: {index+1}/{len(plan["cases"])} verified',flush=True)
(r/'generalization-execution-complete.json').write_text(json.dumps({'complete':True,'trials':len(plan['cases']),'completed_unix':time.time()},indent=2))
