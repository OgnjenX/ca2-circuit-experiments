"""Archive the full workspace, including raw data and retained failed attempts."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import tarfile

HERE=Path(__file__).resolve().parent
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--workspace',type=Path,required=True)
parser.add_argument('--output',type=Path,required=True)
args=parser.parse_args()
workspace=args.workspace.resolve()
if not (workspace/'measurements.json').exists():raise ValueError('Test batch is incomplete')
paths=sorted(p for p in workspace.rglob('*') if p.is_file())
if any(p.is_symlink() for p in workspace.rglob('*')):raise ValueError('Workspace contains symlinks')
manifest={}
args.output.parent.mkdir(parents=True,exist_ok=True)
with args.output.open('xb') as compressed:
    with gzip.GzipFile(filename='',mode='wb',fileobj=compressed,mtime=0,compresslevel=6) as stream:
        with tarfile.open(fileobj=stream,mode='w|') as archive:
            for path in paths:
                content=path.read_bytes()
                relative=path.relative_to(workspace).as_posix()
                manifest[relative]={'bytes':len(content),'sha256':hashlib.sha256(content).hexdigest()}
                info=archive.gettarinfo(str(path),arcname='experiment_002/'+relative)
                info.mtime=0;info.uid=0;info.gid=0;info.uname='';info.gname=''
                with path.open('rb') as source:archive.addfile(info,source)
(HERE/'evidence/workspace_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
record={'experiment':'002_sun2021_ca2_frequency','release':'experiment-002-v1',
        'asset':{'filename':args.output.name,'bytes':args.output.stat().st_size,
                 'sha256':hashlib.sha256(args.output.read_bytes()).hexdigest(),
                 'url':'https://github.com/OgnjenX/ca2-circuit-experiments/releases/download/experiment-002-v1/'+args.output.name},
        'contains':['Original executable and generated configuration','Single-pulse calibration',
                    'All 120 test runs and full raw neuron/spike monitors','Retained setup reader failure'],
        'external_backend':'artifacts/experiment_001.json runtime asset; identical nominal library SHA',
        'copyrighted_source_figure_included':False}
(HERE/'evidence/archive.json').write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps(record,indent=2))
