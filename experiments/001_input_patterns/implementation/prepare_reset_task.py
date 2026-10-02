from pathlib import Path
import json,random,hashlib
root=Path(__file__).resolve().parent
out=root/'stimuli/reset-task-v1';out.mkdir(exist_ok=False)
# Two equally sized, overlapping cortical patterns. No familiarity/learning interpretation.
rng=random.Random(908271);ids=list(range(10818));rng.shuffle(ids)
common=ids[:8820];patterns=[common+ids[8820:9800],common+ids[9800:10780]]
ca3=list(range(4096));rng.shuffle(ca3);ca3=ca3[:1940]
trials=[]
for seed in range(31,36):
 for context in [0,1]:
  for identity in [0,1]:
   for repeat in range(4):
    name=f'seed{seed}-ctx{context}-id{identity}-rep{repeat}'
    d=out/name;d.mkdir();trial_rng=random.Random(8000000+seed*1000+context*100+identity*10+repeat)
    # Draw both streams regardless of context to avoid a hidden RNG dependence.
    ec=sorted((50+10*pulse+trial_rng.randrange(3),cell) for pulse in range(5) for cell in patterns[identity])
    sc=sorted((75+10*pulse+trial_rng.randrange(3),cell) for pulse in range(5) for cell in ca3)
    for filename,events in [('MEC_LII_Stellate.txt',ec),('CA3_Pyramidal.txt',sc if context else [])]:
     (d/filename).write_text(''.join(f'{t} {cell}\n' for t,cell in events))
    trials.append({'name':name,'network_seed':seed,'context':context,'identity':identity,'repeat':repeat,'split':'train' if repeat<2 else 'test','files_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in d.iterdir()}})
config={'status':'Prospective stimulus definition; execution waits for physiology/numerical assessment; model configuration not yet frozen','purpose':'Synthetic identity transfer; no social-memory or learning claim','duration_ms':250,'response_window_ms':[50,250],'MEC_afferents':10818,'MEC_active_per_identity':9800,'MEC_shared_active_cells':8820,'CA3_afferents':4096,'CA3_active_if_context_present':1940,'pulse_count':5,'pulse_interval_ms':10,'MEC_first_pulse_ms':50,'CA3_first_pulse_ms':75,'jitter_ms':[0,1,2],'state':'Every trial starts a new simulator process, resetting membrane, synapse and plasticity states. Fixed connectivity seed within each replicate.','network_seeds':list(range(31,36)),'trials_per_network':16,'primary_readout':'CA1 128 targets: four50ms bins of cell spike counts; nearest-class-centroid Euclidean classifier trained only on designated training trials separately per context. Fixed classifier, no tuning. Balanced held-out accuracy; equal distance earns0.5.','controls':['Intact CA2 pyramidal output','Deleted CA2 pyramidal output, keeping all other input streams fixed','Independently permuted CA2 pyramidal neuron IDs per reset trial, preserving every spike time and cell train up to ID remapping'],'secondary_readout':'Aggregate population-count features using identical split and classifier. Report comparison without choosing the better decoder as primary.','uncertainty':'Paired effects computed per network seed; seeds are model replicates, not animals. Five seeds give exploratory uncertainty, not population-level biological significance.','null':'Balanced label permutations within context and split, fixed random seed, 1000 permutations for aggregate primary accuracy. Retain chance/no-response outcomes.','trials':trials}
(out/'configuration.json').write_text(json.dumps(config,indent=2));print(f'{len(trials)} prospective reset trials prepared')
