"""Create a fresh runnable copy, keeping historical reference data separate."""
from pathlib import Path
import argparse,json,shutil,hashlib
from task_io import spikes,voltage
r=Path(__file__).resolve().parent
parser=argparse.ArgumentParser();parser.add_argument('destination',nargs='?');parser.add_argument('--verify-only',action='store_true');args=parser.parse_args()
protocol=json.loads((r/'frozen-task-protocol.json').read_text())
for name,digest in protocol['files_sha256'].items():assert hashlib.sha256((r/name).read_bytes()).hexdigest()==digest
directories=['model','simulator-reversal-variant','simulator-reversal-75','simulator-reversal-80','stimuli','revised-source-export','plot-deps']
references=['runs/readout-probe-ctx0-intact-rk40','replays/readout-probe-ctx0/intact']
for name in directories+references:assert (r/name).is_dir(),name
for name in ['CA1_Pyramidal','CA1_Basket','CA1_Bistratified']:spikes(r/references[0]/'results',name)
voltage(r/references[0]/'results','CA1_Pyramidal')
for name in ['CA2_Pyramidal','CA2_Basket','CA2_Wide_Arbor_Basket','CA2_Bistratified','CA2_SP_SR','CA3_Pyramidal']:assert (r/references[1]/f'{name}.txt').exists()
outputs={'reset-task-results.json','secondary-voltage-results.json','sensitivity-results.json','generalization-results.json','context-response-results.json','response-dynamics-results.json','variant-precision-results.json','nominal-experiment-audit.json','extended-experiment-audit.json','pursuit-state.json','artifact-manifest.json'}
outputs.update({'completion-audit.json','report-visual-review.json','generalization-scientific-review.json','sensitivity-scientific-review.json','frozen-artifact-integrity-check.json','reproduction-copy-validation.json'})
static_json=[p for p in r.glob('*.json') if p.name not in outputs and 'execution-complete' not in p.name and 'pipeline-state' not in p.name]
scripts=list(r.glob('*.py'));documents=[r/'methods.txt',r/'REPRODUCE.txt']
if args.verify_only:
 print(json.dumps({'frozen_artifacts_verified':len(protocol['files_sha256']),'directories':directories,'retained_unit_gain_reference':references,'scripts':len(scripts),'static_json':len(static_json),'note':'No copy or simulation executed. Runtime and NVIDIA access must be available on the rerun machine.'},indent=2));raise SystemExit
assert args.destination,'Supply a new destination directory or use --verify-only.'
d=Path(args.destination).expanduser().resolve();assert not d.exists(),'Destination must not already exist.';assert d!=r and r not in d.parents,'Use a separate directory, not a child of this experiment.';d.mkdir(parents=True)
for name in directories+references:shutil.copytree(r/name,d/name,ignore=shutil.ignore_patterns('__pycache__'))
for p in [*scripts,*documents,*static_json]:shutil.copy2(p,d/p.name)
reference=d/'reference-evidence';reference.mkdir()
for p in r.glob('*.json'):shutil.copy2(p,reference/p.name)
for name,digest in protocol['files_sha256'].items():assert hashlib.sha256((d/name).read_bytes()).hexdigest()==digest
assert not (d/'reset-task-execution-complete.json').exists() and not (d/'runs/reset-task-v1').exists()
(d/'reproduction-copy.json').write_text(json.dumps({'source':str(r),'destination':str(d),'fresh_task_outputs':True,'immutable_unit_gain_reference':references,'frozen_hashes_verified':protocol['files_sha256'],'note':'Historical JSON evidence is in reference-evidence; it is not proof of the rerun. Execute the sequential workflow in REPRODUCE.txt with NVIDIA access.'},indent=2));print(d)
