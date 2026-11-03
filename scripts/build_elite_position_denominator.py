#!/usr/bin/env python3
"""Validate and total the elite-position denominator components."""
from __future__ import annotations
import csv
from collections import defaultdict
from pathlib import Path

PATH = Path('data/denominator/elite_position_denominator.csv')

def main():
    rows=list(csv.DictReader(PATH.open()))
    sums=defaultdict(int)
    for r in rows:
        if r['component'] in {'A','B','C'}:
            sums[r['component']]+=int(r['value'])
    total=sum(sums.values())
    expected=next((int(r['value']) for r in rows if r['component']=='TOTAL'),None)
    print('A',sums['A']); print('B',sums['B']); print('C',sums['C']); print('TOTAL',total); print('CSV total',expected)
    if expected is not None and total != expected:
        raise SystemExit(f'total mismatch: computed {total}, CSV {expected}')
    # rewrite the TOTAL row in place
    for r in rows:
        if r['component']=='TOTAL':
            r['value']=str(total)
    with PATH.open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=rows[0].keys()); w.writeheader(); w.writerows(rows)

if __name__=='__main__': main()
