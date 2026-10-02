from pathlib import Path
import json,hashlib,ast,re
import numpy as np
from task_io import spikes,voltage
from replay_reset_trial import NAMES
r=Path(__file__).resolve().parent
for marker in ['sensitivity-execution-complete.json','numerical-sensitivity-execution-complete.json','generalization-execution-complete.json']:assert (r/marker).exists()
source=r/'audit_nominal_experiment.py';ns={'hashlib':hashlib,'json':json,'re':re};tree=ast.parse(source.read_text());exec(compile(ast.Module(body=[a for a in tree.body if isinstance(a,ast.FunctionDef)],type_ignores=[]),str(source),'exec'),ns)
trials=json.loads((r/'frozen-task-protocol.json').read_text())['stimulus_definition']['trials'];plan=json.loads((r/'sensitivity-plan.json').read_text());gen=json.loads((r/'stimuli/generalization/configuration.json').read_text());specs=[]
for spec in plan['core_variants']:
 reversal=spec['GABAa_reversal_mV'];gain=spec['pyramidal_inhibitory_gain'];label=f'egaba{str(abs(reversal)).replace(".","p")}-gain{gain}';specs.append({'label':label,'trials':[t for t in trials if t['network_seed']==31],'gain':gain,'reversal':reversal,'steps':40,'output_gain':1,'own_core':True,'kind':'sensitivity'})
 specs.append({'label':f'precision-{label}','trials':[t for t in trials if t['network_seed']==31 and t['identity']==0 and t['repeat']==0],'gain':gain,'reversal':reversal,'steps':80,'output_gain':1,'own_core':True,'kind':'sensitivity'})
for gain in plan['CA1_coupling_variants']:specs.append({'label':f'output-gain{gain}','trials':trials,'gain':100,'reversal':-77.8,'steps':40,'output_gain':gain,'own_core':False,'kind':'sensitivity'})
for label,own_core,chosen in [('readout-rk80',False,trials),('full-rk80',True,[t for t in trials if t['network_seed']==31])]:specs.append({'label':label,'trials':chosen,'gain':100,'reversal':-77.8,'steps':80,'output_gain':1,'own_core':own_core,'kind':'sensitivity'})
specs.append({'label':'generalization','trials':gen['cases'],'gain':100,'reversal':-77.8,'steps':40,'output_gain':1,'own_core':True,'kind':'generalization'})
summary=[]
for spec in specs:
 core_signatures={};states={};readout_signatures={};core_count=0;readout_count=0
 for t in spec['trials']:
  seed=t['network_seed'];name=t['name'];base=r/'runs'/('sensitivity' if spec['kind']=='sensitivity' else 'generalization')
  if spec['kind']=='sensitivity':base=base/spec['label']
  base=base/name;core=base/'core' if spec['own_core'] else r/'runs/reset-task-v1'/name/'core'
  replay_root=r/'replays/generalization'/name if spec['kind']=='generalization' else (r/'replays/sensitivity'/spec['label']/name if spec['own_core'] else r/'replays/reset-task-v1'/name)
  if spec['own_core']:
   conf=json.loads((core/'configuration.json').read_text());assert (core/'exit-status.txt').read_text().strip()=='0';assert conf['seed']==seed and conf['substeps']==spec['steps'] and conf['CA2_inhibitory_gain']==spec['gain'] and conf['GABAa_reversal_mV']==spec['reversal'] and conf['default_CA2_output_gain']==1 and conf['duration_ms']==250
   inp=r/'stimuli'/('generalization' if spec['kind']=='generalization' else 'reset-task-v1')/name
   binary=r/'model/sensitivity'/('circuit-nominal' if spec['reversal']==-77.8 else f'circuit-egaba{int(abs(spec["reversal"]))}');assert conf['executable_sha256']==hashlib.sha256(binary.read_bytes()).hexdigest()
   for filename,digest in t['files_sha256'].items():assert hashlib.sha256((inp/filename).read_bytes()).hexdigest()==digest
   for population in ['MEC_LII_Stellate','CA3_Pyramidal']:assert ns['events'](spikes(core/'results',population))==sorted(tuple(map(int,line.split())) for line in (inp/f'{population}.txt').read_text().splitlines())
   state_bytes=b''
   for population in NAMES[:-1]:state_bytes+=voltage(core/'results',population)[:,:40].tobytes()
   states.setdefault(seed,set()).add(hashlib.sha256(state_bytes).hexdigest());core_signatures.setdefault(seed,set()).add(ns['signature'](core,33));core_count+=1
  streams={population:spikes(core/'results',population) for population in NAMES};meta=json.loads((replay_root/'configuration.json').read_text());assert Path(meta['source_run'])==core.resolve();perm=np.random.default_rng(meta['permutation_rng_seed']).permutation(18956)
  for condition in ['intact','blocked','scrambled']:
   run=base/condition;assert (run/'exit-status.txt').read_text().strip()=='0';conf=json.loads((run/'configuration.json').read_text());assert conf['seed']==seed and conf['substeps']==spec['steps'] and conf['CA2_inhibitory_gain']==spec['gain'] and conf['GABAa_reversal_mV']==spec['reversal'] and conf['default_CA2_output_gain']==spec['output_gain'] and conf['duration_ms']==250
   binary=r/'model/sensitivity'/('circuit-nominal' if spec['reversal']==-77.8 else f'circuit-egaba{int(abs(spec["reversal"]))}');assert conf['executable_sha256']==hashlib.sha256(binary.read_bytes()).hexdigest()
   voltage(run/'results','CA1_Pyramidal');readout_signatures.setdefault(seed,set()).add(ns['signature'](run,18))
   for population,a in streams.items():
    expected=ns['events'](a)
    if population=='CA2_Pyramidal' and condition=='blocked':expected=[]
    if population=='CA2_Pyramidal' and condition=='scrambled':expected=sorted((int(time),int(perm[cell])) for time,cell in zip(a['t'],a['id']))
    assert ns['events'](spikes(run/'results',population))==expected
    file=replay_root/condition/f'{population}.txt';assert hashlib.sha256(file.read_bytes()).hexdigest()==meta['files_sha256'][condition][file.name]
   for population in ['CA1_Pyramidal','CA1_Basket','CA1_Bistratified']:spikes(run/'results',population)
   readout_count+=1
 assert all(len(s)==1 for d in [states,core_signatures,readout_signatures] for s in d.values())
 summary.append({'label':spec['label'],'trials':len(spec['trials']),'verified_core_runs':core_count,'verified_readouts':readout_count,'network_seeds':sorted(readout_signatures)})
 print(f'{spec["label"]}: {core_count} cores and {readout_count} matched replays audited.',flush=True)
out={'complete':True,'variants':summary,'total_verified_core_runs':sum(a['verified_core_runs'] for a in summary),'total_verified_readouts':sum(a['verified_readouts'] for a in summary),'checks':['Exact source input hashes and delivery','Configurations and executable hashes','Complete finite monitored voltage data and valid complete spike files','Every delivered replay stream independently reconstructed from its source core and exact permutation','Reset baseline and aggregate graph-count matching within variants and seeds'],'limits':['Aggregate graph-count signatures are not individual-edge hashes.','Voltages record monitored subsets; spikes cover all modeled cells.','This validates execution and controls, not biological accuracy.']};(r/'extended-experiment-audit.json').write_text(json.dumps(out,indent=2))
