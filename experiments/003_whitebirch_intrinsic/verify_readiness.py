"""Verify the frozen pre-run record; never simulate or score incomplete targets."""
import argparse
import ast
import hashlib
import json
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def inspect():
    manifest = json.loads((HERE / 'preregistration_manifest.json').read_text())
    for name, digest in manifest['sha256'].items():
        actual = hashlib.sha256((HERE / name).read_bytes()).hexdigest()
        if actual != digest:
            raise ValueError(f'Frozen input changed: {name}')
    for name in ['reference.py', 'reference_carlsim.py', 'verify_readiness.py']:
        ast.parse((HERE / name).read_text())
    p = json.loads((HERE / 'protocol.json').read_text())
    m = json.loads((HERE / 'model_configuration.json').read_text())
    target = json.loads((HERE / 'target_data.json').read_text())
    rows = target['rows']
    if [r['current_pA'] for r in rows] != list(range(100, 1001, 100)):
        raise ValueError('Missing or duplicated current rows')
    for r in rows:
        if r['mean_Hz'] is None:
            if r['digitization_interval_Hz'] is not None:
                raise ValueError('Missing target has manufactured bounds')
        else:
            lo, hi = r['digitization_interval_Hz']
            if not 0 <= lo <= r['mean_Hz'] <= hi:
                raise ValueError('Invalid reading interval')
        if r['model_count'] is not None or r['residual_spikes_per_second'] is not None:
            raise ValueError('Blocked record contains production outcomes')
    q = m['parameters']
    v = m['holding_mV']
    u = q['b'] * (v - q['Vr'])
    bias = u - q['k'] * (v - q['Vr']) * (v - q['Vt'])
    if abs(u - m['u_hold_pA']) > 1e-10 or abs(bias - m['I_hold_pA']) > 1e-10:
        raise ValueError('Holding equilibrium mismatch')
    subprocess.run(['git', 'merge-base', '--is-ancestor', '81cbbb7', 'HEAD'],
                   cwd=ROOT, check=True)
    gates = {
        'all_ten_means': all(r['mean_Hz'] is not None for r in rows),
        'highest_resolution_official_asset_verified': p['gates']['highest_resolution_official_asset_verified'],
        'backend_choice_approved': p['gates']['backend_choice_approved'],
    }
    return {'record_integrity': 'pass', 'ready_for_production': all(gates.values()),
            'gates': gates, 'production_executed': False,
            'missing_target_currents_pA': [r['current_pA'] for r in rows if r['mean_Hz'] is None],
            'equilibrium': {'u_pA': u, 'Ihold_pA': bias},
            'frozen_record_commit': subprocess.check_output(
                ['git', 'log', '-1', '--format=%H', '--', str(HERE / 'preregistration_manifest.json')],
                cwd=ROOT, text=True).strip(),
            'tested_head': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--require-ready', action='store_true')
    args = parser.parse_args()
    result = inspect()
    print(json.dumps(result, indent=2))
    if args.require_ready and not result['ready_for_production']:
        raise SystemExit(2)
