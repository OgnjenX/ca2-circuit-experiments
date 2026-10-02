"""Restore and verify the versioned raw workspace in a new directory."""
import argparse
import json
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'src'))
from ca2lab.provenance import extract_tar,verify_file
from experiment import verify_frozen

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--archive',type=Path,required=True)
parser.add_argument('--destination',type=Path,required=True)
args=parser.parse_args()
record=json.loads((HERE/'evidence/archive.json').read_text())['asset']
verify_file(args.archive,record['sha256'],record['bytes'])
extract_tar(args.archive,args.destination)
workspace=args.destination/'experiment_002'
manifest=json.loads((HERE/'evidence/workspace_manifest.json').read_text())
actual={p.relative_to(workspace).as_posix() for p in workspace.rglob('*') if p.is_file()}
if actual!=set(manifest):raise ValueError('Restored workspace has missing or extra files')
for name,item in manifest.items():verify_file(workspace/name,item['sha256'],item['bytes'])
verify_frozen(workspace)
print(f'Restored and verified {len(manifest)} files in {workspace}')
