from pathlib import Path
import ast,json,itertools,hashlib,subprocess,sys
import numpy as np
from task_io import spikes,voltage
r=Path(__file__).resolve().parent;protocol=json.loads((r/'frozen-task-protocol.json').read_text());plan=json.loads((r/'sensitivity-plan.json').read_text());bins=np.array([50,100,150,200,250])
source=r/'analyze_reset_task_v2.py';tree=ast.parse(source.read_text());namespace={'np':np,'bins':bins};functions=[a for a in tree.body if isinstance(a,ast.FunctionDef)];exec(compile(ast.Module(body=functions,type_ignores=[]),str(source),'exec'),namespace);features=namespace['features'];decoder=namespace['decoder']
def variant(label,trials,root):
 rows=[]
 for t in trials:
  for condition in ['intact','blocked','scrambled']:
   run=root/t['name']/condition;assert (run/'exit-status.txt').read_text().strip()=='0';a=spikes(run/'results','CA1_Pyramidal');v=voltage(run/'results','CA1_Pyramidal');baseline=v[:,40:50].mean(1);vf=np.stack([v[:,start:start+50].mean(1)-baseline for start in [50,100,150,200]],1).reshape(-1)
   rows.append({**t,'condition':condition,'spikes':features(a,128),'voltage':vf,'evoked_spikes':int(((a['t']>=50)&(a['t']<250)).sum())})
 seeds=sorted({t['network_seed'] for t in trials});summary=[]
 for seed in seeds:
  for context in [0,1]:
   for condition in ['intact','blocked','scrambled']:
    subset=[a for a in rows if a['network_seed']==seed and a['context']==context and a['condition']==condition];assert len(subset)==8;y=np.array([a['identity'] for a in subset]);train=np.array([a['split']=='train' for a in subset]);test=~train
    scores={kind:decoder(np.stack([a[kind] for a in subset]),y,train,test) for kind in ['spikes','voltage']}
    summary.append({'seed':seed,'context':context,'condition':condition,**scores,'total_evoked_spikes':sum(a['evoked_spikes'] for a in subset)})
 effects=[]
 for kind in ['spikes','voltage']:
  for alternative in ['blocked','scrambled']:
   differences=[]
   for seed in seeds:
    means={c:float(np.mean([a[kind] for a in summary if a['seed']==seed and a['condition']==c])) for c in ['intact',alternative]};differences.append(means['intact']-means[alternative])
   difference=np.array(differences);interval=None
   if len(seeds)>1:
    boot=np.array([difference[list(index)].mean() for index in itertools.product(range(len(seeds)),repeat=len(seeds))]);interval=np.quantile(boot,[.025,.975]).tolist()
   effects.append({'measure':kind,'comparison':'intact_minus_'+alternative,'network_seeds':seeds,'paired_differences':differences,'mean_difference':float(difference.mean()),'descriptive_bootstrap95_interval':interval,'note':'Network-level descriptive uncertainty, not animal uncertainty. Single-network sensitivity has no confidence interval.'})
 return {'label':label,'trials':len(trials),'network_seeds':seeds,'per_seed_context_condition':summary,'paired_effects':effects}
nominal_trials=protocol['stimulus_definition']['trials'];variants=[variant('nominal',nominal_trials,r/'runs/reset-task-v1')]
assert (r/'sensitivity-execution-complete.json').exists() and (r/'numerical-sensitivity-execution-complete.json').exists(),'Execution phases not complete'
for spec in plan['core_variants']:
 label=f'egaba{str(abs(spec["GABAa_reversal_mV"])).replace(".","p")}-gain{spec["pyramidal_inhibitory_gain"]}';trials=[t for t in nominal_trials if t['network_seed']==31];variants.append(variant(label,trials,r/'runs/sensitivity'/label))
for gain in plan['CA1_coupling_variants']:
 label=f'output-gain{gain}';variants.append(variant(label,nominal_trials,r/'runs/sensitivity'/label))
variants.append(variant('readout-rk80',nominal_trials,r/'runs/sensitivity/readout-rk80'));variants.append(variant('full-rk80',[t for t in nominal_trials if t['network_seed']==31],r/'runs/sensitivity/full-rk80'))
comparisons=[];nominal=variants[0]
for v in variants[1:]:
 for kind in ['spikes','voltage']:
  for alternative in ['blocked','scrambled']:
   chosen=next(a for a in v['paired_effects'] if a['measure']==kind and a['comparison']=='intact_minus_'+alternative)
   reference=next(a for a in nominal['paired_effects'] if a['measure']==kind and a['comparison']=='intact_minus_'+alternative);mapping=dict(zip(reference['network_seeds'],reference['paired_differences']));paired=[effect-mapping[seed] for seed,effect in zip(chosen['network_seeds'],chosen['paired_differences'])]
   comparisons.append({'variant':v['label'],'measure':kind,'comparison':chosen['comparison'],'matched_seed_effect_changes':paired,'mean_effect_change':float(np.mean(paired)),'variant_effect':chosen['mean_difference'],'matched_nominal_effect':float(np.mean([mapping[s] for s in chosen['network_seeds']]))})
out={'analysis_method_source':str(source.name),'analysis_method_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'variants':variants,'comparisons_with_nominal':comparisons,'limits':['Frozen feature/classifier definitions and train/test split for every variant; centroids refitted only on each variant/condition\'s designated training responses. This measures available information, not transfer of one unchanged trained readout across interventions.','Core perturbations and full-core numerical sensitivity use one preselected network; absence of a change there does not prove robustness across networks.','Half/double couplings andgain50/150 are exploratory perturbations, not measured confidence bounds.','Primary spike results remain primary even if secondary voltage decoding is positive.','Any numerical change in an inferred voltage effect limits its scientific interpretation.']};(r/'sensitivity-results.json').write_text(json.dumps(out,indent=2));print(json.dumps({'variants':len(variants),'comparisons':comparisons},indent=2))
subprocess.run([sys.executable,str(r/'analyze_context_responses.py')],check=True,cwd=r)
