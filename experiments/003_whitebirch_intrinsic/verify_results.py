"""Verify committed evidence consistency, without rerunning GPU/reference ODEs."""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ASSAY = Path(__file__).resolve().parent
REV = ASSAY / 'revisions/002'
ROOT = ASSAY.parents[1]
sys.path.insert(0, str(REV))
from numerics import validate_records
from analyze import primary_records, scoring_bounds


def main():
    manifest = json.loads((REV/'preregistration_manifest.json').read_text())
    for name, expected in manifest['sha256'].items():
        assert hashlib.sha256((ASSAY/name).read_bytes()).hexdigest() == expected, name
    freeze = subprocess.check_output(['git','log','-1','--format=%H','--',
        str(REV/'preregistration_manifest.json')],cwd=ROOT,text=True).strip()
    evidence = json.loads((ASSAY/'results/evidence_manifest.json').read_text())
    assert evidence['frozen_commit'] == freeze
    for name, expected in evidence['sha256'].items():
        assert hashlib.sha256((ASSAY/'results'/name).read_bytes()).hexdigest() == expected, name
    numerical = json.loads((ASSAY/'results/numerical_checks.json').read_text())
    assert numerical['frozen_commit'] == freeze
    recovery = ASSAY/'revisions/003'
    repair = json.loads((recovery/'preregistration_manifest.json').read_text())
    assert repair['source_freeze_commit'] == freeze
    for name, expected in repair['sha256'].items():
        assert hashlib.sha256((ASSAY/name).read_bytes()).hexdigest() == expected, name
    recovery_commit = subprocess.check_output(['git','log','-1','--format=%H','--',
        str(recovery/'preregistration_manifest.json')],cwd=ROOT,text=True).strip()
    assert numerical['recovery_commit'] == recovery_commit
    assert type(numerical['passed']) is bool
    assert {'numerical_checks.json','report.md','runtime_review.json','audit_native_trace.py'} <= set(evidence['sha256'])
    if numerical.get('incomplete_or_invalid'):
        assert numerical['passed'] is False and numerical.get('failure')
    else:
        recomputed = validate_records(numerical['records'])
        assert recomputed['passed'] == numerical['passed']
        assert recomputed['production_timestep_refinements'] == numerical['production_timestep_refinements']
        assert recomputed['comparability_unresolved'] == numerical['comparability_unresolved']
    results = ASSAY/'results'
    if numerical['passed']:
        records = primary_records(numerical)
        target = json.loads((REV/'target_data.json').read_text())
        expected = scoring_bounds({k:r['crossing_audit']['raw_counts']['pulse'] for k,r in records.items()},target['rows'])
        comparison = json.loads((results/'comparison.json').read_text())
        assert {'comparison.json','comparison.csv','comparison.png'} <= set(evidence['sha256'])
        for key, value in expected.items():
            assert comparison[key] == value, key
        assert comparison['measurement_comparability_unresolved'] == numerical['comparability_unresolved']
        for key, path in [('numerics',results/'numerical_checks.json'),('target',REV/'target_data.json')]:
            assert comparison['input_sha256'][key] == hashlib.sha256(path.read_bytes()).hexdigest()
        if comparison['input_sha256'].get('diagnostic'):
            assert comparison['input_sha256']['diagnostic'] == hashlib.sha256((results/'immediate_diagnostic.json').read_bytes()).hexdigest()
        assert (results/'comparison.csv').exists() and (results/'comparison.png').exists()
    else:
        assert not any((results/name).exists() for name in ('comparison.json','comparison.csv','comparison.png'))
        assert 'Biological discrepancy scoring' in (results/'report.md').read_text()
    print(f'Frozen inputs and compact evidence consistent at {freeze}; numerical gate passed={numerical["passed"]}.')
    print('This check does not rerun raw-trace integration, establish biological equivalence, or erase failed gates.')


if __name__ == '__main__':
    main()
