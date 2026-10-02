"""Draw scientific figures from verified compact evidence; does not score results."""
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

HERE=Path(__file__).resolve().parent
load=lambda name:json.loads((HERE/name).read_text())
results=load('evidence/results.json')
source=load('source_targets.json')['points']
levels=load('protocol.json')['calibration_amplitudes_mV']
colors=['#0072B2','#D55E00','#009E73']
plt.rcParams.update({'font.size':11,'axes.spines.top':False,'axes.spines.right':False,
                     'svg.fonttype':'none','figure.facecolor':'white'})
figures=HERE/'figures'
figures.mkdir(exist_ok=True)

def export(fig,name):
    fig.savefig(figures/(name+'.png'),dpi=180,bbox_inches='tight')
    fig.savefig(figures/(name+'.svg'),bbox_inches='tight')
    plt.close(fig)

fig,ax=plt.subplots(figsize=(9.5,5.8))
x=[p['frequency_Hz'] for p in source]
y=[p['mean'] for p in source]
lo=[p['interval'][0] for p in source]
hi=[p['interval'][1] for p in source]
ax.fill_between(x,lo,hi,color='#cccccc',alpha=.45,label='Conservative digitized compatibility band')
ax.errorbar(x,y,yerr=[p['SEM_upper_bound'] for p in source],fmt='o-',color='#333333',
            capsize=4,label='Paper CA2 + APV: digitized mean / SEM upper bound')
for level,color in zip(levels,colors):
    rows=sorted((r for r in results['comparisons'] if r['target_single_EPSP_mV']==level),key=lambda r:r['frequency_Hz'])
    xx=[r['frequency_Hz'] for r in rows]
    yy=[r['model_mean_ratio'] if r['eligible_all_seeds'] else np.nan for r in rows]
    ax.plot(xx,yy,'s--',ms=5,color=color,label=f'Model: single-pulse setup {level:.2f} mV')
    ax.fill_between(xx,[r['model_seed_min'] if r['eligible_all_seeds'] else np.nan for r in rows],
                    [r['model_seed_max'] if r['eligible_all_seeds'] else np.nan for r in rows],color=color,alpha=.25)
ax.axhline(1,color='#999999',lw=.9,ls=':')
ax.set(xlabel='Input train frequency (Hz)',ylabel='Fifth EPSP / first EPSP',xticks=x,
       title='CA2 response to five cortical-input pulses',ylim=(-.6,4.9),xlim=(0,52))
ax.legend(loc='upper left',fontsize=9,frameon=False)
fig.text(.12,.005,'Primary comparisons: 30 and 50 Hz. Model bands are seed ranges, not animal uncertainty.\n'
         'Upper setup at 50 Hz omitted: one seed spiked. Absolute APV first-EPSP amplitude remains unknown.',fontsize=9)
fig.tight_layout(rect=(0,.07,1,1))
export(fig,'frequency_response')

fig,axes=plt.subplots(1,2,figsize=(11.5,4.8))
for trace,color in zip(load('evidence/trace_samples.json'),colors):
    axes[0].plot(trace['time_from_first_pulse_ms'],trace['normalized_mean_voltage'],
                 color=color,label=f"{trace['target_single_EPSP_mV']:.2f} mV setup")
for t in [0,20,40,60,80]:axes[0].axvline(t,color='#bbbbbb',lw=.75,ls=':')
axes[0].set(title='Model voltage during a 50 Hz train',xlabel='Time from first input pulse (ms)',
            ylabel='Depolarization / first EPSP',xlim=(-10,179))
axes[0].legend(fontsize=9,frameon=False)
for frequency,marker in [(30,'o'),(50,'s')]:
    rows=sorted((r for r in results['primary'] if r['frequency_Hz']==frequency),key=lambda r:r['target_single_EPSP_mV'])
    point=next(p for p in source if p['frequency_Hz']==frequency)
    color='#0072B2' if frequency==30 else '#D55E00'
    axes[1].axhspan(*point['interval'],color=color,alpha=.1)
    axes[1].axhline(point['mean'],color=color,ls=':',lw=1.5,label=f'Paper mean: {frequency} Hz')
    axes[1].plot(levels,[r['model_mean_ratio'] if r['eligible_all_seeds'] else np.nan for r in rows],
                 marker+'-',color=color,label=f'Model mean: {frequency} Hz')
axes[1].set(title='Fixed sensitivity scenarios',xlabel='Calibrated single-pulse setup (mV)',
            ylabel='Fifth EPSP / first EPSP',xticks=levels,ylim=(.8,4.5))
axes[1].legend(fontsize=9,frameon=False)
fig.text(.075,.005,'Left: average of individually normalized point-cell voltages, seed 201; input timing shown by dotted lines.\n'
         'Right: conservative graph bands; upper 50 Hz group omitted because one seed spiked. APV amplitude is unknown.',fontsize=9)
fig.tight_layout(rect=(0,.09,1,1))
export(fig,'traces_and_sensitivity')
