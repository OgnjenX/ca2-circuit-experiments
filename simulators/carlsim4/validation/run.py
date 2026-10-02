"""Compile actual CARLsim probe and compare public conductance readbacks to analytical oracle."""
import argparse,hashlib,json,subprocess
from pathlib import Path
import numpy as np
from oracle import expected
HERE=Path(__file__).resolve().parent
p=argparse.ArgumentParser();p.add_argument('--backend',required=True,type=Path);p.add_argument('--output',required=True,type=Path);p.add_argument('--historical',action='store_true');a=p.parse_args()
a.backend=a.backend.resolve();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=False)
command=['g++-12','-std=c++11','-O2',*[f'-I{a.backend/x}' for x in ['carlsim/interface/inc','carlsim/kernel/inc','carlsim/monitor']],str(HERE/'probe.cpp'),str(a.backend/'libcarlsim.a.4.0.0'),'-lcurand','-lcudart','-lpthread','-o',str(a.output/'probe')]
subprocess.run(command,check=True)
def edge(n=1,active=1,tau=4.7886,stp=True,rise=0,inh=False,delay=1,events=(10,)):
 return dict(n=n,active=active,tau=tau,stp=stp,rise=rise,inh=inh,delay=delay,events=list(events))
cases=[]
for silent in [0,1,31,91,255]:cases.append((f'silent-{silent}',80,[edge(n=1+silent)],0))
for stp in [False,True]:
 for rise in [0,2]:
  for reverse in [0,1,2]:
   cases.append((f'components-stp{stp}-rise{rise}-order{reverse}',1080,[edge(n=3,active=2,stp=stp,rise=rise,events=(0,20,200,999,1000,1001)),edge(n=5,active=3,tau=9,stp=not stp,rise=0,inh=True,delay=5,events=(0,20,200,999,1000,1001)),edge(tau=12,stp=False,rise=0,events=(10,30))],reverse))
cases.append(('pure-static',1080,[edge(stp=False,events=(0,20,999,1000,1001)),edge(stp=False,inh=True,tau=9,rise=2,delay=5,events=(0,20,999,1000,1001))],0))
cases.append(('reset-repeat',80,[edge()],0))
if a.historical:cases=[(name,duration,edges,1) for name,duration,edges,_ in cases[:5]]
results=[]
for mode in ['cpu','gpu']:
 for name,duration,edges,order in cases:
  folder=a.output/f'{mode}-{name}';folder.mkdir();spec=folder/'input.txt'
  spec.write_text(f'{duration} {order}\n'+''.join(f"{e['n']} {e['active']} {int(e['inh'])} {int(e['stp'])} {e['tau']} {e['rise']} {e['delay']} {len(e['events'])} "+' '.join(map(str,e['events']))+'\n' for e in edges))
  with (folder/'run.log').open('w') as log:
   outcome=subprocess.run([str(a.output/'probe'),mode,str(spec),str(folder/'trace.csv')],cwd=folder,stdout=log,stderr=subprocess.STDOUT)
  row=dict(mode=mode,case=name,exit_code=outcome.returncode)
  if outcome.returncode==0:
   actual=np.loadtxt(folder/'trace.csv',delimiter=',')[:,1:];want=np.column_stack([expected(duration,edges),expected(duration,edges,static=True)])
   error=np.abs(actual-want);row.update(max_absolute_error=float(error.max()),pass_oracle=bool(np.all(error<=2e-5+1e-4*np.abs(want))),observed_first=actual[11,0].item(),observed_second=actual[12,0].item(),expected_first=want[11,0].item(),expected_second=want[12,0].item(),trace_sha256=hashlib.sha256((folder/'trace.csv').read_bytes()).hexdigest())
  else:row['pass_oracle']=False
  results.append(row);print(row,flush=True)
record=dict(spec_sha256=hashlib.sha256((HERE/'spec.json').read_bytes()).hexdigest(),oracle_sha256=hashlib.sha256((HERE/'oracle.py').read_bytes()).hexdigest(),library_sha256=hashlib.sha256((a.backend/'libcarlsim.a.4.0.0').read_bytes()).hexdigest(),historical=a.historical,results=results,passed=all(r['pass_oracle'] for r in results))
(a.output/'results.json').write_text(json.dumps(record,indent=2)+'\n')
if not a.historical and not record['passed']:raise SystemExit(1)
