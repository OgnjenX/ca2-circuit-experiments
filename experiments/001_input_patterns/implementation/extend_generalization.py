from pathlib import Path
import json,shutil,hashlib,time
r=Path(__file__).resolve().parent;d=r/'stimuli/generalization';p=d/'configuration.json';old=p.read_bytes();cfg=json.loads(old)
assert len(cfg['cases'])==24,'Run once after prepare_generalization.py, before executing new trials.'
(r/'generalization-seed31-prospective-plan.json').write_bytes(old);base=list(cfg['cases'])
for seed in [32,33,34,35]:
 for t in base:
  name=f'seed{seed}-{t["name"]}';shutil.copytree(d/t['name'],d/name);cfg['cases'].append({**t,'name':name,'network_seed':seed,'input_pairing':'Identical unseen stimuli across networks; nominal training centroids fitted separately per network.'})
cfg['network_seeds']=[31,32,33,34,35];cfg.pop('network_seed');cfg['seed_scope']='Five nominal independent network seeds, with identical unseen inputs across networks. Paired descriptive network uncertainty, not animal uncertainty.';cfg['readout']='Use only nominal training centroids separately for each network, context and condition; no update on new trials.'
cfg['extension']={'before_nominal_decoder_outcome_inspection':True,'created_unix':time.time(),'reason':'Repeat held-out pattern and timing checks across independent networks as required by original design. No neural parameter or nominal protocol changes.','original_plan_sha256':hashlib.sha256(old).hexdigest()};p.write_text(json.dumps(cfg,indent=2))
