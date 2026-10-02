from pathlib import Path
import json,hashlib,re
from collections import Counter
import numpy as np
from task_io import spikes,voltage
r=Path(__file__).resolve().parent;p=json.loads((r/'frozen-task-protocol.json').read_text());conditions=['intact','blocked','scrambled'];ca2=['CA2_Pyramidal','CA2_Basket','CA2_Wide_Arbor_Basket','CA2_Bistratified','CA2_SP_SR'];inputs=['MEC_LII_Stellate','CA3_Pyramidal'];complete=[];pending=[];graph_counts={};initial_states={}
def events(a):return sorted(zip(a['t'].tolist(),a['id'].tolist()))
def signature(run,expected):
 with (run/'results/carlsim.log').open() as file:text=file.read(131072)
 blocks=re.findall(r'Local Connection Id (\d+): ([^\n]+)\n(.*?)(?=Local Connection Id|\Z)',text,re.S);out=[]
 for cid,pair,body in blocks:
  n=re.search(r'Num of synapses\s*=\s*(\d+)',body);assert n is not None;out.append([int(cid),pair,int(n.group(1))])
 assert len(out)==expected
 return hashlib.sha256(json.dumps(out,separators=(',',':')).encode()).hexdigest()
for t in p['stimulus_definition']['trials']:
 base=r/'runs/reset-task-v1'/t['name']
 if not all((base/c/'exit-status.txt').exists() for c in ['core',*conditions]):pending.append(t['name']);continue
 for c in ['core',*conditions]:assert (base/c/'exit-status.txt').read_text().strip()=='0'
 core=base/'core';config=json.loads((core/'configuration.json').read_text());assert config['seed']==t['network_seed'] and config['substeps']==40 and config['duration_ms']==250 and config['inhibitory_gain']==100 and config['inhibitory_scope']=='pyramidal' and config['executable_sha256']==p['executable_sha256']
 inp=r/'stimuli/reset-task-v1'/t['name']
 for file,digest in t['files_sha256'].items():assert hashlib.sha256((inp/file).read_bytes()).hexdigest()==digest
 for name in inputs:assert events(spikes(core/'results',name))==sorted(tuple(map(int,s.split())) for s in (inp/f'{name}.txt').read_text().splitlines())
 state_bytes=b''
 for name in ca2:
  v=voltage(core/'results',name);spikes(core/'results',name);state_bytes+=v[:,:40].tobytes()
 state=hashlib.sha256(state_bytes).hexdigest();seed=t['network_seed'];initial_states.setdefault(seed,set()).add(state);graph_counts.setdefault(seed,set()).add(signature(core,33))
 streams={name:spikes(core/'results',name) for name in [*ca2,'CA3_Pyramidal']};meta=json.loads((r/'replays/reset-task-v1'/t['name']/'configuration.json').read_text());perm=np.random.default_rng(meta['permutation_rng_seed']).permutation(18956)
 readout_signatures=[]
 for condition in conditions:
  run=base/condition;conf=json.loads((run/'configuration.json').read_text());assert conf['seed']==seed and conf['substeps']==40 and conf['duration_ms']==250 and conf['executable_sha256']==p['executable_sha256'];voltage(run/'results','CA1_Pyramidal');readout_signatures.append(signature(run,18))
  for name,a in streams.items():
   expected=events(a)
   if name=='CA2_Pyramidal' and condition=='blocked':expected=[]
   if name=='CA2_Pyramidal' and condition=='scrambled':expected=sorted((int(time),int(perm[cell])) for time,cell in zip(a['t'],a['id']))
   delivered=events(spikes(run/'results',name));assert delivered==expected
   file=r/'replays/reset-task-v1'/t['name']/condition/f'{name}.txt';assert hashlib.sha256(file.read_bytes()).hexdigest()==meta['files_sha256'][condition][file.name]
  for name in ['CA1_Pyramidal','CA1_Basket','CA1_Bistratified']:spikes(run/'results',name)
 assert len(set(readout_signatures))==1
 complete.append(t['name'])
assert all(len(s)==1 for s in graph_counts.values());assert all(len(s)==1 for s in initial_states.values())
records=Counter(t['network_seed'] for t in p['stimulus_definition']['trials'] if t['name'] in complete)
full=len(complete)==80;out={'all80trials_complete':full,'verified_trials':len(complete),'verified_readout_runs':3*len(complete),'trials_verified_by_network':dict(records),'pending_trials':pending,'checks':['Exact input hashes and delivered core events','Core and readout seed/configuration and exit statuses','Complete finite voltage/adaptation/current data for every monitored CA2 group and CA1 target','Exact intact and blocked pyramidal streams','Exact bijective scrambled pyramidal stream, conserving spike times and cell trains','All four inhibitory streams and CA3 identical across controls','Same aggregate connection-count signatures across controls and repeated core trials','Identical pre-stimulus core voltage records across reset trials within network'],'aggregate_connection_signatures_by_seed':{seed:list(s) for seed,s in graph_counts.items()},'pre_stimulus_voltage_signatures_by_seed':{seed:list(s) for seed,s in initial_states.items()},'limits':['Connection-count signatures are not individual-edge hashes. Matching source configuration/seeds and event-loader code without RNG draws support fixed topology; this audit does not independently export every edge.','Monitor limit128pergroup means complete records for the monitored subset, not voltage recordings of all19,381CA2 neurons. Spikes are recorded for all modeled cells.','Partial progress is not a full completion claim.']};(r/'nominal-experiment-audit.json').write_text(json.dumps(out,indent=2));print(json.dumps({k:v for k,v in out.items() if k in ['all80trials_complete','verified_trials','verified_readout_runs','trials_verified_by_network']},indent=2))
