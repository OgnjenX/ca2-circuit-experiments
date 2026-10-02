from pathlib import Path
import json,subprocess,hashlib
r=Path(__file__).resolve().parent;binary=r/'model/ca1-adequacy/circuit';events=r/'stimuli/ca1-adequacy-single-SC'
for gain,label in [(1,'intact'),(0,'target-inhibition-removed')]:
 run=r/f'runs/ca1-adequacy-{label}';assert not run.exists();(run/'results').mkdir(parents=True)
 c={'mode':'readout','seed':20,'duration_ms':250,'substeps':40,'CA1_target_inhibitory_gain':gain,'GABAa_reversal_mV':-77.8,'active_SC_afferents':1940,'pulse_ms':50,'input_directory':str(events),'executable_sha256':hashlib.sha256(binary.read_bytes()).hexdigest()};(run/'configuration.json').write_text(json.dumps(c,indent=2))
 with (run/'run.log').open('w') as log:status=subprocess.run([str(binary),'readout','20','250','40',str(events),str(gain)],cwd=run,stdout=log,stderr=subprocess.STDOUT).returncode
 (run/'exit-status.txt').write_text(str(status));assert status==0;print(f'{label}: exit0',flush=True)
