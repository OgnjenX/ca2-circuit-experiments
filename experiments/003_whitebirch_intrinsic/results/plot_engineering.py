"""Reproduce the engineering figure only; no biological comparison."""
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

if __name__ == '__main__':
    here=Path(__file__).resolve().parent
    rows=json.loads((here/'engineering_summary.json').read_text())['rows']
    figure,axes=plt.subplots(1,3,figsize=(12.5,4.2),layout='constrained')
    fields=['max_same_grid_crossing_error_ms','max_same_grid_reset_u_error_pA','max_cross_grid_crossing_error_ms']
    titles=['GPU vs independent reference','GPU vs reference reset recovery','GPU timestep refinement']
    labels=['Maximum crossing error (ms)','Maximum pre-reset u error (pA)','Maximum crossing difference (ms)']
    for axis,key,limit,title,label in zip(axes,fields,[.05,.01,.05],titles,labels):
        axis.plot([r['current_pA'] for r in rows],[r[key] for r in rows],'o-',color='#b54737',label='Maximum over declared grids')
        axis.axhline(limit,color='#222',linestyle='--',label=f'Preregistered limit {limit:g}')
        axis.set(xlabel='Added current (pA)',ylabel=label,title=title,ylim=(0,None))
        axis.grid(alpha=.18);axis.legend(fontsize=7)
    figure.suptitle('Experiment 003: primary GPU numerical verification failed',fontsize=13)
    figure.savefig(here/'numerical_verification.png',dpi=180)
    plt.close(figure)
