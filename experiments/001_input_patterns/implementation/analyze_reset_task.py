from pathlib import Path
import json,itertools
import numpy as np
from task_io import spikes,voltage
r=Path(__file__).resolve().parent;protocol=json.loads((r/'frozen-task-protocol.json').read_text());trials=protocol['stimulus_definition']['trials'];bins=np.array([50,100,150,200,250]);records=[]
def features(a,n):
 out=np.zeros((n,4),dtype=float);valid=(a['t']>=50)&(a['t']<250);t=a['t'][valid];ids=a['id'][valid]
 np.add.at(out,(ids,np.searchsorted(bins,t,side='right')-1),1);return out.reshape(-1)
def decoder(x,y,train,test):
 centers=[x[train&(y==k)].mean(0) for k in [0,1]];assert all((train&(y==k)).sum()==2 for k in [0,1])
 d=np.stack([((x[test]-c)**2).sum(1) for c in centers],1);ties=np.isclose(d[:,0],d[:,1],rtol=0,atol=1e-10)
 prediction=d.argmin(1);scores=np.where(ties,.5,(prediction==y[test]).astype(float));return float(scores.mean())
for tr in trials:
 base=r/'runs/reset-task-v1'/tr['name']
 assert (base/'core/exit-status.txt').read_text().strip()=='0'
 for condition in ['intact','blocked','scrambled']:
  run=base/condition;assert (run/'exit-status.txt').read_text().strip()=='0';a=spikes(run/'results','CA1_Pyramidal')
  v=voltage(run/'results','CA1_Pyramidal');base=v[:,40:50].mean(1);vf=np.stack([v[:,bins[b]:bins[b+1]].mean(1)-base for b in range(4)],axis=1).reshape(-1)
  records.append({**{k:tr[k] for k in ['name','network_seed','context','identity','repeat','split']},'condition':condition,'features':features(a,128),'voltage_features':vf,'evoked_spikes':int(((a['t']>=50)&(a['t']<250)).sum()),'first_latency_ms':int(a['t'].min())-50 if len(a) else None})
summary=[];datasets=[]
for seed in protocol['stimulus_definition']['network_seeds']:
 for context in [0,1]:
  for condition in ['intact','blocked','scrambled']:
   rows=[a for a in records if a['network_seed']==seed and a['context']==context and a['condition']==condition];assert len(rows)==8
   x=np.stack([a['features'] for a in rows]);y=np.array([a['identity'] for a in rows]);train=np.array([a['split']=='train' for a in rows]);test=~train
   rate=x.reshape(8,128,4).sum(1)
   vx=np.stack([a['voltage_features'] for a in rows])
   result={'network_seed':seed,'context':context,'condition':condition,'heldout_accuracy':decoder(x,y,train,test),'rate_only_accuracy':decoder(rate,y,train,test),'secondary_voltage_accuracy':decoder(vx,y,train,test),'total_evoked_spikes':sum(a['evoked_spikes'] for a in rows)};summary.append(result);datasets.append((condition,x,y,train,test))
seed_results=[]
for seed in protocol['stimulus_definition']['network_seeds']:
 seed_results.append({'network_seed':seed,**{condition:float(np.mean([a['heldout_accuracy'] for a in summary if a['network_seed']==seed and a['condition']==condition])) for condition in ['intact','blocked','scrambled']}})
index=list(itertools.product(range(5),repeat=5));effects={}
for alternative in ['blocked','scrambled']:
 differences=np.array([a['intact']-a[alternative] for a in seed_results]);boot=np.array([differences[list(i)].mean() for i in index])
 effects['intact_minus_'+alternative]={'mean_accuracy_difference':float(differences.mean()),'paired_seed_differences':differences.tolist(),'descriptive_bootstrap95_interval':np.quantile(boot,[.025,.975]).tolist(),'replicates':5,'note':'Exact five-seed bootstrap distribution; model-network uncertainty only, not uncertainty across animals.'}
null_rng=np.random.default_rng(671993);null={condition:[] for condition in ['intact','blocked','scrambled']}
for iteration in range(1000):
 values={c:[] for c in null}
 for condition,x,y,train,test in datasets:
  shuffled=y.copy();shuffled[train]=null_rng.permutation(y[train]);shuffled[test]=null_rng.permutation(y[test]);values[condition].append(decoder(x,shuffled,train,test))
 for condition in null:null[condition].append(float(np.mean(values[condition])))
null_summary={}
for condition in null:
 observed=float(np.mean([a['heldout_accuracy'] for a in summary if a['condition']==condition]));arr=np.array(null[condition]);null_summary[condition]={'observed_accuracy':observed,'permutation95_range':np.quantile(arr,[.025,.975]).tolist(),'one_sided_descriptive_p':float((1+(arr>=observed).sum())/1001),'permutations':1000,'note':'Balanced label permutations within network, context and split; no multiple-comparison adjustment. Primary intervention evidence is paired seed effects, not these diagnostic p values.'}
serial=[{k:v for k,v in a.items() if k not in ['features','voltage_features']} for a in records]
np.savez_compressed(r/'reset-task-features.npz',features=np.stack([a['features'] for a in records]),voltage_features=np.stack([a['voltage_features'] for a in records]))
out={'protocol':protocol,'per_seed_context_condition':summary,'per_seed_primary_accuracy':seed_results,'paired_effects':effects,'permutation_null':null_summary,'trials':serial,'limits':['Synthetic identities and random connectivity do not model familiarity, learning, or animal behavior.','CA1 is a feedforward sample with no pyramidal feedback.','CA2 intervention changes only pyramidal output; all inhibitory streams and direct CA3 input are preserved.','Reversal and inhibitory gain include assumptions and calibration; results are conditional on this revised model.','Five model networks do not establish CA2 function in animals.','No decoder tuning; trial split predetermined before outcomes.']}
(r/'reset-task-results.json').write_text(json.dumps(out,indent=2));print(json.dumps({'seed_results':seed_results,'effects':effects,'null':null_summary},indent=2))
