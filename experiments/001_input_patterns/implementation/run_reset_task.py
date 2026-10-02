from pathlib import Path
import hashlib,json,subprocess,time
from task_io import voltage,spikes,COUNTS
from replay_reset_trial import prepare
r=Path(__file__).resolve().parent
protocol=json.loads((r/'frozen-task-protocol.json').read_text());assert protocol['status']=='frozen before confirmatory outcomes'
binary=r/protocol['executable_path'];assert hashlib.sha256(binary.read_bytes()).hexdigest()==protocol['executable_sha256']
inputs=r/'stimuli/reset-task-v1';all_names=['CA2_Pyramidal','CA2_Basket','CA2_Wide_Arbor_Basket','CA2_Bistratified','CA2_SP_SR']
def execute(run,mode,seed,eventdir):
 configuration={'mode':mode,'seed':seed,'duration_ms':250,'substeps':protocol['substeps'],'inhibitory_scope':'pyramidal','inhibitory_gain':100 if mode=='core' else 'not applied to readout','GABAa_reversal_mV':-77.8,'input_directory':str(eventdir),'executable_sha256':protocol['executable_sha256']}
 if run.exists():
  assert (run/'exit-status.txt').exists(),'Existing unfinished run requires live-process audit; do not overwrite'
  assert (run/'exit-status.txt').read_text().strip()=='0'
  assert json.loads((run/'configuration.json').read_text())==configuration
 else:
  (run/'results').mkdir(parents=True);(run/'configuration.json').write_text(json.dumps(configuration,indent=2))
  (run/'input-and-executable-sha256.txt').write_text('\n'.join(f'{hashlib.sha256(p.read_bytes()).hexdigest()} {p}' for p in [binary,*eventdir.glob('*.txt')]))
  with (run/'run.log').open('w') as log:
   p=subprocess.Popen([str(binary),mode,str(seed),'250',str(protocol['substeps']),str(eventdir),'100','pyramidal'],cwd=run,stdout=log,stderr=subprocess.STDOUT)
   (run/'process.json').write_text(json.dumps({'pid':p.pid,'started_unix':time.time()}));status=p.wait()
  (run/'exit-status.txt').write_text(str(status));assert status==0
 if mode=='core':
  for name in all_names:voltage(run/'results',name);spikes(run/'results',name)
  for name in ['MEC_LII_Stellate','CA3_Pyramidal']:
   a=spikes(run/'results',name);expected=sorted(tuple(map(int,line.split())) for line in (eventdir/f'{name}.txt').read_text().splitlines())
   assert sorted(zip(a['t'].tolist(),a['id'].tolist()))==expected
 else:
  voltage(run/'results','CA1_Pyramidal')
  for name in ['CA2_Pyramidal','CA2_Basket','CA2_Wide_Arbor_Basket','CA2_Bistratified','CA2_SP_SR','CA3_Pyramidal']:
   a=spikes(run/'results',name);expected=sorted(tuple(map(int,line.split())) for line in (eventdir/f'{name}.txt').read_text().splitlines())
   assert sorted(zip(a['t'].tolist(),a['id'].tolist()))==expected
  for name in ['CA1_Pyramidal','CA1_Basket','CA1_Bistratified']:spikes(run/'results',name)
for index,trial in enumerate(protocol['stimulus_definition']['trials']):
 name=trial['name'];seed=trial['network_seed'];events=inputs/name
 for file,digest in trial['files_sha256'].items():assert hashlib.sha256((events/file).read_bytes()).hexdigest()==digest
 core=r/'runs/reset-task-v1'/name/'core';execute(core,'core',seed,events)
 replays=r/'replays/reset-task-v1'/name
 if not replays.exists():prepare(core,replays,name)
 else:
  manifest=json.loads((replays/'configuration.json').read_text())
  for condition,files in manifest['files_sha256'].items():
   for file,digest in files.items():assert hashlib.sha256((replays/condition/file).read_bytes()).hexdigest()==digest
 for condition in ['intact','blocked','scrambled']:execute(r/'runs/reset-task-v1'/name/condition,'readout',seed,replays/condition)
 print(f'{index+1}/{len(protocol["stimulus_definition"]["trials"])} verified: {name}',flush=True)
(r/'reset-task-execution-complete.json').write_text(json.dumps({'verified_trials':len(protocol['stimulus_definition']['trials']),'completed_unix':time.time(),'protocol_sha256':hashlib.sha256((r/'frozen-task-protocol.json').read_bytes()).hexdigest()},indent=2))
