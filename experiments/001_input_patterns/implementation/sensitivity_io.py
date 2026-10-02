from pathlib import Path
import json,hashlib,subprocess,time
from task_io import spikes,voltage
from replay_reset_trial import NAMES
def execute(run,binary,mode,seed,events,gain=100,output_gain=1,reversal=-77.8,steps=40):
 c={'mode':mode,'seed':seed,'duration_ms':250,'substeps':steps,'inhibitory_scope':'pyramidal','CA2_inhibitory_gain':gain,'default_CA2_output_gain':output_gain,'GABAa_reversal_mV':reversal,'input_directory':str(events),'executable_sha256':hashlib.sha256(binary.read_bytes()).hexdigest()}
 if run.exists():
  assert (run/'exit-status.txt').exists(),'Unfinished existing run: audit live process before resuming.';assert (run/'exit-status.txt').read_text().strip()=='0';assert json.loads((run/'configuration.json').read_text())==c
 else:
  (run/'results').mkdir(parents=True);(run/'configuration.json').write_text(json.dumps(c,indent=2));(run/'input-and-executable-sha256.txt').write_text('\n'.join(f'{hashlib.sha256(f.read_bytes()).hexdigest()} {f}' for f in [binary,*events.glob('*.txt')]))
  with (run/'run.log').open('w') as log:
   process=subprocess.Popen([str(binary),mode,str(seed),'250',str(steps),str(events),str(gain),'pyramidal',str(output_gain)],cwd=run,stdout=log,stderr=subprocess.STDOUT);(run/'process.json').write_text(json.dumps({'pid':process.pid,'started_unix':time.time()}));status=process.wait()
  (run/'exit-status.txt').write_text(str(status));assert status==0
 groups=['CA2_Pyramidal','CA2_Basket','CA2_Wide_Arbor_Basket','CA2_Bistratified','CA2_SP_SR'] if mode=='core' else ['CA1_Pyramidal']
 for name in groups:voltage(run/'results',name)
 input_names=['MEC_LII_Stellate','CA3_Pyramidal'] if mode=='core' else NAMES
 for name in input_names:
  a=spikes(run/'results',name);expected=sorted(tuple(map(int,line.split())) for line in (events/f'{name}.txt').read_text().splitlines());assert sorted(zip(a['t'].tolist(),a['id'].tolist()))==expected
 for name in (groups if mode=='core' else ['CA1_Pyramidal','CA1_Basket','CA1_Bistratified']):spikes(run/'results',name)
 return run
