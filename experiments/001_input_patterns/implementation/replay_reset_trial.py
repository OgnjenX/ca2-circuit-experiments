from pathlib import Path
import json,hashlib
import numpy as np
from task_io import spikes,COUNTS
NAMES=['CA2_Pyramidal','CA2_Basket','CA2_Wide_Arbor_Basket','CA2_Bistratified','CA2_SP_SR','CA3_Pyramidal']
def prepare(run,destination,trial_name):
 run=Path(run);destination=Path(destination);assert not destination.exists()
 streams={name:spikes(run/'results',name) for name in NAMES};seed=int.from_bytes(hashlib.sha256(trial_name.encode()).digest()[:8],'little');perm=np.random.default_rng(seed).permutation(COUNTS['CA2_Pyramidal'])
 inverse_perm=np.argsort(perm)
 manifests={}
 for condition in ['intact','blocked','scrambled']:
  d=destination/condition;d.mkdir(parents=True)
  for name,a in streams.items():
   events=list(zip(a['t'].tolist(),a['id'].tolist()))
   if name=='CA2_Pyramidal':
    if condition=='blocked':events=[]
    if condition=='scrambled':events=[(t,int(perm[cell])) for t,cell in events]
   events.sort();(d/f'{name}.txt').write_text(''.join(f'{t} {cell}\n' for t,cell in events))
   if name=='CA2_Pyramidal' and condition=='scrambled':
    assert sorted(t for t,_ in events)==sorted(a['t'].tolist())
    restored=sorted((t,int(inverse_perm[cell])) for t,cell in events)
    assert restored==sorted(zip(a['t'].tolist(),a['id'].tolist()))
  manifests[condition]={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in d.iterdir() if p.is_file()}
 (destination/'configuration.json').write_text(json.dumps({'trial':trial_name,'condition':'CA2 pyramidal output only; all four CA2 inhibitory streams and CA3 unchanged','duration_ms':250,'permutation_rng_seed':seed,'population_size':18956,'scrambled_preserves':'All spike times, population counts, and each cell train up to a bijective identity remapping','source_run':str(run.resolve()),'source_executable_hash':(run/'input-and-executable-sha256.txt').read_text() if (run/'input-and-executable-sha256.txt').exists() else None,'files_sha256':manifests},indent=2))
 return manifests
if __name__=='__main__':
 import sys
 prepare(*sys.argv[1:])
