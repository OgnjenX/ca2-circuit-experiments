from pathlib import Path
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
r=Path(__file__).resolve().parent;d=json.loads((r/'pyramidal-train-validation-results.json').read_text());task=json.loads((r/'task-probe-results.json').read_text());readout=json.loads((r/'readout-precision40vs80-results.json').read_text())
plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False})
fig,axes=plt.subplots(1,3,figsize=(13,4.8));names=['CA3_Pyramidal','MEC_LII_Stellate'];ticks=['CA3 input','MEC layer II input'];x=np.arange(2)
blocked=[d['results'][n]['blocked']['spike_count']['CA2_Pyramidal'] for n in names];fitted=[d['results'][n]['fitted']['spike_count']['CA2_Pyramidal'] for n in names]
axes[0].bar(x-.18,blocked,width=.36,label='Pyramidal inhibition removed',color='#777777');axes[0].bar(x+.18,fitted,width=.36,label='Fitted inhibition intact',color='#276994');axes[0].set(yscale='log',xticks=x,xticklabels=ticks,ylabel='CA2 pyramidal spikes in 250 ms (log scale)',title='Inhibition changes pathway responses',ylim=(10,3000000));axes[0].legend(fontsize=8,loc='upper right')
for positions,values in [(x-.18,blocked),(x+.18,fitted)]:
 for pos,v in zip(positions,values):axes[0].text(pos,v*1.15,f'{v:,}',ha='center',fontsize=8)
t=np.arange(250)-50
for n,label,color in zip(names,ticks,['#276994','#c47120']):axes[1].plot(t,d['results'][n]['fitted']['mean_voltage_trace'],label=label,color=color)
for pulse in range(5):axes[1].axvline(pulse*10,color='#aaaaaa',lw=.5,alpha=.5)
axes[1].set(xlabel='Time after first pulse (ms)',ylabel='Mean voltage, first 128 CA2 cells (mV)',title='Fitted-model responses',xlim=(-10,200));axes[1].legend(fontsize=9)
labels=['CA3 train','MEC train','Task alone','Task + CA3','CA1 replay']
values=[max(z['relative_difference'] for z in d['numerical_checks'][n]['populations'].values())*100 for n in names]+[max(z['relative_difference'] for z in task['results'][ctx]['checks'].values())*100 for ctx in ['0','1']]+[max(z['relative_difference'] for c in readout['results'] for z in c['count_checks'].values())*100]
axes[2].barh(labels,values,color='#276994');axes[2].axvline(5,color='#9e3c31',ls='--',label='Preset 5% limit');axes[2].set(xlabel='Largest population spike-count difference (%)',title='Higher precision checks',xlim=(0,6));axes[2].legend(fontsize=8,loc='lower right')
fig.suptitle('Validation checks for the revised CA2-centered model',fontsize=14)
fig.text(.035,.025,'Model seed 20; core traces/counts at 20 substeps/ms; five pulses at 100 Hz. GABAa reversal assumed −77.8 mV; fitted inhibitory-to-pyramidal gain 100.\nCore checks: RK4 20 versus 40 substeps/ms. CA1 check: 40 versus 80. These checks support numerical use, not biological validation.',fontsize=9)
fig.tight_layout(rect=(0,.13,1,.92));out=r/'figures';out.mkdir(exist_ok=True);fig.savefig(out/'targeted-model-validation.png',dpi=180);fig.savefig(out/'targeted-model-validation.pdf')
(out/'targeted-model-validation-data.json').write_text(json.dumps({'blocked_spikes':blocked,'fitted_spikes':fitted,'maximum_precision_differences_percent':dict(zip(labels,values)),'sources':['pyramidal-train-validation-results.json','task-probe-results.json','readout-precision40vs80-results.json']},indent=2))
