from pathlib import Path
import json,ast,hashlib,numpy as np
r=Path(__file__).resolve().parent;p=json.loads((r/'stimuli/generalization/configuration.json').read_text());nominal=json.loads((r/'frozen-task-protocol.json').read_text())['stimulus_definition']['trials'];source=r/'analyze_reset_task_v2.py';ns={'np':np,'bins':np.array([50,100,150,200,250])};tree=ast.parse(source.read_text());exec(compile(ast.Module(body=[a for a in tree.body if isinstance(a,ast.FunctionDef)],type_ignores=[]),str(source),'exec'),ns)
rows=[]
for seed,group,ctx in sorted({(t['network_seed'],t['group'],t['context']) for t in p['cases']}):
 train=[t for t in nominal if t['network_seed']==seed and t['context']==ctx and t['split']=='train'];test=[t for t in p['cases'] if t['network_seed']==seed and t['group']==group and t['context']==ctx];assert len(train)==len(test)==4
 dirs=[r/'stimuli/reset-task-v1'/t['name'] for t in train]+[r/'stimuli/generalization'/t['name'] for t in test];x=[]
 for d in dirs:
  a=np.loadtxt(d/'MEC_LII_Stellate.txt',dtype=np.int32);cells,counts=np.unique(a[:,1],return_counts=True);assert len(cells)==9800 and (counts==5).all();assert (a[:,0]>=50).all() and (a[:,0]<=92).all();x.append(np.bincount(a[:,1],minlength=10818))
 y=np.array([t['identity'] for t in train+test]);tm=np.array([True]*4+[False]*4);accuracy=ns['decoder'](np.stack(x),y,tm,~tm);assert accuracy==1;assert ns['decoder'](np.stack(x).sum(1,keepdims=True),y,tm,~tm)==.5
 rows.append({'network_seed':seed,'group':group,'context':ctx,'input_accuracy':accuracy,'total_count_accuracy':.5})
for t in p['cases']:
 d=r/'stimuli/generalization'/t['name']
 for f,h in t['files_sha256'].items():assert hashlib.sha256((d/f).read_bytes()).hexdigest()==h
 lines=(d/'CA3_Pyramidal.txt').read_text().splitlines();assert len(lines)==(9700 if t['context'] else 0)
 if lines:
  a=np.array([list(map(int,line.split())) for line in lines]);ids,counts=np.unique(a[:,1],return_counts=True);assert len(ids)==1940 and (counts==5).all();assert (a[:,0]>=50+t['CA3_delay_ms']).all() and (a[:,0]<=92+t['CA3_delay_ms']).all()
out={'complete':True,'trials':len(p['cases']),'checks':'Exact file hashes, five events per active cell, timing bounds, matched active counts, fixed nominal input decoder and total count negative control.','positive_controls':rows,'configuration_sha256':hashlib.sha256((r/'stimuli/generalization/configuration.json').read_bytes()).hexdigest()};(r/'generalization-input-audit.json').write_text(json.dumps(out,indent=2));print(f'{len(p["cases"])} input trials verified; {len(rows)} fixed-decoder positive controls passed.')
