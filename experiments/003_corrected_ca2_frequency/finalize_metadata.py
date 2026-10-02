"""Fill release labels from frozen run configurations without changing science or raw data.

The frozen controller emitted release in configuration.json but omitted it in
measurement rows. Preserve its original batch and derive this categorical label
from each configuration before the unchanged frozen analysis.
"""
import argparse,json,hashlib
from pathlib import Path
from experiment import load,save,sha,verify_frozen
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--workspace',type=Path,required=True);a=p.parse_args();w=a.workspace.resolve();frozen=verify_frozen(w)
original=w/'measurements-original.json';batch=w/'measurements.json'
if original.exists():raise ValueError('Metadata adapter already applied; refuse overwrite')
record=load(batch)
if record['frozen_sha256']!=sha(Path(__file__).parent/'frozen_configuration.json'):raise ValueError('Freeze mismatch')
protocol=load(Path(__file__).parent/'protocol.json')
expected={(release,selection['selected']['active'],seed,frequency,steps)
          for release in ['stp','static'] for selection in frozen['calibration']['selections']
          for seed in protocol['evaluation_seeds']
          for steps,frequencies in [(protocol['nominal_substeps'],protocol['frequencies_Hz']),(protocol['precision_substeps'],protocol['primary_frequencies_Hz'])]
          for frequency in frequencies}
rows=[];mapping={};keys=[]
for row in record['runs']:
    cfg_path=w/'runs'/row['label']/'configuration.json';cfg=load(cfg_path)
    if sha(cfg_path)!=row['configuration_sha256']:raise ValueError('Configuration changed')
    release=cfg['release']
    if release not in ['stp','static']:raise ValueError('Unknown release condition')
    expected_executable=(frozen['executable_sha256'] if release=='stp' else frozen['build_record']['static_executable_sha256'])
    if cfg['executable_sha256']!=expected_executable:raise ValueError('Condition/executable mismatch')
    if 'release' in row and row['release']!=release:raise ValueError('Conflicting release metadata')
    for field in ['seed','active','frequency_Hz','steps']:
        if row[field]!=cfg[field]:raise ValueError('Run/configuration coordinates differ')
    if row['label'] in mapping:raise ValueError('Duplicate run label')
    base={k:v for k,v in row.items() if k!='release'}
    original_values_sha256=hashlib.sha256(json.dumps(base,sort_keys=True).encode()).hexdigest()
    mapping[row['label']]={'configuration_sha256':sha(cfg_path),'release':release,'unchanged_measurement_values_sha256':original_values_sha256}
    keys.append((release,row['active'],row['seed'],row['frequency_Hz'],row['steps']))
    rows.append({**row,'release':release})
if len(keys)!=len(set(keys)) or set(keys)!=expected:raise ValueError('Missing/duplicate/unexpected runs; refuse metadata recovery')
if len({m['configuration_sha256'] for m in mapping.values()})!=len(mapping):raise ValueError('Configuration hashes are not one-to-one')
original.write_bytes(batch.read_bytes())
record['runs']=rows;record['metadata_repair']={'original_sha256':sha(original),'rule':'release copied only from checksum-verified configuration.json; no measurements or scores altered'}
save(batch,record)
save(Path(__file__).parent/'evidence/metadata_mapping.json',{'original_batch_sha256':sha(original),'adapted_batch_sha256':sha(batch),'runs':mapping,'coordinates_and_measurement_values_unchanged':True})
print(f'Added verified categorical release labels to {len(rows)} rows; original batch retained.')
