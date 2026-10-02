from pathlib import Path
import struct,json
root=Path(__file__).resolve().parent
crit=json.loads((root/'numerical-check-criteria.json').read_text()); results={}
for steps in [5,10]:
 run=root/f'runs/fresh-seed10-rk{steps}';assert (run/'exit-status.txt').read_text().strip()=='0'
 rows={}
 for p in (run/'results').glob('spk_*.dat'):
  d=p.read_bytes();magic,ver,x,y,z=struct.unpack('<ifiii',d[:20]);assert magic==206661989
  counts=[0]*200
  for t,i in struct.iter_unpack('<ii',d[20:]):
   assert 0<=t<10000 and 0<=i<x*y*z
   counts[t//50]+=1
  rates=[c/(x*y*z*.05) for c in counts];starts=[];ends=[];active=False
  for j,rate in enumerate(rates):
   if rate>1 and not active:starts.append(j*50);active=True
   elif rate<=1 and active:ends.append(j*50);active=False
  if active:ends.append(10000)
  merged=[]
  for start,end in zip(starts,ends):
   if merged and start-merged[-1][1]<100:merged[-1][1]=end
   else:merged.append([start,end])
  starts=[v[0] for v in merged];ends=[v[1] for v in merged]
  rows[p.stem[4:]]={'neurons':x*y*z,'spikes':sum(counts),'mean_Hz':sum(counts)/(x*y*z*10),'rate_50ms':rates,'burst_starts_ms':starts,'burst_ends_ms':ends}
 results[str(steps)]=rows
checks={}
for name,r in results['5'].items():
 a=r['mean_Hz'];b=results['10'][name]['mean_Hz'];checks[name]={'relative_mean_rate_difference':abs(a-b)/max(a,1e-12),'pass_rate_screen':abs(a-b)/max(a,1e-12)<=.05}
a=results['5']['CA2_Pyramidal']['burst_starts_ms'];b=results['10']['CA2_Pyramidal']['burst_starts_ms'];starts_pass=len(a)==len(b) and all(abs(x-y)<=100 for x,y in zip(a,b))
res={'criteria':crit,'results':results,'checks':checks,'pyramidal_onsets_pass':starts_pass,'pass_preliminary_screen':starts_pass and all(c['pass_rate_screen'] for c in checks.values())}
(root/'numerical-validation.json').write_text(json.dumps(res,indent=2));print(json.dumps({'checks':checks,'pyramidal_onsets_5':a,'pyramidal_onsets_10':b,'pass':res['pass_preliminary_screen']},indent=2))
