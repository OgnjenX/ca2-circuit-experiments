from pathlib import Path
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
root=Path(__file__).resolve().parent;data=json.loads((root/'physiology-default-results.json').read_text());r=data['results'][1]
plt.rcParams.update({'font.size':11,'axes.spines.top':False,'axes.spines.right':False})
fig,axes=plt.subplots(1,2,figsize=(11,4.7),gridspec_kw={'width_ratios':[1.4,1]})
t=np.arange(150)-50
axes[0].plot(t,r['traces']['0'],label='Inhibitory connections blocked',color='#c7781d',linewidth=2)
axes[0].plot(t,r['traces']['1'],label='Default inhibition intact',color='#286a9f',linestyle='--',linewidth=2)
axes[0].axvline(0,color='#777777',linewidth=.8);axes[0].set(xlabel='Time after CA3 pulse (ms)',ylabel='Mean CA2 voltage (mV)',title='Responses almost overlap',xlim=(-10,100));axes[0].legend(fontsize=9,loc='upper right')
axes[1].bar([0,1],[abs(r['inhibition_difference_population_min_mV']),13.8],color=['#286a9f','#666666'],width=.55)
axes[1].errorbar(1,13.8,yerr=2.4,color='black',capsize=5,fmt='none')
axes[1].set(xticks=[0,1],xticklabels=['Default model','Published experiment'],ylabel='Inhibitory effect magnitude (mV)',title='Inhibition is much weaker',ylim=(0,18))
axes[1].text(0,.65,'0.27',ha='center');axes[1].text(1,16.7,'13.8 ± 2.4',ha='center')
fig.suptitle('CA2 physiology check: excitation alone does not validate the circuit',fontsize=14)
fig.text(.05,.02,'Model: seed 20; 1,940 CA3 afferents; RK4 10 substeps/ms; first 128 CA2 cells.\nModel measure: minimum intact-minus-blocked mean waveform. Experiment: n=7, mean ± SEM (Chevaleyre & Siegelbaum, 2010, Fig. 3).',fontsize=9)
fig.tight_layout(rect=(0,.12,1,.92))
out=root/'figures';out.mkdir(exist_ok=True);fig.savefig(out/'default-inhibition-check.png',dpi=180);fig.savefig(out/'default-inhibition-check.pdf')
print(out/'default-inhibition-check.png')
