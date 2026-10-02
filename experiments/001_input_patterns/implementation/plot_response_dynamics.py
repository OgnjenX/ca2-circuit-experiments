from pathlib import Path
import json,sys,os
sys.path.insert(0,str(Path(__file__).resolve().parent/'plot-deps'));os.environ.setdefault('MPLCONFIGDIR','/tmp/ca2-matplotlib')
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
r=Path(__file__).resolve().parent;d=json.loads((r/'response-dynamics-results.json').read_text());rows=d['trial_population_responses'];names=['CA2_Pyramidal','CA2_Basket','CA2_Wide_Arbor_Basket','CA2_Bistratified','CA2_SP_SR'];labels=['Pyramidal','Basket','Wide-arbor\nbasket','Bistratified','SP-SR']
plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False})
fig,ax=plt.subplots(figsize=(6.8,3.6));colors=['#276994','#b65f24']
for ctx in [0,1]:
 rates=np.array([[np.mean([a['response_rate_Hz_per_cell'] for a in rows if a['population']==name and a['condition']=='core' and a['context']==ctx and a['network_seed']==seed]) for name in names] for seed in range(31,36)])
 x=np.arange(5)+(ctx-.5)*.32;ax.bar(x,rates.mean(0),width=.29,color=colors[ctx],alpha=.8,label=['Cortical input alone','With delayed CA3 input'][ctx])
 for i,rate in enumerate(rates):ax.scatter(x+(i-2)*.02,rate,color='black',s=9,zorder=3)
ax.set(xticks=np.arange(5),xticklabels=labels,yscale='log',ylabel='Response spikes per cell per second');fig.suptitle('CA2 activity under the two input contexts',fontsize=12,y=.98);fig.legend(*ax.get_legend_handles_labels(),fontsize=8,loc='upper center',bbox_to_anchor=(.5,.91),ncol=2,frameon=False);fig.tight_layout(rect=(0,0,1,.85));out=r/'figures';fig.savefig(out/'response-dynamics.png',dpi=220);fig.savefig(out/'response-dynamics.pdf');plt.close(fig)
(out/'response-dynamics-source.json').write_text(json.dumps({'source':'response-dynamics-results.json','rate':'All modeled cells; response50-249ms. Bars are five-network means; points are network means.','limits':'Context comparisons use separately drawn0-2ms cortical jitter. Conditional on fitted inhibition. Logarithmic vertical scale; this is not steady in-vivo firing.'},indent=2))
