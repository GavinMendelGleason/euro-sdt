"""
analytics_stats.py — Data quality statistics page with dark-themed charts.

Shows coverage, completeness, source breakdown, and gap analysis.
"""
import sqlite3, os, re
from collections import defaultdict, Counter
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
from datetime import date

DB_PATH = 'euro_sdt.db'
OUT_HTML = 'wiki/stats.md'
IMG_DIR = 'wiki/img'
TODAY = date.today().isoformat()
plt.style.use('dark_background')

def load_data():
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    
    data = {}
    # Total counts
    data['total_facts'] = db.execute("SELECT COUNT(*) FROM fact").fetchone()[0]
    data['total_entities'] = db.execute("SELECT COUNT(*) FROM entity").fetchone()[0]
    
    # Entity type counts
    data['commissioners'] = db.execute("SELECT COUNT(*) FROM entity WHERE type='person' AND category='commissioner'").fetchone()[0]
    data['dgs']  = db.execute("SELECT COUNT(*) FROM entity WHERE type='person' AND category='dg'").fetchone()[0]
    data['ddgs'] = db.execute("SELECT COUNT(*) FROM entity WHERE type='person' AND category='ddg'").fetchone()[0]
    data['cjeu'] = db.execute("SELECT COUNT(*) FROM entity WHERE type='person' AND category IN ('cjeu_judge','cjeu_ag')").fetchone()[0]
    data['orgs'] = db.execute("SELECT COUNT(*) FROM entity WHERE type='organisation'").fetchone()[0]
    
    # Coverage by predicate (how many entities have this fact type)
    data['pred_coverage'] = {}
    for pred_label, predicate in [
        ('Education', "educated_at"),
        ('Field of Study', "studied_field"),
        ('Degree', "held_degree"),
        ('Member of Org', "member_of"),
        ('Post-mandate', "post_mandate_occupation"),
        ('Portfolio', "held_portfolio"),
    ]:
        total_ppl = db.execute("SELECT COUNT(DISTINCT id) FROM entity WHERE type='person' AND category IN ('commissioner','dg','ddg','cjeu_judge','cjeu_ag')").fetchone()[0]
        with_fact = db.execute(f"SELECT COUNT(DISTINCT entity_id) FROM fact WHERE predicate='{predicate}'").fetchone()[0]
        data['pred_coverage'][pred_label] = (with_fact, total_ppl)
    
    # Commissioner education coverage
    data['comm_edu'] = db.execute("""SELECT COUNT(DISTINCT entity_id) FROM fact WHERE predicate='educated_at' AND entity_id IN (SELECT id FROM entity WHERE category='commissioner')""").fetchone()[0]
    data['comm_total'] = db.execute("SELECT COUNT(*) FROM entity WHERE category='commissioner'").fetchone()[0]
    
    # DG/DDG education coverage
    data['dg_edu'] = db.execute("""SELECT COUNT(DISTINCT entity_id) FROM fact WHERE predicate='educated_at' AND entity_id IN (SELECT id FROM entity WHERE category IN ('dg','ddg'))""").fetchone()[0]
    data['dg_total'] = data['dgs'] + data['ddgs']
    
    # Provenance quality
    data['with_quote'] = db.execute("SELECT COUNT(*) FROM provenance WHERE phrase_index > 0").fetchone()[0]
    data['name_ref']   = db.execute("SELECT COUNT(*) FROM provenance WHERE phrase_index = -1").fetchone()[0]
    data['file_ref']   = db.execute("SELECT COUNT(*) FROM provenance WHERE phrase_index = 0").fetchone()[0]
    
    # Confidence
    data['conf_counts'] = {}
    for row in db.execute("SELECT confidence, COUNT(*) as c FROM fact GROUP BY confidence").fetchall():
        data['conf_counts'][row['confidence']] = row['c']
    
    # Source breakdown
    data['sources'] = {}
    for row in db.execute("""SELECT c.source_name, COUNT(DISTINCT p.fact_id) as n FROM provenance p JOIN citation c ON p.citation_id=c.id GROUP BY p.citation_id ORDER BY n DESC LIMIT 6"""):
        data['sources'][row['source_name']] = row['n']
    
    db.close()
    return data


def bar_chart(ax, labels, values, title, color='#00d2ff', ylabel='Count'):
    bars = ax.bar(range(len(labels)), values, color=color, alpha=0.8, edgecolor='white', linewidth=0.5)
    ax.set_xticks(range(len(labels)))
    ax.set_xticklabels(labels, rotation=30, ha='right', fontsize=9)
    ax.set_title(title, fontsize=13, pad=10, color='#00d2ff')
    ax.set_ylabel(ylabel)
    ax.yaxis.set_major_locator(ticker.MaxNLocator(integer=True))
    # Add value labels on bars
    for bar in bars:
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height + 0.5, str(int(height)),
                ha='center', va='bottom', fontsize=8, color='white')


def coverage_bar(ax, labels, covered, totals):
    """Stacked bar showing covered vs total."""
    uncovered = [t - c for c, t in zip(covered, totals)]
    ax.barh(range(len(labels)), covered, color='#00d2ff', alpha=0.8, label='With data')
    ax.barh(range(len(labels)), uncovered, left=covered, color='#e94560', alpha=0.5, label='Missing')
    ax.set_yticks(range(len(labels)))
    ax.set_yticklabels(labels, fontsize=9)
    ax.set_title('Data Coverage', fontsize=13, pad=10, color='#00d2ff')
    ax.legend(loc='lower right', fontsize=8)
    # Label at end of each bar so it's visually tied to that bar
    x_max = max(totals)
    for i, (c, t) in enumerate(zip(covered, totals)):
        ax.text(t, i, f'  {c}/{t} ({c/t*100:.0f}%)', va='center', ha='left', fontsize=8, color='white')
    ax.set_xlim(right=x_max * 1.35)


def pie_chart(ax, labels, values, title):
    cm = plt.get_cmap('viridis')
    colors = [cm(i/len(labels)) for i in range(len(labels))]
    wedges, texts, autotexts = ax.pie(values, labels=None, autopct='%1.0f%%',
                                       colors=colors, startangle=140, pctdistance=0.85)
    ax.set_title(title, fontsize=13, pad=10, color='#00d2ff')
    ax.legend(wedges, [f'{l} ({v})' for l,v in zip(labels, values)], loc='center left',
              bbox_to_anchor=(1, 0.5), fontsize=8)


def generate_edu_trends(db):
    """Education clusters line chart (% of commissioners per term)."""
    COMM_ORDER = ['Santer','Prodi','Barroso I','Barroso II','Juncker','VdL I','VdL II']
    COMM_SIZES = {'Santer': 20, 'Prodi': 20, 'Barroso I': 30, 'Barroso II': 28,
                  'Juncker': 27, 'VdL I': 30, 'VdL II': 27}
    def normalise_comm(slug):
        joined = '-'.join(slug.replace('commission-','').split('-'))
        m = re.match(r'^vdl\W*(i{1,2})$', joined.lower())
        if m: return 'VdL I' if m.group(1) == 'i' else 'VdL II'
        m = re.match(r'^barroso\W*(i{1,2})$', joined.lower())
        if m: return 'Barroso I' if m.group(1) == 'i' else 'Barroso II'
        return joined.title()

    person_comms = defaultdict(set)
    for r in db.execute("SELECT e.name, f.object FROM fact f JOIN entity e ON e.id=f.entity_id WHERE f.predicate='served_on_commission' AND e.category='commissioner'"):
        person_comms[r[0]].add(normalise_comm(r[1]))

    person_edu = defaultdict(set)
    for r in db.execute("""SELECT e.name, TRIM(LOWER(obj.name)) FROM fact f
        JOIN entity e ON e.id=f.entity_id JOIN entity obj ON obj.id=f.object
        WHERE f.predicate='educated_at' AND e.category='commissioner'"""):
        inst = r[1]
        for canon, pats in [
            ("Sciences Po / ENA", ['sciences po','sciences-po','iep paris','ena','ecole nationale','cole nationale']),
            ("Oxbridge", ['oxford','cambridge']),
            ("LSE", ['london school','lse']),
            ("Harvard / Georgetown", ['harvard','georgetown']),
            ("College of Europe", ['college of europe']),
        ]:
            if any(re.search(p, inst, re.IGNORECASE) for p in pats):
                person_edu[r[0]].add(canon)
                break

    clusters = ["Sciences Po / ENA", "Oxbridge", "LSE", "Harvard / Georgetown", "College of Europe"]
    edu_pct = {c: [] for c in clusters}
    for comm in COMM_ORDER:
        people = {p for p, cs in person_comms.items() if comm in cs}
        total = len(people)
        for cl in clusters:
            n = sum(1 for p in people if cl in person_edu.get(p, set()))
            edu_pct[cl].append(round(n / total * 100, 1) if total else 0)

    fig, ax = plt.subplots(figsize=(13, 5.5))
    colors = ['#e94560','#00d2ff','#ff7f0e','#9467bd','#2ca02c']
    for ci, cl in enumerate(clusters):
        ax.plot(COMM_ORDER, edu_pct[cl], marker='o', linewidth=2.5, color=colors[ci], label=cl, markersize=8)
    ax.set_title('Commissioner Education Clusters (% of Commissioners)', fontsize=13, color='#00d2ff')
    ax.set_ylabel('% of Commissioners', fontsize=10)
    ax.legend(loc='center left', bbox_to_anchor=(1.02, 0.5), fontsize=9)
    ax.set_ylim(bottom=0)
    ax.yaxis.set_major_formatter(ticker.FormatStrFormatter('%.0f%%'))
    plt.tight_layout(rect=[0, 0, 0.85, 1])
    plt.savefig(f'{IMG_DIR}/stats_edu_trends.png', dpi=150, facecolor='#1a1a2e')
    plt.close()


def generate_atlanticist_trends(db):
    """Elite network organisation connections line chart."""
    COMM_ORDER = ['Santer','Prodi','Barroso I','Barroso II','Juncker','VdL I','VdL II']
    COMM_SIZES = {'Santer': 20, 'Prodi': 20, 'Barroso I': 30, 'Barroso II': 28,
                  'Juncker': 27, 'VdL I': 30, 'VdL II': 27}
    DISPLAY = {
        'commission-santer': 'Santer', 'commission-prodi': 'Prodi',
        'commission-barroso-i': 'Barroso I', 'commission-barroso-ii': 'Barroso II',
        'commission-juncker': 'Juncker', 'commission-vdl-i': 'VdL I',
        'commission-vdl-ii': 'VdL II',
    }
    def org_slug(n): return re.sub(r'[^a-z0-9]+', '-', n.lower()).strip('-')

    orgs = {
        'Bilderberg Group': 'bilderberg-group',
        'Trilateral Commission': 'trilateral-commission',
        'Atlantic Council': 'atlantic-council',
        'WEF': 'world-economic-forum',
        'Munich Security Conference': 'munich-security-conference',
        'Friends of Europe': 'friends-of-europe',
        'ECFR': 'european-council-on-foreign-relations-ecfr',
        'European Policy Centre': 'european-policy-centre',
        'GLOBSEC': 'glosec',
        'German Marshall Fund': 'german-marshall-fund',
        'European Leadership Network': 'european-leadership-network',
        'Bruegel': 'bruegel',
        'RAND Europe': 'rand-europe',
    }

    org_pct = {}
    for org_name, slug in orgs.items():
        pcts = {}
        for comm_slug, disp in DISPLAY.items():
            row = db.execute("""SELECT COUNT(DISTINCT f.entity_id) FROM fact f
                JOIN fact f2 ON f2.entity_id = f.entity_id AND f2.predicate='served_on_commission'
                WHERE f.predicate IN ('affiliated_with','member_of')
                AND f.object = ? AND f2.object = ?
                AND f.entity_id IN (SELECT id FROM entity WHERE category='commissioner')
            """, [slug, comm_slug]).fetchone()
            pcts[disp] = round(row[0] / COMM_SIZES[disp] * 100, 1)
        org_pct[org_name] = pcts

    active = [(n, p) for n, p in org_pct.items() if any(p[c] > 0 for c in COMM_ORDER)]
    active.sort(key=lambda x: -sum(x[1].values()))

    fig, ax = plt.subplots(figsize=(14, 5.5))
    org_colors = ['#e94560','#00d2ff','#ff7f0e','#9467bd','#2ca02c','#d62728',
                  '#8c564b','#17becf','#e377c2','#7f7f7f','#bcbd22','#1f77b4']
    for oi, (org_name, pcts) in enumerate(active):
        vals = [pcts[c] for c in COMM_ORDER]
        ax.plot(COMM_ORDER, vals, marker='o', linewidth=2.2, color=org_colors[oi], label=org_name, markersize=7)
    ax.set_title('Elite Network Ties (% of Commissioners)', fontsize=13, color='#00d2ff')
    ax.set_ylabel('% of Commissioners', fontsize=10)
    ax.legend(loc='center left', bbox_to_anchor=(1.02, 0.5), fontsize=8, ncol=2)
    ax.set_ylim(bottom=0)
    ax.yaxis.set_major_formatter(ticker.FormatStrFormatter('%.0f%%'))
    plt.tight_layout(rect=[0, 0, 0.82, 1])
    plt.savefig(f'{IMG_DIR}/stats_elite_network_trends.png', dpi=150, facecolor='#1a1a2e')
    plt.close()


def generate_sdt_charts(db):
    """SDT cross-reference: MEP-commissioner org overlap + circulation flow."""
    COMM_ORDER = ['Santer','Prodi','Barroso I','Barroso II','Juncker','VdL I','VdL II']
    DISPLAY = {
        'commission-santer':'Santer','commission-prodi':'Prodi',
        'commission-barroso-i':'Barroso I','commission-barroso-ii':'Barroso II',
        'commission-juncker':'Juncker','commission-vdl-i':'VdL I','commission-vdl-ii':'VdL II',
    }

    # Shared elite network overlap
    orgs_shared = []
    for r in db.execute("""
        SELECT obj.name,
               COUNT(DISTINCT CASE WHEN e.category='commissioner' THEN f.entity_id END) as comms,
               COUNT(DISTINCT CASE WHEN f.entity_id LIKE 'mep-%' THEN f.entity_id END) as meps
        FROM fact f JOIN entity obj ON obj.id = f.object
        LEFT JOIN entity e ON e.id = f.entity_id
        WHERE f.predicate IN ('affiliated_with','member_of')
        AND (e.category='commissioner' OR f.entity_id LIKE 'mep-%')
        GROUP BY obj.name HAVING comms >= 2 AND meps >= 1
        ORDER BY (comms + meps) DESC
    """):
        orgs_shared.append((r[0], r[1], r[2]))

    if orgs_shared:
        fig, ax = plt.subplots(figsize=(11, max(4, len(orgs_shared) * 0.5)))
        y_pos = range(len(orgs_shared))
        ax.barh([y + 0.2 for y in y_pos], [o[1] for o in orgs_shared], 0.35, color='#00d2ff', alpha=0.8, label='Commissioners')
        ax.barh([y - 0.2 for y in y_pos], [o[2] for o in orgs_shared], 0.35, color='#e94560', alpha=0.8, label='MEP Leaders')
        ax.set_yticks(y_pos); ax.set_yticklabels([o[0] for o in orgs_shared], fontsize=9)
        ax.set_title('Elite Network Overlap: Commissioners vs MEP Leaders', fontsize=13, color='#00d2ff')
        ax.legend(loc='lower right', fontsize=9)
        ax.xaxis.set_major_locator(ticker.MaxNLocator(integer=True))
        plt.tight_layout()
        plt.savefig(f'{IMG_DIR}/stats_sdt_overlap.png', dpi=150, facecolor='#1a1a2e')
        plt.close()

    # Circulation: EP leaders who became commissioners per term
    circulation = {}
    for comm_slug, disp in DISPLAY.items():
        count = db.execute("""SELECT COUNT(DISTINCT e.id) FROM entity e
            JOIN fact f ON f.entity_id = e.id AND f.predicate='served_on_commission'
            WHERE e.category='commissioner' AND f.object = ?
            AND LOWER(e.name) IN (SELECT LOWER(name) FROM entity WHERE category='mep_sdt')
        """, [comm_slug]).fetchone()[0]
        circulation[disp] = count

    fig, ax = plt.subplots(figsize=(10, 5))
    x = range(len(COMM_ORDER))
    vals = [circulation.get(c, 0) for c in COMM_ORDER]
    ax.bar(x, vals, color='#9467bd', alpha=0.8)
    ax.set_xticks(x); ax.set_xticklabels(COMM_ORDER, fontsize=9)
    ax.set_title('EP Leadership → Commission Circulation', fontsize=13, color='#00d2ff')
    ax.set_ylabel('Commissioners with EP Leadership Background')
    ax.yaxis.set_major_locator(ticker.MaxNLocator(integer=True))
    for xi, v in enumerate(vals):
        if v > 0: ax.text(xi, v + 0.1, str(v), ha='center', fontsize=10, color='white')
    plt.tight_layout()
    plt.savefig(f'{IMG_DIR}/stats_sdt_circulation.png', dpi=150, facecolor='#1a1a2e')
    plt.close()


def main():
    os.makedirs(IMG_DIR, exist_ok=True)
    data = load_data()

    # ── Page 1: Entity Overview ─────────────────────────────────────────
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle('Euro-SDT Data Statistics', fontsize=16, color='#00d2ff')
    
    # Entities by type
    entity_types = ['Commissioners', 'DGs', 'DDGs', 'CJEU', 'Organisations']
    entity_counts = [data['commissioners'], data['dgs'], data['ddgs'], data['cjeu'], data['orgs']]
    bar_chart(axes[0,0], entity_types, entity_counts, 'Entities by Type', '#e94560')
    
    # Facts by predicate
    pred_labels = list(data['pred_coverage'].keys())
    pred_values = [data['pred_coverage'][l][0] for l in pred_labels]
    pred_totals = [data['pred_coverage'][l][1] for l in pred_labels]
    coverage_bar(axes[0,1], pred_labels, pred_values, pred_totals)
    
    # Confidence distribution
    conf_labels = list(data['conf_counts'].keys())
    conf_values = [data['conf_counts'][l] for l in conf_labels]
    pie_chart(axes[1,0], conf_labels, conf_values, 'Fact Confidence')
    
    # Education coverage
    edu_labels = ['Commissioners', 'DG/DDG']
    edu_covered = [data['comm_edu'], data['dg_edu']]
    edu_totals = [data['comm_total'], data['dg_total']]
    coverage_bar(axes[1,1], edu_labels, edu_covered, edu_totals)
    
    plt.tight_layout()
    plt.savefig(f'{IMG_DIR}/stats_overview.png', dpi=150, facecolor='#1a1a2e')
    plt.close()

    # ── Page 2: Source Quality ──────────────────────────────────────────
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    fig.suptitle('Provenance & Source Quality', fontsize=16, color='#00d2ff')
    
    # Provenance quality
    prov_labels = ['Phrase-index\n(exact sentence)', 'Name-in-page\n(commission roster)', 'File-level\n(source documented)']
    prov_values = [data['with_quote'], data['name_ref'], data['file_ref']]
    bar_chart(axes[0], prov_labels, prov_values, 'Provenance Level', '#00d2ff')
    
    # Source types
    source_labels = list(data['sources'].keys())[:6]
    source_labels_pretty = [s[:50] for s in source_labels]
    source_values = [data['sources'][s] for s in source_labels[:6]]
    bar_chart(axes[1], source_labels_pretty, source_values, 'Facts by Source', '#9467bd')
    
    plt.tight_layout()
    plt.savefig(f'{IMG_DIR}/stats_sources.png', dpi=150, facecolor='#1a1a2e')
    plt.close()

    # ── Page 3: Education Trends ────────────────────────────────────────
    db2 = sqlite3.connect(DB_PATH)
    generate_edu_trends(db2)
    db2.close()

    # ── Page 4: Elite Network Trends ───────────────────────────────────────
    db3 = sqlite3.connect(DB_PATH)
    generate_atlanticist_trends(db3)
    db3.close()

    # ── Page 5: SDT Cross-Reference ──────────────────────────────────────
    db4 = sqlite3.connect(DB_PATH)
    generate_sdt_charts(db4)
    db4.close()

    # ── Build Markdown ──────────────────────────────────────────────────
    md = f'''---
id: stats
title: Data Statistics
type: stats
tags: [stats, analytics]
generated: {TODAY}
---

# Data Statistics

← [Back to Wiki](index.md)

## Summary

| Metric | Value |
|---|---|
| Total verified facts | {data['total_facts']} |
| Entities tracked | {data['total_entities']} |
| Commissioner education covered | {data['comm_edu']}/{data['comm_total']} |
| DG/DDG education covered | {data['dg_edu']}/{data['dg_total']} |
| Facts with exact source quote | {data['with_quote']} |
| Confirmed facts | {data['conf_counts'].get('confirmed',0)} |

## Entity Overview

![Overview](img/stats_overview.png)

## Source Quality

![Sources](img/stats_sources.png)

## Data Gaps

| Category | Covered | Total | Gap |
|---|---:|---:|---:|'''
    
    for label, (covered, total) in data['pred_coverage'].items():
        gap = total - covered
        pct = covered/total*100 if total else 0
        md += f'\n| {label} | {covered} | {total} | {gap} ({100-pct:.0f}%) |'
    
    md += f'''

## DG/DDG Education by Institution

![DG Education](img/stats_dg_edu.png)

## Commissioner Education Clusters by Commission

![Commissioner Education Time](img/stats_comm_edu_time.png)

## Education Clusters Over Time

![Education Trends](img/stats_edu_trends.png)

## Elite Network Ties

![Elite Network Trends](img/stats_elite_network_trends.png)

## SDT: Circulation & Overlap

![Elite Network Overlap](img/stats_sdt_overlap.png)

![EP Leadership to Commission Circulation](img/stats_sdt_circulation.png)
'''
    
    with open(OUT_HTML, 'w') as f:
        f.write(md)


if __name__ == '__main__':
    main()
