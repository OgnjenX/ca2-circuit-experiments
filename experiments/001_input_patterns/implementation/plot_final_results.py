from pathlib import Path
import json,sys,os
sys.path.insert(0,str(Path(__file__).resolve().parent/'plot-deps'))
os.environ.setdefault('MPLCONFIGDIR','/tmp/ca2-matplotlib')
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import PercentFormatter
r=Path(__file__).resolve().parent;primary=json.loads((r/'reset-task-results.json').read_text());secondary=json.loads((r/'secondary-voltage-results.json').read_text());sensitivity=json.loads((r/'sensitivity-results.json').read_text());out=r/'figures';out.mkdir(exist_ok=True)
plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False,'savefig.facecolor':'white'})
colors=['#276994','#b65f24','#3e805b','#7a558e','#bb823c'];conditions=['intact','blocked','scrambled'];labels=['Intact','Blocked','Scrambled'];seeds=[31,32,33,34,35]
for name,records,key,title in [('primary-decoding',primary['per_seed_context_condition'],'heldout_accuracy','Primary: identity information in CA1 spikes'),('secondary-decoding',secondary['per_seed_context_condition'],'accuracy','Secondary: identity information in CA1 voltage')]:
 fig,axes=plt.subplots(1,2,figsize=(6.8,3.25),sharey=True)
 for ctx,ax in enumerate(axes):
  for index,seed in enumerate(seeds):
   values=[]
   for condition in conditions:
    matches=[a[key] for a in records if a.get('network_seed',a.get('seed'))==seed and a['context']==ctx and a['condition']==condition];assert len(matches)==1;values.append(matches[0])
   offset=(index-2)*.05;ax.plot(np.arange(3)+offset,values,'o-',color=colors[index],alpha=.75,ms=4,lw=.7,label=f'Seed{seed}')
  ax.axhline(.5,color='#777777',ls='--',lw=.8);ax.set(xticks=np.arange(3),xticklabels=labels,ylim=(-.03,1.03),title=['Cortical input alone','With delayed CA3 input'][ctx]);ax.yaxis.set_major_formatter(PercentFormatter(1));ax.set_yticks([0,.25,.5,.75,1]);ax.set_xlabel('CA2 pyramidal output')
 axes[0].set_ylabel('Held-out identity accuracy');fig.suptitle(title,fontsize=12);fig.tight_layout(rect=(0,0,1,.93));fig.savefig(out/f'{name}.png',dpi=220);fig.savefig(out/f'{name}.pdf');plt.close(fig)
# Physiological response panel sized for a portrait report.
d=json.loads((r/'pyramidal-train-validation-results.json').read_text());fig,ax=plt.subplots(figsize=(6.8,3.2));t=np.arange(250)-50
for pathway,label,color in [('CA3_Pyramidal','CA3 input','#276994'),('MEC_LII_Stellate','MEC layer-II input','#b65f24')]:ax.plot(t,d['results'][pathway]['fitted']['mean_voltage_trace'],label=label,color=color)
for pulse in range(5):ax.axvline(pulse*10,color='#aaaaaa',lw=.4)
ax.set(xlim=(-10,130),xlabel='Time after first pulse (ms)',ylabel='Mean monitored CA2\npyramidal voltage (mV)',title='Fitted model: distinct responses to held-out pulse trains');ax.legend(fontsize=9);fig.tight_layout();fig.savefig(out/'physiology-report.png',dpi=220);plt.close(fig)
variants=sensitivity['variants'];fig,axes=plt.subplots(1,2,figsize=(6.8,4.2),sharey=True)
labels=[]
for v in variants:
 n=len(v['network_seeds']);labels.append(v['label']+f' (n={n})')
for ax,kind,title in zip(axes,['spikes','voltage'],['Primary spikes','Secondary voltage']):
 for i,v in enumerate(variants):
  effect=next(a for a in v['paired_effects'] if a['measure']==kind and a['comparison']=='intact_minus_scrambled');mean=effect['mean_difference'];ci=effect['descriptive_bootstrap95_interval']
  ax.plot(mean,i,'o' if ci is not None else 's',color='#276994',ms=4)
  if ci is not None:ax.plot(ci,[i,i],color='#276994',lw=1.2)
 ax.axvline(0,color='#777777',ls='--',lw=.8);ax.set(title=title,xlabel='Intact - scrambled accuracy');ax.xaxis.set_major_formatter(PercentFormatter(1));ax.set_xlim(-1.02,1.02)
axes[0].set(yticks=np.arange(len(labels)),yticklabels=labels);axes[0].invert_yaxis();axes[0].tick_params(axis='y',labelsize=8);fig.suptitle('Effect sensitivity: fixed analysis rules and matched inputs',fontsize=12);fig.tight_layout(rect=(0,0,1,.93));fig.savefig(out/'sensitivity-effects.png',dpi=220);fig.savefig(out/'sensitivity-effects.pdf');plt.close(fig)
(out/'final-figure-provenance.json').write_text(json.dumps({'primary-decoding':['reset-task-results.json','per_seed_context_condition.heldout_accuracy'],'secondary-decoding':['secondary-voltage-results.json','per_seed_context_condition.accuracy'],'physiology-report':['pyramidal-train-validation-results.json','results.*.fitted.mean_voltage_trace'],'sensitivity-effects':['sensitivity-results.json','variants.*.paired_effects.intact_minus_scrambled'],'notes':['Five model-network points, not animal replicates.','Single-network sensitivity has no confidence interval; square points denote n1.','Intervals are descriptive network bootstraps; not biological parameter confidence intervals.']},indent=2))
