from pathlib import Path
import struct,json,random,hashlib
root=Path(__file__).resolve().parent
config=json.loads((root/'stimuli/pilot/configuration.json').read_text());trials=config['trials'];duration=config['duration_ms']
run=root/'runs/core-pilot-seed20';assert (run/'exit-status.txt').read_text().strip()=='0'
source=run/'results'
for mode in ['intact','blocked','scrambled']:
 out=root/'replays/pilot'/mode;out.mkdir(parents=True,exist_ok=True)
 audit={}
 for name,n in [('CA2_Pyramidal',18956),('CA2_Basket',105),('CA2_Wide_Arbor_Basket',147),('CA2_Bistratified',79),('CA2_SP_SR',94),('CA3_Pyramidal',1024)]:
  p=source/f'spk_{name}.dat';data=p.read_bytes();magic,version,x,y,z=struct.unpack('<ifiii',data[:20]);assert magic==206661989 and x*y*z==n
  events=list(struct.iter_unpack('<ii',data[20:]));assert all(0<=t<duration and 0<=i<n for t,i in events)
  if name=='CA2_Pyramidal' and mode=='blocked': events=[]
  elif name=='CA2_Pyramidal' and mode=='scrambled':
   perms=[]
   for trial in trials:
    rng=random.Random(700000+trial['trial']);ids=list(range(n));rng.shuffle(ids);perms.append(ids)
   events=[(t,perms[min((t-500)//300,len(trials)-1)][i] if t>=500 else i) for t,i in events]
  events.sort();f=out/f'{name}.txt';f.write_text(''.join(f'{t} {i}\n' for t,i in events))
  audit[name]={'events':len(events),'sha256':hashlib.sha256(f.read_bytes()).hexdigest()}
 (out/'configuration.json').write_text(json.dumps({'mode':mode,'source_run':str(run),'events':audit,'intervention':'CA2 pyramidal output only; other CA2 and CA3 events unchanged','scramble':'Within each 300ms trial block, independently permute pyramidal source identities; preserve every event time and each source-cell spike train up to a cell-ID permutation. Initial warmup unchanged. Same readout connectivity seed across conditions.','interpretation':'Output-pathway assay, not whole-CA2 silencing in an interacting brain; core network itself remains identical.'},indent=2))
print('Prepared all three exact replay conditions.')
