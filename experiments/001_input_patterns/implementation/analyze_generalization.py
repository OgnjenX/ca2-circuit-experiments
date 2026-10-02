from pathlib import Path
import ast,json,hashlib,itertools,subprocess,sys
import numpy as np
from task_io import spikes,voltage,COUNTS
r=Path(__file__).resolve().parent
assert (r/'generalization-execution-complete.json').exists()
plan=json.loads((r/'stimuli/generalization/configuration.json').read_text())
nominal=json.loads((r/'frozen-task-protocol.json').read_text())['stimulus_definition']['trials']
source=r/'analyze_reset_task_v2.py';ns={'np':np,'bins':np.array([50,100,150,200,250])}
tree=ast.parse(source.read_text());exec(compile(ast.Module(body=[a for a in tree.body if isinstance(a,ast.FunctionDef)],type_ignores=[]),str(source),'exec'),ns)
def read(run):
 assert (run/'exit-status.txt').read_text().strip()=='0'
 a=spikes(run/'results','CA1_Pyramidal');v=voltage(run/'results','CA1_Pyramidal');baseline=v[:,40:50].mean(1)
 return {'spikes':ns['features'](a,128),'voltage':np.stack([v[:,start:start+50].mean(1)-baseline for start in [50,100,150,200]],1).reshape(-1),'count':int(((a['t']>=50)&(a['t']<250)).sum())}
def input_counts(directory):
 a=np.loadtxt(directory/'MEC_LII_Stellate.txt',dtype=np.int32)
 return np.bincount(a[:,1],minlength=10818).astype(float)
rows=[];controls=[];core_rows=[]
for t in plan['cases']:
 run=r/'runs/generalization'/t['name']/'core';assert (run/'exit-status.txt').read_text().strip()=='0'
 for population in ['CA2_Pyramidal','CA2_Basket','CA2_Wide_Arbor_Basket','CA2_Bistratified','CA2_SP_SR']:
  a=spikes(run/'results',population);valid=(a['t']>=50)&(a['t']<250);times=a['t'][valid];ids=a['id'][valid];n=COUNTS[population];first=np.full(n,250);np.minimum.at(first,ids,times);active=first<250
  core_rows.append({**{k:t[k] for k in ['name','network_seed','group','context','identity','repeat','CA3_delay_ms']},'population':population,'response_spikes':int(valid.sum()),'response_rate_Hz_per_cell':float(valid.sum()/n/.2),'baseline_rate_Hz_per_cell':float((a['t']<50).sum()/n/.05),'responsive_cell_fraction':float(active.mean()),'first_population_latency_ms':int(times.min()-50) if len(times) else None,'median_first_cell_latency_ms_among_responsive':float(np.median(first[active]-50)) if active.any() else None})
for seed,group,context in sorted({(t['network_seed'],t['group'],t['context']) for t in plan['cases']}):
 train=[t for t in nominal if t['network_seed']==seed and t['context']==context and t['split']=='train']
 tests=[t for t in plan['cases'] if t['network_seed']==seed and t['group']==group and t['context']==context]
 assert len(train)==len(tests)==4
 y=np.array([t['identity'] for t in train+tests]);trainmask=np.array([True]*4+[False]*4);testmask=~trainmask
 directories=[r/'stimuli/reset-task-v1'/t['name'] for t in train]+[r/'stimuli/generalization'/t['name'] for t in tests]
 inputs=np.stack([input_counts(d) for d in directories]);accuracy=ns['decoder'](inputs,y,trainmask,testmask);assert accuracy==1
 rate=ns['decoder'](inputs.sum(1,keepdims=True),y,trainmask,testmask);assert rate==.5
 controls.append({'network_seed':seed,'group':group,'context':context,'fixed_input_decoder_accuracy':accuracy,'total_count_accuracy':rate})
 for condition in ['intact','blocked','scrambled']:
  data=[read(r/'runs/reset-task-v1'/t['name']/condition) for t in train]+[read(r/'runs/generalization'/t['name']/condition) for t in tests]
  scores={kind:ns['decoder'](np.stack([a[kind] for a in data]),y,trainmask,testmask) for kind in ['spikes','voltage']}
  rows.append({'network_seed':seed,'group':group,'context':context,'condition':condition,**scores,'test_trials':4,'total_test_spikes':sum(a['count'] for a in data[4:])})
effects=[]
for group,context in sorted({(t['group'],t['context']) for t in plan['cases']}):
 for kind in ['spikes','voltage']:
  for alternative in ['blocked','scrambled']:
   differences=[]
   for seed in plan['network_seeds']:
    scores={a['condition']:a[kind] for a in rows if a['network_seed']==seed and a['group']==group and a['context']==context};differences.append(scores['intact']-scores[alternative])
   a=np.array(differences);boot=np.array([a[list(i)].mean() for i in itertools.product(range(5),repeat=5)])
   effects.append({'group':group,'context':context,'measure':kind,'comparison':'intact_minus_'+alternative,'paired_seed_differences':differences,'mean_difference':float(a.mean()),'descriptive_bootstrap95_interval':np.quantile(boot,[.025,.975]).tolist()})
out={'plan':plan,'analysis_source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'rows':rows,'paired_effects':effects,'input_positive_controls':controls,'core_response_rows':core_rows,'core_response_definition':'Same descriptive response/latency definitions as nominal response-dynamics-results.json. All modeled cells contribute spike counts. Comparisons with nominal inputs include fresh jitter, so timing comparisons are not exact matched-jitter counterfactuals. These measures do not replace or tune the frozen primary readout.','limits':['Five model networks; bootstrap intervals describe network variability, not animals.','Centroids use only frozen nominal training trials, with no retraining on new inputs.','These are variants of two synthetic classes, not novel individuals or memory tests.','Only generalization across the tested pattern changes and CA3 delays is assessed.']}
(r/'generalization-results.json').write_text(json.dumps(out,indent=2));print(json.dumps({'rows':rows,'input_positive_controls':controls},indent=2))
subprocess.run([sys.executable,str(r/'audit_extended_experiments.py')],check=True,cwd=r)
