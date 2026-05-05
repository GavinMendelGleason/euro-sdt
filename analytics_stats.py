"""
analytics_stats.py — Data quality statistics page with dark-themed charts.

Shows coverage, completeness, source breakdown, and gap analysis.
"""
import sqlite3, os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import numpy as np
from collections import Counter
from datetime import date

DB_PATH = 'euro_sdt.db'
OUT_HTML = 'wiki/stats.html'
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
    # Add percentage labels
    for i, (c, t) in enumerate(zip(covered, totals)):
        ax.text(c + 0.5, i, f'{c}/{t} ({c/t*100:.0f}%)', va='center', fontsize=8, color='white')


def pie_chart(ax, labels, values, title):
    cm = plt.get_cmap('viridis')
    colors = [cm(i/len(labels)) for i in range(len(labels))]
    wedges, texts, autotexts = ax.pie(values, labels=None, autopct='%1.0f%%',
                                       colors=colors, startangle=140, pctdistance=0.85)
    ax.set_title(title, fontsize=13, pad=10, color='#00d2ff')
    ax.legend(wedges, [f'{l} ({v})' for l,v in zip(labels, values)], loc='center left',
              bbox_to_anchor=(1, 0.5), fontsize=8)


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

    # ── Build HTML ──────────────────────────────────────────────────────
    html = f'''<!DOCTYPE html><html lang="en"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Euro-SDT Data Statistics</title>
<style>
body{{background:#1a1a2e;color:#e0e0e0;font-family:system-ui,sans-serif;max-width:1000px;margin:0 auto;padding:20px}}
h1,h2{{color:#00d2ff;border-bottom:1px solid #333;padding-bottom:8px}}
img{{max-width:100%;border-radius:8px;margin:15px 0;box-shadow:0 4px 20px rgba(0,0,0,.5)}}
.stat-grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:15px;margin:20px 0}}
.stat-card{{background:#16213e;padding:15px;border-radius:8px;text-align:center}}
.stat-card .num{{font-size:32px;font-weight:bold;color:#e94560}}
.stat-card .label{{font-size:12px;color:#888;margin-top:5px}}
a{{color:#00d2ff}}
</style></head><body>
<h1>Data Statistics</h1>
<p><a href="index.md">← Back to Wiki</a> | Generated {TODAY}</p>

<div class="stat-grid">
<div class="stat-card"><div class="num">{data['total_facts']}</div><div class="label">Total verified facts</div></div>
<div class="stat-card"><div class="num">{data['total_entities']}</div><div class="label">Entities tracked</div></div>
<div class="stat-card"><div class="num">{data['comm_edu']}/{data['comm_total']}</div><div class="label">Commissioner education covered</div></div>
<div class="stat-card"><div class="num">{data['dg_edu']}/{data['dg_total']}</div><div class="label">DG/DDG education covered</div></div>
<div class="stat-card"><div class="num">{data['with_quote']}</div><div class="label">Facts with exact source quote</div></div>
<div class="stat-card"><div class="num">{data['conf_counts'].get('confirmed',0)}</div><div class="label">Confirmed facts</div></div>
</div>

<h2>Entity Overview</h2>
<img src="img/stats_overview.png" alt="Overview">

<h2>Source Quality</h2>
<img src="img/stats_sources.png" alt="Sources">

<h2>Data Gaps</h2>
<table style="width:100%;border-collapse:collapse;margin:20px 0">
<tr style="border-bottom:1px solid #333"><th style="text-align:left;padding:8px">Category</th><th style="text-align:right;padding:8px">Covered</th><th style="text-align:right;padding:8px">Total</th><th style="text-align:right;padding:8px">Gap</th></tr>'''
    
    for label, (covered, total) in data['pred_coverage'].items():
        gap = total - covered
        pct = covered/total*100 if total else 0
        html += f'<tr style="border-bottom:1px solid #222"><td style="padding:8px">{label}</td><td style="text-align:right;color:#00d2ff;padding:8px">{covered}</td><td style="text-align:right;padding:8px">{total}</td><td style="text-align:right;color:#e94560;padding:8px">{gap} ({100-pct:.0f}%)</td></tr>'
    
    html += '</table></body></html>'
    
    with open(OUT_HTML, 'w') as f:
        f.write(html)
    
    print(f'Generated stats page → {OUT_HTML}')


if __name__ == '__main__':
    main()
