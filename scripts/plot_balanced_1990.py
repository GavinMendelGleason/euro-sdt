#!/usr/bin/env python3
"""Four-institution balanced output per position, 1990-2024."""
import csv
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
rows=list(csv.DictReader(open('data/analysis/gating_balanced_1990_panel.csv')))
fig,ax=plt.subplots(figsize=(9,5.2))
ax.plot([int(r['year']) for r in rows],[float(r['per_1000_positions']) for r in rows],color='#0072B2',marker='o',markersize=3,linewidth=2)
ax.set_xlabel('Year');ax.set_ylabel('Aggregate output per 1,000 Commission + judicial positions')
fig.suptitle('Balanced four-institution output per position, 1990–2024',x=0.012,y=0.985,ha='left',fontsize=13,fontweight='bold')
fig.text(0.012,0.925,'College of Europe, Harvard, Stockholm and Georgetown; fixed n=4. Output measures still differ.',ha='left',fontsize=7.5,color='#555')
ax.grid(axis='y',alpha=.25)
fig.tight_layout(rect=[0,0,1,0.88])
out=Path('assets/papers/methodology/gating-balanced-1990-panel.png')
fig.savefig(out,dpi=200,bbox_inches='tight',facecolor='white');fig.savefig(out.with_suffix('.svg'),bbox_inches='tight',facecolor='white');plt.close(fig)
print(out);print(rows[0],rows[-1])
