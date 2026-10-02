"""Describe exclusions and numerical limits without changing prospective scores."""
import argparse
import json
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'src'))
from ca2lab.monitors import read_spikes

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--workspace',type=Path,required=True)
args=parser.parse_args()
load=lambda name:json.loads((HERE/'evidence'/name).read_text())
rows=load('run_measurements.json');checks=load('numerical_checks.json')
by_key={(r['active'],r['seed'],r['frequency_Hz'],r['steps']):r for r in rows}
eligible=[c for c in checks if by_key[(c['active'],c['seed'],c['frequency_Hz'],20)]['eligible']]
def maxima(group):
    return {name:max(c[name] for c in group) for name in
            ['mean_ratio_difference','max_mean_peak_difference_mV','max_cell_ratio_difference']}
exclusions=[]
for row in rows:
    if row['eligible']:continue
    directory=args.workspace/'runs'/row['label']
    cfg=json.loads((directory/'configuration.json').read_text())
    spikes=read_spikes(directory/'results/spk_CA2_Pyramidal.dat',128,cfg['duration_ms'])
    exclusions.append({'label':row['label'],'reason':'Target spiking; EPSP comparison ineligible',
                       'spikes':[{'absolute_ms':int(r['t']),'cell_id':int(r['id'])} for r in spikes],
                       'baseline_mV':row['baseline_mV'],'baseline_drift_mV':row['max_baseline_drift_mV']})
record={'post_analysis_descriptive_audit':True,'primary_scores_changed':False,
        'eligible_pair_count':len(eligible),'all_pair_maxima':maxima(checks),
        'eligible_pair_maxima':maxima(eligible),'excluded_runs':exclusions,
        'numerical_limit':'The declared gates concern mean EPSP ratios and mean peaks, and unchanged eligibility/spike counts. They do not establish convergence of every cell or spike time. The ineligible spiking pair has a large individual-cell ratio difference and a 1ms spike-time difference.',
        'ineligible_aggregation_limit':'results.json retains all-run means and errors even for the ineligible upper 50Hz condition, for auditability. These numbers include a spike and are not valid subthreshold EPSP comparisons. Figures omit that group, without dropping a seed to rescue its score.'}
(HERE/'evidence/review_diagnostics.json').write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps(record,indent=2))
