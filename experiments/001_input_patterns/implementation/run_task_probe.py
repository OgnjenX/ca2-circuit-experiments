from pathlib import Path
import json,subprocess,hashlib,time
from task_io import voltage,spikes
r=Path(__file__).resolve().parent;binary=r/'model/circuit-validated-candidate'
summary=json.loads((r/'pyramidal-train-validation-results.json').read_text())
assert summary['complete'] and summary['CA3_physiology_check']['qualitative_suppression_pass'] and all(x['pass'] for x in summary['numerical_checks'].values()),'Physiology/numerical gate not passed'
for ctx in [0,1]:
 for steps in [20,40]:
  run=r/f'runs/reset-task-probe-ctx{ctx}-rk{steps}';events=r/f'stimuli/reset-task-v1/seed31-ctx{ctx}-id0-rep0'
  assert not run.exists();(run/'results').mkdir(parents=True)
  conf={'mode':'core','network_seed':20,'duration_ms':250,'substeps':steps,'inhibitory_gain':100,'inhibitory_scope':'pyramidal','GABAa_reversal_mV':-77.8,'context':ctx,'purpose':'Exploratory task-condition numerical check; network seed20 excluded from confirmatory replications','input_directory':str(events),'executable_sha256':hashlib.sha256(binary.read_bytes()).hexdigest()};(run/'configuration.json').write_text(json.dumps(conf,indent=2))
  (run/'input-and-executable-sha256.txt').write_text('\n'.join(f'{hashlib.sha256(p.read_bytes()).hexdigest()} {p}' for p in [binary,*events.glob('*.txt')]))
  with (run/'run.log').open('w') as log:status=subprocess.run([str(binary),'core','20','250',str(steps),str(events),'100','pyramidal'],cwd=run,stdout=log,stderr=subprocess.STDOUT).returncode
  (run/'exit-status.txt').write_text(str(status));assert status==0
  for name in ['CA2_Pyramidal','CA2_Basket','CA2_Wide_Arbor_Basket','CA2_Bistratified','CA2_SP_SR']:voltage(run/'results',name);spikes(run/'results',name)
  print(f'context{ctx} rk{steps}: verified',flush=True)
