from pathlib import Path
import json,struct,math
root=Path(__file__).resolve().parent
conf=json.loads((root/'stimuli/pilot/configuration.json').read_text());trials=conf['trials']
def read_spikes(p):
 d=p.read_bytes();magic,version,x,y,z=struct.unpack('<ifiii',d[:20]);assert magic==206661989
 events=list(struct.iter_unpack('<ii',d[20:]));assert all(0<=t<conf['duration_ms'] and 0<=i<x*y*z for t,i in events)
 return x*y*z,events
def features(events,n):
 rows=[[0]*(n*4) for _ in trials]
 for t,i in events:
  if t<500:continue
  trial=(t-500)//300
  if trial>=len(trials):continue
  offset=t-trials[trial]['start_ms']
  if 0<=offset<200:rows[trial][i*4+offset//50]+=1
 return rows
def loo_accuracy(rows,indices):
 predictions=[]
 for test in indices:
  train=[i for i in indices if i!=test];centroids=[]
  for label in [0,1]:
   members=[rows[i] for i in train if trials[i]['identity']==label]
   if not members:return None
   centroids.append([sum(v)/len(v) for v in zip(*members)])
  distances=[sum((a-b)**2 for a,b in zip(rows[test],c)) for c in centroids]
  if abs(distances[0]-distances[1])<1e-12:correct=.5;prediction='tie'
  else:prediction=int(distances[1]<distances[0]);correct=int(prediction==trials[test]['identity'])
  predictions.append({'trial':test,'identity':trials[test]['identity'],'prediction':prediction,'correct':correct})
 return {'accuracy':sum(x['correct'] for x in predictions)/len(predictions),'predictions':predictions,'note':'Exploratory leave-one-trial-out nearest-centroid result, no tuning. Small samples and adaptation mean this is not confirmatory performance; ties count as chance.'}
results={'status':'exploratory pilot; independent-seed confirmatory testing still required','trials':trials,'conditions':{}}
core=root/'runs/core-pilot-seed20';assert (core/'exit-status.txt').read_text().strip()=='0'
n,events=read_spikes(core/'results/spk_CA2_Pyramidal.dat');rows=features(events,n)
results['core']={'pyramidal_spikes':len(events),'trial_window_spikes':[sum(row) for row in rows],'trial_rate_Hz_per_cell':[sum(row)/(n*.2) for row in rows]}
for mode in ['intact','blocked','scrambled']:
 run=root/f'runs/readout-pilot-seed20-{mode}';assert (run/'exit-status.txt').read_text().strip()=='0'
 n,events=read_spikes(run/'results/spk_CA1_Pyramidal.dat');rows=features(events,n)
 results['conditions'][mode]={'CA1_spikes':len(events),'trial_window_spikes':[sum(row) for row in rows],'identity_LOO_by_context':{str(context):loo_accuracy(rows,[i for i,t in enumerate(trials) if t['CA3_context']==context]) for context in [0,1]}}
(root/'pilot-results.json').write_text(json.dumps(results,indent=2));print(json.dumps(results,indent=2))
