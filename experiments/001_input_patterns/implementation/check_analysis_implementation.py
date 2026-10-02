from pathlib import Path
import ast,json
import numpy as np
from task_io import spikes,voltage
r=Path(__file__).resolve().parent;p=json.loads((r/'frozen-task-protocol.json').read_text());trials=[t for t in p['stimulus_definition']['trials'] if t['network_seed']==31];assert len(trials)==16
checks=[]
for filename in ['analyze_reset_task.py','analyze_reset_task_v2.py']:
 tree=ast.parse((r/filename).read_text());functions=[a for a in tree.body if isinstance(a,ast.FunctionDef)];loop=next(a for a in tree.body if isinstance(a,ast.For) and isinstance(a.target,ast.Name) and a.target.id=='tr')
 ns={'r':r,'protocol':p,'trials':trials,'bins':np.array([50,100,150,200,250]),'records':[],'np':np,'spikes':spikes,'voltage':voltage};error=None
 try:exec(compile(ast.Module(body=functions+[loop],type_ignores=[]),filename,'exec'),ns)
 except Exception as e:error=type(e).__name__+': '+str(e)
 if filename.endswith('_v2.py'):
  assert error is None and len(ns['records'])==48
  for a in ns['records']:assert a['features'].shape==(512,) and a['voltage_features'].shape==(512,) and np.isfinite(a['voltage_features']).all() and a['features'].sum()==a['evoked_spikes']
 else:assert error is not None
 checks.append({'analysis':filename,'records_completed':len(ns['records']),'error':error})
(r/'analysis-implementation-smoke-check.json').write_text(json.dumps({'corrected_implementation_pass':True,'data':'Real completed network31trial outputs; check of data ingestion and feature construction only. No new scientific inference or fictitious replicate used.','checks':checks},indent=2));print(json.dumps(checks,indent=2))
