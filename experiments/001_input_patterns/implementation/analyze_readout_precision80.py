from pathlib import Path
import json
import numpy as np
from task_io import spikes,voltage
r=Path(__file__).resolve().parent;out=[]
for ctx in [0,1]:
 for condition in ['intact','blocked','scrambled']:
  runs={};complete=True
  for steps in [40,80]:
   run=r/f'runs/readout-probe-ctx{ctx}-{condition}-rk{steps}'
   if not (run/'exit-status.txt').exists():complete=False;continue
   assert (run/'exit-status.txt').read_text().strip()=='0';v=voltage(run/'results','CA1_Pyramidal');a=spikes(run/'results','CA1_Pyramidal')
   runs[steps]={'voltage':v,'counts':{name:len(spikes(run/'results',name)) for name in ['CA1_Pyramidal','CA1_Basket','CA1_Bistratified']},'latency':int(a['t'].min())-50 if len(a) else None}
  checks={};voltage_check=False;latency_check=False;rms=None
  if complete:
   for name in runs[40]['counts']:
    x,y=runs[40]['counts'][name],runs[80]['counts'][name];fraction=abs(x-y)/max(x,y,1);checks[name]={'rk40':x,'rk80':y,'relative_difference':fraction,'pass':abs(x-y)<=1 if max(x,y)<=1 else fraction<=.05}
   vf={s:np.stack([z['voltage'][:,start:start+50].mean(1)-z['voltage'][:,40:50].mean(1) for start in [50,100,150,200]],axis=1) for s,z in runs.items()};rms=float(np.sqrt(np.mean((vf[40]-vf[80])**2)));voltage_check=rms<=.5
   a,b=runs[40]['latency'],runs[80]['latency'];latency_check=(a is None and b is None) or (a is not None and b is not None and abs(a-b)<=1)
  out.append({'context':ctx,'condition':condition,'complete':complete,'count_checks':checks,'voltage_feature_RMS_difference_mV':rms,'voltage_RMS_le_0p5mV':voltage_check,'latency_check':latency_check,'pass':complete and all(x['pass'] for x in checks.values()) and voltage_check and latency_check})
summary={'complete':all(a['complete'] for a in out),'pass':all(a['pass'] for a in out),'results':out,'criteria':'5% count difference (<=1 tolerated only if bothcounts<=1); pyramidal first latency<=1ms; baseline-subtracted four-window voltage features RMSdifference<=0.5mV. Same replay and seed20 at both precisions.'};(r/'readout-precision40vs80-results.json').write_text(json.dumps(summary,indent=2));print(json.dumps(summary,indent=2))
