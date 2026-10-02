from pathlib import Path
import json
from task_io import spikes,voltage
r=Path(__file__).resolve().parent;names=['CA2_Pyramidal','CA2_Basket','CA2_Wide_Arbor_Basket','CA2_Bistratified','CA2_SP_SR'];results={}
for ctx in [0,1]:
 comparisons={};complete=True
 for steps in [20,40]:
  run=r/f'runs/reset-task-probe-ctx{ctx}-rk{steps}'
  if not (run/'exit-status.txt').exists():complete=False;continue
  assert (run/'exit-status.txt').read_text().strip()=='0';counts={};latency={}
  for name in names:
   voltage(run/'results',name);a=spikes(run/'results',name);counts[name]=len(a);latency[name]=int(a['t'].min())-50 if len(a) else None
  comparisons[steps]={'counts':counts,'latency':latency,'complete_finite_recording':True}
 checks={};lp=False
 if complete:
  for name in names:
   x,y=comparisons[20]['counts'][name],comparisons[40]['counts'][name];relative=abs(x-y)/max(x,y,1);checks[name]={'rk20':x,'rk40':y,'relative_difference':relative,'pass':abs(x-y)<=1 if max(x,y)<=1 else relative<=.05}
  a,b=[comparisons[s]['latency']['CA2_Pyramidal'] for s in [20,40]];lp=(a is None and b is None) or (a is not None and b is not None and abs(a-b)<=1)
 results[str(ctx)]={'complete':complete,'comparisons':comparisons,'checks':checks,'first_pyramidal_latency_pass':lp,'pass':complete and all(x['pass'] for x in checks.values()) and lp}
out={'complete':all(x['complete'] for x in results.values()),'pass':all(x['pass'] for x in results.values()),'results':results,'gate':'Same5% population-count and1ms latency criteria as physiological precision check, evaluated on actual jittered task inputs at calibration network seed20. Held-out seeds31-35 remain unused.'};(r/'task-probe-results.json').write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2))
