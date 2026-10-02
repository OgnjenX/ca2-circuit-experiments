from pathlib import Path
import random,json,hashlib
root=Path(__file__).resolve().parent; out=root/'stimuli/pilot';out.mkdir(parents=True,exist_ok=True)
rng=random.Random(91731);labels=[(i,j) for i in [0,1] for j in [0,1] for _ in range(3)];rng.shuffle(labels)
ids=list(range(10818));rng.shuffle(ids);patterns=[ids[:5409],ids[5409:]]
ec=[];ca3=[];trials=[]
for trial,(identity,context) in enumerate(labels):
 start=500+trial*300
 trials.append({'trial':trial,'identity':identity,'CA3_context':context,'start_ms':start,'response_end_ms':start+200,'pulse_count':5,'pulse_interval_ms':10})
 for nid in patterns[identity]:
  jitter=rng.randint(0,2)
  for k in range(5):ec.append((start+k*10+jitter,nid))
 if context:
  for nid in range(1024):
   jitter=rng.randint(0,2)
   for k in range(5):ca3.append((start+25+k*10+jitter,nid))
for name,events in [('MEC_LII_Stellate',ec),('CA3_Pyramidal',ca3)]:
 (out/(name+'.txt')).write_text(''.join(f'{t} {i}\n' for t,i in sorted(events)))
config={'status':'exploratory pilot, not calibration or confirmatory test','duration_ms':4200,'stimulus_seed':91731,'trials':trials,'pattern_definition':'Two disjoint random half-populations of MEC LII Stellate afferents; equal pulse count and jitter distribution. Synthetic identity patterns. No familiarity signal or learning.','pulse_protocol':'5 pulses at 100 Hz inspired by Chevaleyre2010 Figure4 (LIII); this implementation uses exported MEC LII connections and is explicitly not a matched LIII replication.','CA3_context':'1024 stimulated CA3 afferents, 25 ms delayed train; number and timing are controlled experimental choices, not claimed animal recordings.','analysis_window':'0-200ms from train onset; includes delayed CA3 input','trial_interval_note':'300ms is a pilot interval and may retain adaptation; later design must test longer intervals and counterbalanced order.','files':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in out.glob('*.txt')}}
(out/'configuration.json').write_text(json.dumps(config,indent=2));print('Pilot schedule: 12 balanced trials, 4200ms; inputs saved.')
