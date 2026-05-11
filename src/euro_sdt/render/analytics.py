"""
analytics.py — Generate time-series graphs and aggregate charts from the database.

Produces an HTML page with dark-themed visualisations:
  - Time series: participation in educational institutions across commissions
  - Time series: membership in specific organisations across commissions
  - Pie charts: DG/DDG education and nationality aggregates

Usage:
    python analytics.py
    open wiki/analytics.html
"""

from euro_sdt.config import DB_PATH, DEEPSEEK_API_KEY, DEEPSEEK_API_URL, MANIFEST_DIR, WIKI_DIR, WIKI_IMG_DIR, WIKIDATA_SPARQL
import sqlite3
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import os, re
from collections import Counter
from datetime import date

DB_PATH = DB_PATH
OUT_HTML = 'wiki/analytics.html'
TODAY = date.today().isoformat()
plt.style.use('dark_background')

# Commission colours
COMM_COLORS = {
    'Santer':      '#1f77b4',
    'Prodi':       '#ff7f0e',
    'Barroso I':   '#2ca02c',
    'Barroso II':  '#d62728',
    'Juncker':     '#9467bd',
    'VdL I':       '#8c564b',
    'VdL II':      '#e377c2',
}

COMM_ORDER = ['Santer','Prodi','Barroso I','Barroso II','Juncker','VdL I','VdL II']

# ── Data loading ────────────────────────────────────────────────────────────

def load_data():
    db = sqlite3.connect(DB_PATH)
    
    # Commissioner facts by commission
    comm_map = {}
    for row in db.execute("""
        SELECT f.object as comm_id, e.name as entity_name, e.id as entity_id
        FROM fact f JOIN entity e ON e.id = f.entity_id
        WHERE f.predicate = 'served_on_commission'
    """):
        comm_name = row[0].replace('commission-','').replace('-',' ').title()
        comm_name = comm_name.replace('Vdl I','VdL I').replace('Vdl Ii','VdL II')
        comm_name = comm_name.replace('Barroso I','Barroso I').replace('Barroso Ii','Barroso II')
        for orig, fixed in [('Santer','Santer'),('Prodi','Prodi'),('Juncker','Juncker'),
                            ('Vdl I','VdL I'),('Vdl Ii','VdL II'),
                            ('Barroso I','Barroso I'),('Barroso Ii','Barroso II')]:
            if orig.lower() in comm_name.lower():
                comm_name = fixed; break
        name = row[1]
        if name not in comm_map:
            comm_map[name] = []
        comm_map[name].append(comm_name)

    # Education facts
    edu_facts = [(r[0], r[1], r[2], r[3], r[4]) for r in db.execute("""
        SELECT f.entity_id, e.name, f.object, f.start_date, f.confidence
        FROM fact f JOIN entity e ON e.id = f.entity_id
        WHERE f.predicate = 'educated_at'
    """)]

    # Member_of facts
    member_facts = [(r[0], r[1], r[2], r[3], r[4]) for r in db.execute("""
        SELECT f.entity_id, e.name, f.object, f.qualifier, f.confidence
        FROM fact f JOIN entity e ON e.id = f.entity_id
        WHERE f.predicate = 'member_of'
    """)]

    # DG/DDG education data
    dg_edu = [(r[0], r[1], r[2], r[3]) for r in db.execute("""
        SELECT f.entity_id, e.name, f.object, f.predicate
        FROM fact f JOIN entity e ON e.id = f.entity_id
        WHERE f.predicate IN ('studied_field','held_degree')
        AND e.category IN ('dg','ddg')
    """)]

    # DG/DDG nationality data
    dg_nat = [(r[0], r[1]) for r in db.execute("""
        SELECT e.name, e.country
        FROM entity e
        WHERE e.type = 'person' AND e.category IN ('dg','ddg') AND e.country != ''
    """)]

    db.close()
    return comm_map, edu_facts, member_facts, dg_edu, dg_nat


# ── Graph generators ────────────────────────────────────────────────────────

def time_series(ax, data, title, ylabel='Commissioners'):
    """Plot a stacked bar chart showing presence across commissions."""
    # data is dict: {label: [count_santer, count_prodi, ...]}
    bottom = [0] * 7
    handles = []
    for label, values in data.items():
        bar = ax.bar(COMM_ORDER, values, bottom=bottom, label=label, alpha=0.85)
        handles.append(bar)
        bottom = [b + v for b, v in zip(bottom, values)]

    ax.set_title(title, fontsize=13, pad=10)
    ax.set_ylabel(ylabel)
    ax.tick_params(axis='x', rotation=30)
    ax.yaxis.set_major_locator(ticker.MaxNLocator(integer=True))
    return handles


def single_line(ax, data, title, ylabel='Commissioners'):
    """Plot a simple line/bar showing count per commission for a single entity."""
    ax.bar(COMM_ORDER, data, color='#1f77b4', alpha=0.8, edgecolor='white', linewidth=0.5)
    ax.set_title(title, fontsize=12, pad=8)
    ax.set_ylabel(ylabel)
    ax.tick_params(axis='x', rotation=30)
    ax.yaxis.set_major_locator(ticker.MaxNLocator(integer=True))


def pie_chart(ax, labels, values, title, cmap='viridis'):
    """Plot a pie chart."""
    cm = plt.get_cmap(cmap)
    colors = [cm(i / len(labels)) for i in range(len(labels))]
    wedges, texts, autotexts = ax.pie(
        values, labels=None, autopct='%1.1f%%',
        colors=colors,
        startangle=140, pctdistance=0.85
    )
    ax.set_title(title, fontsize=12, pad=10)
    ax.legend(wedges, labels, title="", loc="center left",
              bbox_to_anchor=(1, 0.5), fontsize=9)
    for at in autotexts:
        at.set_fontsize(8)
        at.set_color('white')


# ── Main ────────────────────────────────────────────────────────────────────

def main():
    comm_map, edu_facts, member_facts, dg_edu, dg_nat = load_data()

    # Map person → commissions
    person_comms = {}
    for name, comms in comm_map.items():
        person_comms[name] = set(comm_name.replace('Barroso I I','Barroso I')
                                 .replace('Barroso Ii','Barroso II')
                                 .replace('Vdl I','VdL I')
                                 .replace('Vdl Ii','VdL II')
                                 .replace('I I','I') for comm_name in comms)

    # Build time series data for educational institutions
    INSTITUTIONS = [
        ('Sciences Po',     r'sciences\s*po|sciences-po'),
        ('ENA',             r'\bena\b|ecole nationale|enarque'),
        ('College of Europe', r'college of europe|coll.ge d.europe'),
        ('Oxford',          r'\boxford\b'),
        ('Cambridge',       r'\bcambridge\b'),
        ('LSE',             r'\blse\b|london school'),
        ('Harvard',         r'\bharvard\b'),
        ('ULB Brussels',    r'\bulb\b|universit.*libre.*bruxelles|free.*university.*brussels'),
        ('Georgetown',      r'georgetown'),
        ('Bocconi',         r'bocconi'),
    ]

    ORGS = [
        ('World Economic Forum',     r'world economic forum|wef'),
        ('Munich Security Conference', r'munich security|msc'),
        ('Atlantic Council',         r'atlantic council'),
        ('ECFR',                     r'\becfr\b|european council on foreign'),
        ('Friends of Europe',        r'friends of europe'),
        ('GLOBSEC',                  r'globsec'),
        ('European Leadership Network', r'european leadership'),
        ('Bilderberg',               r'bilderberg'),
        ('Trilateral Commission',    r'trilateral'),
    ]

    fig_count = 0
    edu_graphs = []
    org_graphs = []

    # ── Education time series ───────────────────────────────────────────────
    for inst_name, inst_pattern in INSTITUTIONS:
        counts = {c: 0 for c in COMM_ORDER}
        for fact in edu_facts:
            person = fact[1]
            inst = fact[2] or ''
            if not re.search(inst_pattern, inst, re.I): continue
            if person not in person_comms: continue
            for c in person_comms[person]:
                if c in counts:
                    counts[c] += 1

        # Deduplicate: one person counted once per commission
        counts = {c: 0 for c in COMM_ORDER}
        for fact in edu_facts:
            person = fact[1]
            inst = fact[2] or ''
            if not re.search(inst_pattern, inst, re.I): continue
            if person not in person_comms: continue
            seen_comms = set()
            for c in person_comms[person]:
                if c in counts and c not in seen_comms:
                    counts[c] += 1
                    seen_comms.add(c)

        if sum(counts.values()) == 0: continue

        fig, ax = plt.subplots(figsize=(8, 4))
        single_line(ax, [counts[c] for c in COMM_ORDER], f'{inst_name}', 'Attendees')
        fn = f'{WIKI_IMG_DIR}/edu_{fig_count}.png'
        os.makedirs(WIKI_IMG_DIR, exist_ok=True)
        plt.tight_layout()
        plt.savefig(fn, dpi=120, facecolor='#1a1a2e')
        plt.close()
        edu_graphs.append((f'{inst_name}', fn))
        fig_count += 1

    # ── Organisation membership time series ─────────────────────────────────
    for org_name, org_pattern in ORGS:
        counts = {c: 0 for c in COMM_ORDER}
        for fact in member_facts:
            person = fact[1]
            org = fact[2] or ''
            if not re.search(org_pattern, org, re.I): continue
            if person not in person_comms: continue
            seen_comms = set()
            for c in person_comms[person]:
                if c in counts and c not in seen_comms:
                    counts[c] += 1
                    seen_comms.add(c)

        if sum(counts.values()) == 0: continue

        fig, ax = plt.subplots(figsize=(8, 4))
        single_line(ax, [counts[c] for c in COMM_ORDER], f'{org_name}', 'Members')
        fn = f'{WIKI_IMG_DIR}/org_{fig_count}.png'
        os.makedirs(WIKI_IMG_DIR, exist_ok=True)
        plt.tight_layout()
        plt.savefig(fn, dpi=120, facecolor='#1a1a2e')
        plt.close()
        org_graphs.append((f'{org_name}', fn))
        fig_count += 1

    # ── DG/DDG education pie chart ──────────────────────────────────────────
    from collections import Counter
    edu_counter = Counter(f[2] for f in dg_edu if f[2])
    top_edu = edu_counter.most_common(8)
    labels_e = [t[0] for t in top_edu]
    values_e = [t[1] for t in top_edu]
    other = sum(v for l, v in edu_counter.items() if l not in labels_e)
    if other:
        labels_e.append('Other'); values_e.append(other)

    fig, ax = plt.subplots(figsize=(7, 5))
    pie_chart(ax, labels_e, values_e, 'DG/DDG Fields of Study')
    fn = 'wiki/img/dg_edu_pie.png'
    plt.tight_layout()
    plt.savefig(fn, dpi=120, facecolor='#1a1a2e')
    plt.close()
    edu_graphs.append(('DG/DDG Education (Pie)', fn))

    # ── DG/DDG nationality pie chart ────────────────────────────────────────
    CC = {'AUT':'Austria','BEL':'Belgium','BGR':'Bulgaria','CYP':'Cyprus','CZE':'Czechia',
          'DEU':'Germany','DNK':'Denmark','ESP':'Spain','EST':'Estonia','FIN':'Finland',
          'FRA':'France','GBR':'UK','GRC':'Greece','HRV':'Croatia','HUN':'Hungary',
          'IRL':'Ireland','ITA':'Italy','LTU':'Lithuania','LUX':'Luxembourg','LVA':'Latvia',
          'MLT':'Malta','NLD':'Netherlands','POL':'Poland','PRT':'Portugal','ROU':'Romania',
          'SVK':'Slovakia','SVN':'Slovenia','SWE':'Sweden'}
    nat_counter = Counter(CC.get(f[1], f[1]) for f in dg_nat)
    top_nat = nat_counter.most_common(10)
    labels_n = [t[0] for t in top_nat]
    values_n = [t[1] for t in top_nat]

    fig, ax = plt.subplots(figsize=(7, 5))
    pie_chart(ax, labels_n, values_n, 'DG/DDG Nationalities')
    fn = 'wiki/img/dg_nat_pie.png'
    plt.tight_layout()
    plt.savefig(fn, dpi=120, facecolor='#1a1a2e')
    plt.close()
    edu_graphs.append(('DG/DDG Nationalities (Pie)', fn))

    # ── Build HTML ──────────────────────────────────────────────────────────
    html_lines = [
        '<!DOCTYPE html><html lang="en"><head>',
        '<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">',
        '<title>Euro-SDT Analytics</title>',
        '<style>',
        'body{background:#1a1a2e;color:#e0e0e0;font-family:system-ui,sans-serif;max-width:900px;margin:0 auto;padding:20px}',
        'h1{color:#00d2ff;border-bottom:1px solid #333;padding-bottom:10px}',
        'h2{color:#00d2ff;margin-top:40px}',
        'img{max-width:100%;border-radius:8px;margin:10px 0;box-shadow:0 4px 20px rgba(0,0,0,.5)}',
        '.graph-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(400px,1fr));gap:20px;margin:20px 0}',
        '.graph-item{background:#16213e;padding:15px;border-radius:8px}',
        '.graph-item h3{color:#e94560;margin:0 0 10px 0;font-size:14px}',
        'a{color:#00d2ff}',
        '</style></head><body>',
        f'<h1>Euro-SDT Analytics</h1><p>Generated {TODAY}. Data from 1,421 verified facts.</p>',
        '<p><a href="index.md">← Back to Wiki</a></p>',
        '<h2>Education — Time Series</h2><p>Commissioner attendance at specific institutions across administrations.</p>',
        '<div class="graph-grid">',
    ]

    for title, fn in edu_graphs:
        if 'DG/DDG' in title: continue
        rel_fn = fn.replace(os.path.join(os.path.dirname(WIKI_IMG_DIR), ''),'')
        html_lines.append(f'<div class="graph-item"><h3>{title}</h3><img src="{rel_fn}" alt="{title}"></div>')

    html_lines.extend([
        '</div>',
        '<h2>Organisation Membership — Time Series</h2><p>Commissioner memberships in specific organisations across administrations.</p>',
        '<div class="graph-grid">',
    ])

    for title, fn in org_graphs:
        rel_fn = fn.replace(os.path.join(os.path.dirname(WIKI_IMG_DIR), ''),'')
        html_lines.append(f'<div class="graph-item"><h3>{title}</h3><img src="{rel_fn}" alt="{title}"></div>')

    html_lines.extend([
        '</div>',
        '<h2>DG/DDG Aggregate Statistics</h2>',
        '<div class="graph-grid">',
    ])

    for title, fn in edu_graphs + org_graphs:
        if 'DG/DDG' in title:
            rel_fn = fn.replace(os.path.join(os.path.dirname(WIKI_IMG_DIR), ''),'')
            html_lines.append(f'<div class="graph-item"><h3>{title}</h3><img src="{rel_fn}" alt="{title}"></div>')

    html_lines.extend(['</div>', '</body></html>'])

    with open(OUT_HTML, 'w') as f:
        f.write('\n'.join(html_lines))

    print(f'Generated {fig_count} graphs + 2 pie charts → {OUT_HTML}')


if __name__ == '__main__':
    main()
