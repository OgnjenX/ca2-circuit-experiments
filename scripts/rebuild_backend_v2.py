"""Build separately versioned corrected dynamics; preserve historical source checks."""
import argparse,json,subprocess,sys
from pathlib import Path
from _common import ROOT
from ca2lab.provenance import sha256,verify_file
p=argparse.ArgumentParser(description=__doc__);p.add_argument('destination',type=Path);p.add_argument('--prepare-only',action='store_true');a=p.parse_args();a.destination=a.destination.resolve()
subprocess.run([sys.executable,str(ROOT/'scripts/rebuild_backend.py'),str(a.destination),'--prepare-only'],check=True)
identity=json.loads((ROOT/'simulators/carlsim4/synapse_dynamics_v2.json').read_text());patch=ROOT/'simulators/carlsim4'/identity['patch'];verify_file(patch,identity['patch_sha256'])
source=a.destination/'backend'
with patch.open('rb') as stream,(a.destination/'v2-patch.log').open('w') as log:subprocess.run(['patch','--batch','--fuzz=0','-p1'],cwd=source,stdin=stream,stdout=log,stderr=subprocess.STDOUT,check=True)
for name,digest in identity['changed_source_sha256'].items():verify_file(source/name,digest)
record={'identity':identity,'historical_sources_verified_before_v2_patch':True}
if not a.prepare_only:
 with (a.destination/'v2-build.log').open('w') as log:subprocess.run(identity['build_command'],cwd=source,stdout=log,stderr=subprocess.STDOUT,check=True)
 record['library_sha256']=sha256(source/'libcarlsim.a.4.0.0')
(a.destination/'v2-build.json').write_text(json.dumps(record,indent=2)+'\n')
