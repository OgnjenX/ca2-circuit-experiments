from pathlib import Path
import json,ast,itertools
import numpy as np
from task_io import spikes,COUNTS
r=Path(__file__).resolve().parent;assert (r/'reset-task-execution-complete.json').exists()
trials=json.loads((r/'frozen-task-protocol.json').read_text())['stimulus_definition']['trials']
source=r/'analyze_reset_task_v2.py';ns={'np':np,'bins':np.array([50,100,150,200,250])};tree=ast.parse(source.read_text());exec(compile(ast.Module(body=[a for a in tree.body if isinstance(a,ast.FunctionDef)],type_ignores=[]),str(source),'exec'),ns)
rows=[];vectors={}
groups={'core':['CA2_Pyramidal','CA2_Basket','CA2_Wide_Arbor_Basket','CA2_Bistratified','CA2_SP_SR'],**{c:['CA1_Pyramidal','CA1_Basket','CA1_Bistratified'] for c in ['intact','blocked','scrambled']}}
for t in trials:
 for condition,names in groups.items():
  for name in names:
   a=spikes(r/'runs/reset-task-v1'/t['name']/condition/'results',name);valid=(a['t']>=50)&(a['t']<250);times=a['t'][valid];ids=a['id'][valid];n=COUNTS[name]
   first=np.full(n,250);np.minimum.at(first,ids,times);active=first<250
   rows.append({**{k:t[k] for k in ['name','network_seed','context','identity','repeat','split']},'condition':condition,'population':name,'response_spikes':int(valid.sum()),'response_rate_Hz_per_cell':float(valid.sum()/n/.2),'baseline_rate_Hz_per_cell':float((a['t']<50).sum()/n/.05),'responsive_cell_fraction':float(active.mean()),'first_population_latency_ms':int(times.min()-50) if len(times) else None,'median_first_cell_latency_ms_among_responsive':float(np.median(first[active]-50)) if active.any() else None})
   vectors[(t['network_seed'],t['context'],condition,name,t['identity'],t['repeat'])]=ns['features'](a,n)
similarities=[]
def cosine(x,y):
 norm=np.linalg.norm(x)*np.linalg.norm(y)
 return float(np.dot(x,y)/norm) if norm else None
for seed in range(31,36):
 for context in [0,1]:
  for condition,names in groups.items():
   for name in names:
    v=[[vectors[(seed,context,condition,name,identity,repeat)] for repeat in range(4)] for identity in [0,1]]
    within=[cosine(v[k][i],v[k][j]) for k in [0,1] for i,j in itertools.combinations(range(4),2)];between=[cosine(x,y) for x in v[0] for y in v[1]]
    validwithin=[x for x in within if x is not None];validbetween=[x for x in between if x is not None]
    similarities.append({'network_seed':seed,'context':context,'condition':condition,'population':name,'mean_within_class_cosine':float(np.mean(validwithin)) if validwithin else None,'mean_between_class_cosine':float(np.mean(validbetween)) if validbetween else None,'silent_within_pairs':len(within)-len(validwithin),'silent_between_pairs':len(between)-len(validbetween),'class_centroid_L2_distance_spike_counts':float(np.linalg.norm(np.mean(v[0],0)-np.mean(v[1],0)))})
out={'trial_population_responses':rows,'similarity_and_separation':similarities,'definitions':{'response':'50-249ms; rates per modeled cell, averaged over200ms. Baseline reported separately over0-49ms.','latency':'First population response spike after50ms; median first-spike latency among responsive cells. Silent cells omitted from latency and their fraction reported.','reliability':'Cosine similarity of cell-by-four-bin spike-count vectors across repeats of the same class; no test-set selection or classifier adjustment.','separation':'Between-class cosine compared with within-class cosine; Euclidean distance of class means. Silent vectors have undefined cosine, recorded as missing.','scope':'Descriptive secondary response measures; all four repetitions included. No causal animal inference or neuron-level significance tests.'}}
(r/'response-dynamics-results.json').write_text(json.dumps(out,indent=2));print(f'{len(rows)} trial/population response records; {len(similarities)} network/context/population summaries.')
