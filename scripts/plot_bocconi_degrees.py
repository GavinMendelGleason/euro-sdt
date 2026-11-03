#!/usr/bin/env python3
"""Bocconi degrees conferred: economics/management and law."""
import csv
from collections import defaultdict
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

rows=list(csv.DictReader(open('data/institutions/degrees_awarded.csv')))
series=defaultdict(list)
for r in rows:
    if r['institution_id']=='bocconi' and r['metric'] in ('degrees conferred','law degrees conferred'):
        series[r['programme']].append((int(r['year']),int(r['degrees'])))

fig,axs=plt.subplots(2,1,figsize=(9,6.2),sharex=True)
for ax,key,color in [(axs[0],'Economics/management (Economico)','#0072B2'),(axs[1],'Law (Giuridico / LMG/01)','#D55E00')]:
    pts=sorted(series[key])
    ax.plot([x for x,_ in pts],[y for _,y in pts],marker='o',markersize=4,linewidth=2,color=color)
    ax.axvline(2004,color='#888888',linestyle=':',linewidth=1)
    ax.text(2004.2, max(y for _,y in pts)*0.92,'2004 reform',fontsize=7,color='#666')
    ax.set_ylabel('Degrees')
    ax.set_title(key,loc='left',fontsize=11,fontweight='bold')
    ax.grid(axis='y',alpha=.25)
    ax.annotate(f'{pts[-1][1]:,}',xy=pts[-1],xytext=(-30,6),textcoords='offset points',fontsize=8,color=color)
axs[0].set_ylim(3000,4800)
axs[1].set_ylim(0,700)
axs[1].set_xlabel('Year')
axs[1].set_xticks([2002,2004,2008,2012,2016,2020,2024])
fig.suptitle('Bocconi University: degrees conferred',x=0.012,y=0.975,ha='left',fontsize=14,fontweight='bold')
fig.text(0.012,0.925,'Official USTAT laureati: economics/management discipline group and law group. 2004 reform break; 2025 is the latest year.',ha='left',fontsize=8,color='#555')
fig.tight_layout(rect=[0,0,1,0.90])
out=Path('assets/papers/methodology/bocconi-degrees.png')
fig.savefig(out,dpi=200,bbox_inches='tight',facecolor='white')
fig.savefig(out.with_suffix('.svg'),bbox_inches='tight',facecolor='white')
plt.close(fig);print(out)
