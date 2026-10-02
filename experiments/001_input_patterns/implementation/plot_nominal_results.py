# Nominal plots only; final plotting script adds completed sensitivity results.
from pathlib import Path
import json,sys,os
sys.path.insert(0,str(Path(__file__).resolve().parent/'plot-deps'))
os.environ.setdefault('MPLCONFIGDIR','/tmp/ca2-matplotlib')
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import PercentFormatter
r=Path(__file__).resolve().parent;primary=json.loads((r/'reset-task-results.json').read_text());secondary=json.loads((r/'secondary-voltage-results.json').read_text());out=r/'figures';out.mkdir(exist_ok=True)
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
