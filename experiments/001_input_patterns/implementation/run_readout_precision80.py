from pathlib import Path
import json,subprocess,hashlib
from replay_reset_trial import prepare,NAMES
from task_io import spikes,voltage
r=Path(__file__).resolve().parent;b=r/'model/circuit-task-v1';assert json.loads((r/'task-probe-results.json').read_text())['pass']
for ctx in [0,1]:
 source=r/f'runs/reset-task-probe-ctx{ctx}-rk20';replays=r/f'replays/readout-probe-ctx{ctx}';assert replays.exists()
 for condition in ['intact','blocked','scrambled']:
  for steps in [80]:
   run=r/f'runs/readout-probe-ctx{ctx}-{condition}-rk{steps}';assert not run.exists();(run/'results').mkdir(parents=True);events=replays/condition
   c={'mode':'readout','seed':20,'duration_ms':250,'substeps':steps,'condition':condition,'context':ctx,'GABAa_reversal_mV':-77.8,'inhibitory_gain':'not applied to CA1','input_directory':str(events),'executable_sha256':hashlib.sha256(b.read_bytes()).hexdigest()};(run/'configuration.json').write_text(json.dumps(c,indent=2));(run/'input-and-executable-sha256.txt').write_text('\n'.join(f'{hashlib.sha256(p.read_bytes()).hexdigest()} {p}' for p in [b,*events.glob('*.txt')]))
   with (run/'run.log').open('w') as log:status=subprocess.run([str(b),'readout','20','250',str(steps),str(events)],cwd=run,stdout=log,stderr=subprocess.STDOUT).returncode
   (run/'exit-status.txt').write_text(str(status));assert status==0;voltage(run/'results','CA1_Pyramidal')
   for name in NAMES:
    a=spikes(run/'results',name);expected=sorted(tuple(map(int,line.split())) for line in (events/f'{name}.txt').read_text().splitlines());assert sorted(zip(a['t'].tolist(),a['id'].tolist()))==expected
   print(f'ctx{ctx} {condition} rk{steps}: inputs exact; output finite',flush=True)
