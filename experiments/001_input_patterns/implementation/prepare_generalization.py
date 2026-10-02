from pathlib import Path
import json,random,hashlib
import numpy as np
r=Path(__file__).resolve().parent;out=r/'stimuli/generalization';assert not out.exists();out.mkdir()
def active(name):return set(np.loadtxt(r/'stimuli/reset-task-v1'/name/'MEC_LII_Stellate.txt',dtype=np.int32)[:,1].tolist())
patterns=[active('seed31-ctx0-id0-rep0'),active('seed31-ctx0-id1-rep0')];common=patterns[0]&patterns[1];unique=[sorted(p-common) for p in patterns];unused=sorted(set(range(10818))-patterns[0]-patterns[1]);assert len(common)==8820 and len(unique[0])==len(unique[1])==980 and len(unused)==38
ca3=sorted(set(np.loadtxt(r/'stimuli/reset-task-v1/seed31-ctx1-id0-rep0/CA3_Pyramidal.txt',dtype=np.int32)[:,1].tolist()));assert len(ca3)==1940
cases=[('pattern10',.1,0,25),('pattern10',.1,1,25),('pattern50',.5,0,25),('pattern50',.5,1,25),('delay15',0,1,15),('delay35',0,1,35)];trials=[]
for group,fraction,ctx,delay in cases:
 for identity in [0,1]:
  for repeat in [0,1]:
   name=f'{group}-ctx{ctx}-id{identity}-rep{repeat}';d=out/name;d.mkdir();seed=int.from_bytes(hashlib.sha256(name.encode()).digest()[:8],'little');rng=random.Random(seed);chosen=set(patterns[identity]);replaced=round(980*fraction)
   if replaced:
    chosen-=set(rng.sample(unique[identity],replaced));new_count=min(len(unused),replaced);chosen|=set(rng.sample(unused,new_count));chosen|=set(rng.sample(unique[1-identity],replaced-new_count))
   assert len(chosen)==9800
   # A majority of identity-specific cells remains in its own original class, even for 50% perturbation.
   assert len(chosen&set(unique[identity]))>len(chosen&set(unique[1-identity]))
   ec=sorted((50+10*pulse+rng.randrange(3),cell) for pulse in range(5) for cell in sorted(chosen));sc=sorted((50+delay+10*pulse+rng.randrange(3),cell) for pulse in range(5) for cell in ca3)
   for filename,events in [('MEC_LII_Stellate.txt',ec),('CA3_Pyramidal.txt',sc if ctx else [])]:(d/filename).write_text(''.join(f'{t} {cell}\n' for t,cell in events))
   trials.append({'name':name,'network_seed':31,'group':group,'context':ctx,'identity':identity,'repeat':repeat,'split':'unseen-test-only','CA3_delay_ms':delay,'fraction_distinctive_cells_replaced':fraction,'replaced_cells':replaced,'new_unrepresented_cells_used':min(38,replaced),'own_identity_cells_retained':len(chosen&set(unique[identity])),'competing_identity_cells_added':len(chosen&set(unique[1-identity])),'rng_seed':seed,'files_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in d.iterdir()}})
config={'status':'Prospective before nominal decoder outcomes; no neural parameters or frozen nominal protocol changed','purpose':'Unseen variants of the same two synthetic pattern classes and unseen CA3 timing; test the fixed nominal readout without retraining. This is not novel animal/object recognition.','network_seed':31,'seed_scope':'First independent seed selected prospectively; one-network descriptive generalization, not animal or network-population uncertainty.','readout':'Use only nominalseed31trainingtrial centroids for the corresponding context and condition; no update on these new trials.','duration_ms':250,'substeps':40,'MEC_active_cells':9800,'shared_base_cells':8820,'distinctive_cells':980,'source_classes':'Label follows majority membership of the original identity-specific cell pool. Replacement levels10/50%ofdistinctivecells correspond1/5%ofthe fullactiveensemble. Near-balanced50%case leaves a small38cellclassmargin and is intentionally harder.','positive_control':'The fixed input-pattern decoder trained on nominalinputcounts must classify allnewpatternvariants correctly; labels/counts/inputfiles verified. Equal totalcounts remainnoninformative.','cases':trials,'requirement':'Addresses original experiment-design stage to test held-out input patterns and timings with a frozen readout; nominal testing alone holdsout jittered trials, not pattern templates.'};(out/'configuration.json').write_text(json.dumps(config,indent=2));print(f'{len(trials)} prospective generalization trials prepared.')
