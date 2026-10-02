from pathlib import Path
import ast,json,itertools
import numpy as np
r=Path(__file__).resolve().parent;result=json.loads((r/'reset-task-results.json').read_text());data=np.load(r/'reset-task-features.npz')['voltage_features'];records=result['trials'];assert len(records)==240 and data.shape==(240,512)
source=ast.parse((r/'analyze_reset_task_v2.py').read_text());f=next(a for a in source.body if isinstance(a,ast.FunctionDef) and a.name=='decoder');ns={'np':np};exec(compile(ast.Module(body=[f],type_ignores=[]),'frozen_decoder','exec'),ns);decoder=ns['decoder'];datasets=[];seeds=[31,32,33,34,35];summaries=[]
for seed in seeds:
 for ctx in [0,1]:
  for condition in ['intact','blocked','scrambled']:
   indices=[i for i,a in enumerate(records) if a['network_seed']==seed and a['context']==ctx and a['condition']==condition];assert len(indices)==8
   x=data[indices];y=np.array([records[i]['identity'] for i in indices]);train=np.array([records[i]['split']=='train' for i in indices]);test=~train;accuracy=decoder(x,y,train,test)
   recorded=next(a['secondary_voltage_accuracy'] for a in result['per_seed_context_condition'] if a['network_seed']==seed and a['context']==ctx and a['condition']==condition);assert accuracy==recorded
   summaries.append({'seed':seed,'context':ctx,'condition':condition,'accuracy':accuracy});datasets.append((condition,x,y,train,test))
per_seed=[{'seed':seed,**{c:float(np.mean([a['accuracy'] for a in summaries if a['seed']==seed and a['condition']==c])) for c in ['intact','blocked','scrambled']}} for seed in seeds];effects={}
for alternative in ['blocked','scrambled']:
 differences=np.array([a['intact']-a[alternative] for a in per_seed]);bootstrap=np.array([differences[list(index)].mean() for index in itertools.product(range(5),repeat=5)]);effects['intact_minus_'+alternative]={'paired_seed_differences':differences.tolist(),'mean_difference':float(differences.mean()),'descriptive_bootstrap95_interval':np.quantile(bootstrap,[.025,.975]).tolist()}
rng=np.random.default_rng(291874);null={c:[] for c in ['intact','blocked','scrambled']}
for repeat in range(1000):
 values={c:[] for c in null}
 for condition,x,y,train,test in datasets:
  shuffled=y.copy();shuffled[train]=rng.permutation(y[train]);shuffled[test]=rng.permutation(y[test]);values[condition].append(decoder(x,shuffled,train,test))
 for condition in null:null[condition].append(float(np.mean(values[condition])))
null_summary={}
for condition in null:
 observed=float(np.mean([a['accuracy'] for a in summaries if a['condition']==condition]));a=np.array(null[condition]);null_summary[condition]={'observed_accuracy':observed,'permutation95_range':np.quantile(a,[.025,.975]).tolist(),'one_sided_descriptive_p':float((1+(a>=observed).sum())/1001),'permutations':1000}
out={'prespecified_secondary_measure':True,'per_seed_context_condition':summaries,'per_seed_accuracy':per_seed,'paired_effects':effects,'permutation_null':null_summary,'limits':['Secondary voltage decoding does not replace the primary spike result.','Bootstrap describes five model networks, not animal uncertainty.','Voltage effects require numerical sensitivity checks and are not called spike transmission or social memory.','Permutation p values are descriptive without multiple-comparison adjustment.']};(r/'secondary-voltage-results.json').write_text(json.dumps(out,indent=2));print(json.dumps({'seed_values':per_seed,'effects':effects,'null':null_summary},indent=2))
