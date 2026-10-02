from pathlib import Path
import ast,json
import numpy as np
r=Path(__file__).resolve().parent;p=json.loads((r/'frozen-task-protocol.json').read_text());tree=ast.parse((r/'analyze_reset_task.py').read_text());namespace={'np':np,'bins':np.array([50,100,150,200,250])}
functions=[a for a in tree.body if isinstance(a,ast.FunctionDef) and a.name in ['features','decoder']];assert len(functions)==2
exec(compile(ast.Module(body=functions,type_ignores=[]),'frozen_analysis_functions','exec'),namespace)
results=[]
for seed in p['stimulus_definition']['network_seeds']:
 for ctx in [0,1]:
  rows=[t for t in p['stimulus_definition']['trials'] if t['network_seed']==seed and t['context']==ctx];x=[];y=[];train=[]
  for trial in rows:
   events=np.loadtxt(r/'stimuli/reset-task-v1'/trial['name']/'MEC_LII_Stellate.txt',dtype=np.int32);assert events.shape==(49000,2)
   a=np.empty(len(events),dtype=[('t','<i4'),('id','<i4')]);a['t'],a['id']=events[:,0],events[:,1]
   f=namespace['features'](a,10818);assert f.sum()==49000 and np.count_nonzero(f)==9800
   x.append(f);y.append(trial['identity']);train.append(trial['split']=='train')
  x=np.stack(x);y=np.array(y);train=np.array(train);test=~train;accuracy=namespace['decoder'](x,y,train,test);rate=namespace['decoder'](x.reshape(8,10818,4).sum(1),y,train,test)
  assert accuracy==1 and rate==.5
  results.append({'seed':seed,'context':ctx,'cell_pattern_accuracy':accuracy,'aggregate_count_accuracy':rate})
out={'pass':True,'results':results,'meaning':'Frozen feature extraction and classifier identify prescribed patterns perfectly, while equal total counts contain no identity label. This checks task and analysis validity, not brain physiology.'};(r/'input-readout-positive-control.json').write_text(json.dumps(out,indent=2));print('All10 input control comparisons passed: pattern100%, aggregate50%.')
