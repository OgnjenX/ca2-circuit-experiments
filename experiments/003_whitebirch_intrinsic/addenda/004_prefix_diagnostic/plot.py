"""Plot retained diagnostic states; performs no integration."""
import argparse
import csv
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

def read(path):
    with path.open() as stream:
        return np.array([[float(r[k]) for k in ('time_ms','v_mV','u_pA')] for r in csv.DictReader(stream)])

def main():
    p=argparse.ArgumentParser();p.add_argument('--raw',type=Path,required=True);p.add_argument('--native',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    r=json.loads((a.raw/'prefix_results.json').read_text());t=read(a.raw/'dop853_tight.csv');native=read(a.native)[:len(t)];mask=t[:,0]<=r['valid_comparison_end_ms']
    fig,axs=plt.subplots(2,1,figsize=(9,7),sharex=True,layout='constrained')
    curves=[('Native GPU − DOP853',native-t,'#bc5225'),('Float64 RK4 − DOP853',read(a.raw/'rk4_float64_exact_coefficients.csv')-t,'#175fc7'),('Rounded coefficients float64 − DOP853',read(a.raw/'rk4_float64_matched_float32_coefficients.csv')-t,'#79539c'),('Native GPU − scalar float32',native-read(a.raw/'rk4_float32_explicit_no_fma.csv'),'#25805b')]
    for ax,index,unit in zip(axs,(1,2),('Voltage difference (mV)','Recovery difference (pA)')):
        for label,difference,color in curves:ax.plot(t[mask,0],difference[mask,index],label=label,color=color,lw=1.2)
        ax.set_yscale('symlog',linthresh=1e-9);ax.set_ylabel(unit);ax.grid(alpha=.2);ax.axvline(100,color='gray',ls=':',lw=1)
    axs[0].legend(fontsize=8,loc='upper left');axs[0].set_title('One condition: 100 pA, 80 substeps/ms, common pre-threshold prefix')
    axs[1].set_xlabel('Time (ms); pulse starts at 100 ms')
    fig.savefig(a.output,dpi=180,bbox_inches='tight');plt.close(fig)

if __name__=='__main__':main()
