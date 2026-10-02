from pathlib import Path
import json,hashlib,subprocess,time
import numpy as np
from task_io import spikes,voltage
from replay_reset_trial import prepare,NAMES
r=Path(__file__).resolve().parent;p=json.loads((r/'frozen-task-protocol.json').read_text());plan=json.loads((r/'sensitivity-plan.json').read_text());assert (r/'reset-task-execution-complete.json').exists(),'Wait for nominal execution before GPU sensitivity batch.'
from sensitivity_io import execute
nominal=r/'model/sensitivity/circuit-nominal'
# Prove that capturing handles and adding an optional gain leave nominal output unchanged.
events=r/'replays/readout-probe-ctx0/intact';check=execute(r/'runs/sensitivity-unit-gain-check',nominal,'readout',20,events)
reference=r/'runs/readout-probe-ctx0-intact-rk40'
for name in ['CA1_Pyramidal','CA1_Basket','CA1_Bistratified']:
 a,b=[spikes(run/'results',name) for run in [check,reference]];assert sorted(zip(a['t'],a['id']))==sorted(zip(b['t'],b['id']))
assert np.array_equal(voltage(check/'results','CA1_Pyramidal'),voltage(reference/'results','CA1_Pyramidal'))
(r/'sensitivity-unit-gain-validation.json').write_text(json.dumps({'pass':True,'spikes_and_target_voltages_exactly_nominal':True},indent=2))
for spec in plan['core_variants']:
 reversal=spec['GABAa_reversal_mV'];gain=spec['pyramidal_inhibitory_gain'];label=f'egaba{str(abs(reversal)).replace(".","p")}-gain{gain}'
 binary=nominal if reversal==-77.8 else r/f'model/sensitivity/circuit-egaba{int(abs(reversal))}'
 trials=[t for t in p['stimulus_definition']['trials'] if t['network_seed']==31]
 for index,t in enumerate(trials):
  base=r/'runs/sensitivity'/label/t['name'];inputs=r/'stimuli/reset-task-v1'/t['name'];execute(base/'core',binary,'core',31,inputs,gain=gain,reversal=reversal)
  replays=r/'replays/sensitivity'/label/t['name']
  if not replays.exists():prepare(base/'core',replays,t['name'])
  for condition in ['intact','blocked','scrambled']:execute(base/condition,binary,'readout',31,replays/condition,gain=gain,reversal=reversal)
  print(f'{label}: {index+1}/16 verified',flush=True)
for output_gain in plan['CA1_coupling_variants']:
 label=f'output-gain{output_gain}'
 for index,t in enumerate(p['stimulus_definition']['trials']):
  replays=r/'replays/reset-task-v1'/t['name'];base=r/'runs/sensitivity'/label/t['name']
  for condition in ['intact','blocked','scrambled']:execute(base/condition,nominal,'readout',t['network_seed'],replays/condition,output_gain=output_gain)
  print(f'{label}: {index+1}/80 verified',flush=True)
(r/'sensitivity-execution-complete.json').write_text(json.dumps({'complete':True,'core_variants':len(plan['core_variants']),'output_variants':len(plan['CA1_coupling_variants']),'completed_unix':time.time()},indent=2))
