"""Separate source, frozen implementation, execution and scoring readiness."""
import argparse
import hashlib
import json
import math
import subprocess
from pathlib import Path

REV = Path(__file__).resolve().parent
ASSAY = REV.parents[1]
ROOT = ASSAY.parents[1]


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def check_build(record, pins):
    for key in ('library_sha256', 'header_sha256', 'executable_sha256',
                'harness_sha256', 'driver_sha256', 'backend_source_sha256'):
        if record.get(key) != pins.get(key):
            raise ValueError(f'Build differs from frozen identity: {key}')
    if record['compile_exit_code'] != 0 or record.get('archive_interface_object_selected') is not False:
        raise ValueError('Unverified native linkage')
    workspace = Path(record['command'][-1]).parent
    if not workspace.exists() or not Path(record['library']).exists():
        return False
    for filename, key in [('gpu_harness', 'executable_sha256'), ('assay_config.h', 'header_sha256')]:
        if digest(workspace/filename) != pins[key]:
            raise ValueError(f'Compiled artifact changed: {filename}')
    if digest(record['library']) != pins['library_sha256']:
        raise ValueError('Runtime library changed')
    for filename, expected in pins['backend_source_sha256'].items():
        if digest(Path(record['backend'])/filename) != expected:
            raise ValueError(f'Backend source changed: {filename}')
    return True


def inspect(build_record=None, numerical_record=None):
    manifest_path = REV/'preregistration_manifest.json'
    manifest = json.loads(manifest_path.read_text())
    for filename, expected in manifest['sha256'].items():
        path = ASSAY/filename
        if digest(path) != expected:
            raise ValueError(f'Frozen source/config changed: {filename}')
    protocol = json.loads((REV/'protocol.json').read_text())
    target = json.loads((REV/'target_data.json').read_text())
    rows = target['rows']
    source_sufficient = protocol['methods_verified'] and protocol['source_sufficient_for_conditional_bounds']
    if [r['current_pA'] for r in rows] != list(range(100,1001,100)):
        raise ValueError('Target coverage incomplete or duplicated')
    if digest(ASSAY/target['source_file']) != target['source_sha256']:
        raise ValueError('Target source checksum differs')
    for row in rows:
        interval = row.get('mean_interval_Hz')
        if not isinstance(interval, list) or len(interval) != 2:
            source_sufficient = False
            continue
        lo, hi = interval
        if not all(math.isfinite(x) for x in interval) or not 0 <= lo <= hi:
            raise ValueError('Invalid target reading interval')
        if row['mean_Hz'] is None:
            if row['current_pA'] != 100 or row['status'] != 'conditional_interval_censored_mean_no_point_estimate' or not target['conditional_assumption']:
                source_sufficient = False
        elif not lo <= row['mean_Hz'] <= hi:
            raise ValueError('Point mean outside reading interval')
        if row['SEM_Hz'] is not None:
            raise ValueError('This source revision has no recoverable SEM endpoints')
    frozen = True
    head = subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    commit = subprocess.check_output(['git','log','-1','--format=%H','--',str(manifest_path)],cwd=ROOT,text=True).strip()
    for filename in (*manifest['sha256'], str(manifest_path.relative_to(ASSAY))):
        rel = str((ASSAY/filename).relative_to(ROOT))
        result = subprocess.run(['git','show',f'{head}:{rel}'],cwd=ROOT,capture_output=True)
        if result.returncode or result.stdout != (ASSAY/filename).read_bytes():
            frozen = False
    record = json.loads(Path(build_record or REV/'build_record.json').read_text())
    runtime_available = check_build(record, manifest['runtime_pins'])
    review = json.loads((ASSAY/'preparation/gpu_review_final.json').read_text())
    frozen = frozen and bool(review['approved_for_numerical_execution'])
    dependencies = False
    try:
        import numpy, scipy
        dependencies = numpy.__version__ == '2.3.5' and scipy.__version__ == '1.16.3'
    except ImportError:
        pass
    ready = source_sufficient and frozen and runtime_available and dependencies
    numerical_pass = False
    comparable = False
    if numerical_record:
        numerical = json.loads(Path(numerical_record).read_text())
        numerical_pass = (numerical.get('passed') is True and len(numerical.get('records',[])) == 33
                          and numerical.get('frozen_commit') == commit)
        comparable = numerical_pass and numerical.get('comparability_unresolved') is False
    return {'tested_head':head,'frozen_commit':commit,
            'source_sufficient_for_conditional_bounds':bool(source_sufficient),
            'source_condition':'100pA marker plotted under red occluder; mean remains unidentified',
            'implementation_frozen':frozen,'pinned_runtime_available':runtime_available,
            'pinned_numerical_dependencies_available':dependencies,
            'ready_for_numerical_validation':ready,
            'numerically_valid_for_scoring':numerical_pass,
            'measurement_comparable':comparable,
            'population_biological_validation':'not established; no equivalence margin or cell/mouse covariance'}


if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--build-record',type=Path)
    p.add_argument('--numerical-record',type=Path)
    p.add_argument('--require-numerical-ready',action='store_true')
    p.add_argument('--require-scoring-ready',action='store_true')
    args=p.parse_args()
    result=inspect(args.build_record,args.numerical_record)
    print(json.dumps(result,indent=2))
    if args.require_numerical_ready and not result['ready_for_numerical_validation']:
        raise SystemExit(2)
    if args.require_scoring_ready and not result['numerically_valid_for_scoring']:
        raise SystemExit(2)
