"""Run a frozen analysis at its original paths and export outputs separately."""
import argparse
from pathlib import Path
import shutil
import subprocess
import sys
from assay_snapshot import PATHS, snapshot
from verify_assay_revisions import verify_relocation

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--revision', choices=list(PATHS), default='corrected')
parser.add_argument('--script', choices=['analyze.py', 'diagnostics/pair_diagnosis.py'], default='analyze.py')
parser.add_argument('--output', type=Path, required=True,
                    help='New directory for generated evidence; refuses existing paths')
parser.add_argument('arguments', nargs=argparse.REMAINDER)
args = parser.parse_args()
output = args.output.resolve()
if output.exists():
    parser.error('Output directory already exists')
arguments = args.arguments[1:] if args.arguments[:1] == ['--'] else args.arguments
verify_relocation()
with snapshot() as tree:
    experiment = tree / PATHS[args.revision]
    subprocess.run([sys.executable, str(experiment / args.script), *arguments], cwd=tree, check=True)
    shutil.copytree(experiment / 'evidence', output)
print(f'Evidence exported to {output}; canonical and historical evidence were not overwritten.')
