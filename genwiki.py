"""
genwiki.py — Generate a structured, browsable wiki from the database.

Produces markdown with YAML frontmatter compatible with Astro and Obsidian.
Category pages aggregate entities by type, with clickable citation footnotes.

Directory structure:
  wiki/
    index.md                    — navigation hub
    commissions/{slug}.md       — commission member lists
    organisations/{slug}.md     — organisation profiles and member lists
    people/{slug}.md            — individual person pages
    education/{cluster}.md      — education clusters (Sciences Po, CoE, etc.)
    countries/{country}.md      — commissioners by country
    citations.md                — primary source index

Usage:
    python genwiki.py
"""
import sqlite3, os, re, json
from datetime import date

DB_PATH = 'euro_sdt.db'
WIKI_DIR = 'wiki'
TODAY = date.today().isoformat()


# ── Base templates ──────────────────────────────────────────────────────────

PREDICATE_LABEL = {
    'served_on_commission':  'Served on',
    'served_on_ep':          'EP Term',
    'held_portfolio':        'Portfolio',
    'nominated_by':          'Nominated by',
    'from_country':          'Country',
    'educated_at':           'Educated at',
    'studied_field':         'Field of study',
    'held_degree':           'Degree',
    'affiliated_with':       'Organisation affiliations',
    'member_of':             'Member of',
    'held_position':         'Position',
    'post_mandate_occupation':'Post-mandate',
    'classified_as':         'Classification',
    'funding_notes':         'Funding',
    'has_description':       'Description',
}

SECTION_ORDER = [
    'served_on_commission','served_on_ep','held_portfolio','nominated_by','from_country',
    'educated_at','studied_field','held_degree',
    'held_position','works_at',
    'affiliated_with','member_of','post_mandate_occupation',
    'classified_as','funding_notes','has_description',
]

CC = {
    'AUT':'Austria','BEL':'Belgium','BGR':'Bulgaria','CYP':'Cyprus','CZE':'Czechia',
    'DEU':'Germany','DNK':'Denmark','ESP':'Spain','EST':'Estonia','FIN':'Finland',
    'FRA':'France','GBR':'UK','GRC':'Greece','HRV':'Croatia','HUN':'Hungary',
    'IRL':'Ireland','ITA':'Italy','LTU':'Lithuania','LUX':'Luxembourg','LVA':'Latvia',
    'MLT':'Malta','NLD':'Netherlands','POL':'Poland','PRT':'Portugal','ROU':'Romania',
    'SVK':'Slovakia','SVN':'Slovenia','SWE':'Sweden',
}

# Education cluster definitions — only genuine elite pipelines, not national groupings.
# Institutions with 3+ attendees get individual pages. Clusters only where
# multiple institutions form a coherent elite circuit (e.g. Oxbridge, Sciences Po/ENA).
EDUCATION_CLUSTERS = [
    ('college-of-europe',     r'college of europe|college of bruges'),
    ('harvard-ivy',           r'harvard|yale|georgetown|mit\b|edmund a. walsh'),
    ('oxbridge',              r'oxford|cambridge'),
    ('sciences-po-ena',       r'sciences po|sciences-po|iep\b.*paris|\bena\b|ecole nationale.*admin|enarque'),
    # Individual elite-signalling institutions with 3+ attendees
    ('lse',                   r'london school of economics|\blse\b(?!.*conseil|.*false)'),
    ('ucl',                   r'university college london\b(?!.*louvain)'),
    ('ecole-polytechnique',    r'école polytechnique\b(?!.*fédérale)'),
    ('insead',                 r'\binsead\b'),
    ('bocconi',               r'\bbocconi\b'),
    ('sgh-warsaw',            r'sgh warsaw|warsaw school of economics'),
    ('university-of-bonn',    r'university of bonn\b|uni bonn|rheinische.*bonn'),
    ('university-of-cologne', r'university of cologne|universität zu köln'),
]


def slugify(text):
    import unicodedata
    text = unicodedata.normalize('NFD', text)
    text = ''.join(c for c in text if unicodedata.category(c) != 'Mn')
    text = re.sub(r'[^a-zA-Z0-9\s\-]', '', text)
    return text.strip().lower().replace(' ', '-').replace('--', '-')


def get_org_tags(db, entity_id, org_name):
    """Return Obsidian color tags based on organisation type.
    Priority: 1) Wikipedia-sourced classification, 2) name keywords, 3) connected people."""
    
    # 1. Check for Wikipedia-sourced classification fact
    classified = db.execute("""
        SELECT f.object FROM fact f
        WHERE f.entity_id = ? AND f.predicate = 'classified_as'
        LIMIT 1
    """, [entity_id]).fetchone()
    
    if classified:
        industry = classified[0].lower()
        if any(k in industry for k in ['financial', 'bank', 'insurance', 'investment', 'private equity']):
            return ['org', 'corporate', 'financial']
        if any(k in industry for k in ['aerospace', 'defence', 'defense', 'automotive', 'manufacturing', 'engineering']):
            return ['org', 'corporate', 'industrial']
        if any(k in industry for k in ['energy', 'oil', 'gas', 'utility', 'power']):
            return ['org', 'corporate', 'energy']
        if any(k in industry for k in ['technology', 'software', 'semiconductor', 'telecom', 'electronics']):
            return ['org', 'corporate', 'tech']
        if any(k in industry for k in ['pharma', 'healthcare', 'chemical', 'life sciences']):
            return ['org', 'corporate', 'healthcare']
        if any(k in industry for k in ['luxury', 'consumer', 'retail', 'food', 'beverage']):
            return ['org', 'corporate', 'consumer']
        return ['org', 'corporate']
    
    # Rest of classification by keywords + connected people...
    name_lower = org_name.lower()
    
    # Political parties
    party_keywords = ['party', 'parti', 'partido', 'partei', 'partit', 'socialist', 'communist',
                      'christian democrat', 'conservative', 'liberal', 'green party', 'people\'s party',
                      'labour party', 'social democratic', 'popular party', 'republican']
    if any(k in name_lower for k in party_keywords):
        return ['org', 'political-party']
    
    # Parliamentary/government bodies
    gov_keywords = ['parliament', 'congress', 'senate', 'chamber of deputies', 'bundestag',
                    'national assembly', 'diet', 'sejm', 'seimas', 'council of ministers',
                    'committee on', 'delegation to', 'parliamentary assembly']
    if any(k in name_lower for k in gov_keywords):
        return ['org', 'government-body']
    
    # Corporate/industry
    corp_keywords = ['bank', 'insurance', 'energy', 'oil', 'gas', 'steel', 'chemical', 'pharma',
                     'automotive', 'aerospace', 'telecom', 'technology',
                     'airbus', 'safran', 'rheinmetall', 'leonardo', 'thales',
                     'siemens', 'sap', 'asml', 'infineon',
                     'shell', 'bp', 'total', 'eni', 'enel', 'iberdrola',
                     'santander', 'bnp', 'deutsche bank', 'ing', 'bbva', 'unicredit',
                     'allianz', 'axa', 'renault', 'volkswagen', 'stellantis', 'bmw',
                     'mercedes', 'lvmh', 'l\'oréal', 'sanofi', 'bayer',
                     'goldman', 'morgan stanley', 'ubs', 'credit suisse', 'barclays', 'hsbc',
                     'merrill', 'mckinsey', 'boston consulting', 'kpmg', 'deloitte', 'pwc',
                     'ernst', 'accenture', 'blackrock', 'blackstone']
    if any(k in name_lower for k in corp_keywords):
        return ['org', 'corporate']
    
    # Industry associations / business networks
    industry_keywords = ['round table', 'chamber of commerce', 'business association',
                         'industry association', 'financial services', 'insurance forum',
                         'banking federation', 'employers', 'entrepreneurs']
    if any(k in name_lower for k in industry_keywords):
        return ['org', 'industry-association']
    
    # Think tanks
    thinktank_keywords = ['think tank', 'policy institute', 'research institute', 'policy centre',
                          'policy center', 'foundation', 'institute for', 'centre for',
                          'center for', 'council on foreign', 'friends of europe',
                          'atlantic council', 'ecfr', 'bruegel', 'ceps', 'trilateral',
                          'bilderberg', 'munich security']
    if any(k in name_lower for k in thinktank_keywords):
        return ['org', 'think-tank']
    
    # Check connected entity types from DB
    connected_cats = db.execute("""
        SELECT DISTINCT e.category FROM fact f
        JOIN entity e ON e.id = f.entity_id
        WHERE f.predicate IN ('affiliated_with','member_of') AND f.object = ?
    """, [entity_id]).fetchall()
    connected = {r[0] for r in connected_cats}
    
    # Priority: commissioner signals think-tank, MEP signals political, corporate last
    if 'commissioner' in connected:
        return ['org', 'think-tank']
    if 'mep_sdt' in connected:
        return ['org', 'political-party']
    if 'corporate_elite' in connected:
        return ['org', 'corporate']
    
    # Default
    return ['org', 'org-generic']


def get_person_tags(category):
    """Return Obsidian graph color tags based on category."""
    mapping = {
        'commissioner':    ['person', 'commissioner', 'political-elite'],
        'mep_sdt':         ['person', 'mep', 'political-elite'],
        'corporate_elite': ['person', 'corporate', 'economic-elite'],
        'dg':              ['person', 'dg', 'administrative-elite'],
        'ddg':             ['person', 'ddg', 'administrative-elite'],
        'cjeu_judge':      ['person', 'cjeu', 'judicial-elite'],
        'cjeu_ag':         ['person', 'cjeu', 'judicial-elite'],
    }
    return mapping.get(category, ['person', category or 'unknown'])
    """Return Obsidian graph color tags based on category."""
    mapping = {
        'commissioner':    ['person', 'commissioner', 'political-elite'],
        'mep_sdt':         ['person', 'mep', 'political-elite'],
        'corporate_elite': ['person', 'corporate', 'economic-elite'],
        'dg':              ['person', 'dg', 'administrative-elite'],
        'ddg':             ['person', 'ddg', 'administrative-elite'],
        'cjeu_judge':      ['person', 'cjeu', 'judicial-elite'],
        'cjeu_ag':         ['person', 'cjeu', 'judicial-elite'],
    }
    return mapping.get(category, ['person', category or 'unknown'])


def frontmatter(fields):
    """Generate YAML frontmatter."""
    lines = ['---']
    for k, v in fields.items():
        if isinstance(v, list):
            lines.append(f'{k}:')
            for item in v:
                lines.append(f'  - {item}')
        elif v is not None and v != '':
            lines.append(f'{k}: {v}')
    lines.append(f'generated: {TODAY}')
    lines.append('---')
    lines.append('')
    return '\n'.join(lines)


def entity_link(eid, name):
    """Link to another entity page."""
    safe = slugify(name)
    return f'[{name}](../people/{safe}.md)'


def fetch_facts_grouped(db, entity_id):
    """Return facts grouped by predicate."""
    facts = db.execute(
        "SELECT * FROM fact WHERE entity_id = ? ORDER BY predicate, start_date",
        (entity_id,)).fetchall()
    grouped = {}
    for f in facts:
        pred = f[2]
        if pred not in grouped:
            grouped[pred] = []
        # Resolve entity_id references
        obj = f[3]
        if f[4] in ('entity_id', 'entity'):
            ref = db.execute("SELECT name FROM entity WHERE id = ?", (obj,)).fetchone()
            obj = ref[0] if ref else obj
        citations = db.execute(
            """SELECT c.source_name, c.url, p.quote_text, p.phrase_index, p.context_text
               FROM provenance p JOIN citation c ON p.citation_id = c.id
               WHERE p.fact_id = ?
               ORDER BY CASE WHEN p.citation_id = 'cit-wiki-' || ? THEN 0 ELSE 1 END""",
            (f[0], entity_id)).fetchall()
        grouped[pred].append({
            'object': obj,
            'qualifier': f[5] or '',
            'start_date': f[6] or '',
            'end_date': f[7] or '',
            'confidence': f[8],
            'citations': citations,
        })
    return grouped


def render_facts(grouped, heading_level=2):
    """Render facts as markdown with citation footnotes."""
    lines = []
    for predicate in SECTION_ORDER:
        if predicate not in grouped:
            continue
        label = PREDICATE_LABEL.get(predicate, predicate)
        lines.append(f'{"#" * heading_level} {label}')
        lines.append('')

        for fact in grouped[predicate]:
            obj = fact['object']
            qual = fact['qualifier']
            dates = ''
            if fact['start_date']:
                dates = fact['start_date'][:10] if len(str(fact['start_date'])) > 4 else str(fact['start_date'])
                if fact['end_date']:
                    dates += f' → {fact["end_date"][:10]}' if len(str(fact['end_date'])) > 4 else f' → {fact["end_date"]}'

            line = f'- **{obj}**'
            if qual and qual != obj:
                line += f' — {qual}'
            if dates:
                line += f' (*{dates}*)'
            lines.append(line)

            # Citation footnotes
            for cit in fact['citations']:
                src_name, url, quote, phrase_idx, context = cit
                if quote:
                    lines.append(f'  > "{quote[:200]}"')
                if url:
                    lines.append(f'  > 📎 [{src_name}]({url})')
                else:
                    lines.append(f'  > 📎 *{src_name}*')
                if context:
                    lines.append(f'  > {context[:150]}')
            lines.append('')

        lines.append('')
    return lines


# ── Page generators ─────────────────────────────────────────────────────────

def person_page(db, entity_id):
    """Generate a wiki page for a person."""
    ent = db.execute("SELECT * FROM entity WHERE id = ?", (entity_id,)).fetchone()
    if not ent: return None

    name = ent[1]
    etype = ent[2]
    category = ent[3] or ''
    country_code = ent[4] or ''

    fm = frontmatter({
        'id': entity_id,
        'title': name,
        'type': etype,
        'category': category,
        'country': country_code,
        'tags': get_person_tags(category),
    })

    lines = [fm, f'# {name}', '']
    if country_code:
        country_name = CC.get(country_code, country_code)
        lines.append(f'**{category.replace("_"," ").title()}** · [{country_name}](../countries/{country_code.lower()}.md)')
    lines.append('')
    lines.append(f'*← [Bodies](../bodies.md)*')
    lines.append('')

    grouped = fetch_facts_grouped(db, entity_id)
    lines.extend(render_facts(grouped))

    # Education backlinks
    edu_facts = grouped.get('educated_at', [])
    if edu_facts:
        lines.append('### Education clusters')
        clusters_found = set()
        for fact in edu_facts:
            obj_lower = fact['object'].lower()
            for cluster_id, pattern in EDUCATION_CLUSTERS:
                if re.search(pattern, obj_lower) and cluster_id not in clusters_found:
                    clusters_found.add(cluster_id)
                    lines.append(f'- [{cluster_id.replace("-"," ").title()}](../education/{cluster_id}.md)')

    return '\n'.join(lines)


def organisation_page(db, entity_id):
    """Generate a wiki page for an organisation."""
    ent = db.execute("SELECT * FROM entity WHERE id = ?", (entity_id,)).fetchone()
    if not ent: return None

    name = ent[1]
    fm = frontmatter({
        'id': entity_id,
        'title': name,
        'type': 'organisation',
        'tags': get_org_tags(db, entity_id, name),
    })

    lines = [fm, f'# {name}', '', '## Profile', '']

    # Classification facts
    grouped = fetch_facts_grouped(db, entity_id)
    for pred in ['classified_as', 'funding_notes', 'has_description']:
        if pred in grouped:
            for fact in grouped[pred]:
                lines.append(f'- {fact["object"]}')
    lines.append('')

    # Members (both member_of and affiliated_with)
    members = db.execute(
        "SELECT e.id, e.name FROM fact f JOIN entity e ON e.id = f.entity_id "
        "WHERE f.predicate IN ('member_of', 'affiliated_with') AND f.object = ? ORDER BY e.name",
        (entity_id,)).fetchall()
    if members:
        lines.append('## Members')
        lines.append(f'({len(members)} people)')
        lines.append('')
        for mid, mname in members:
            safe = slugify(mname)
            lines.append(f'- [{mname}](../people/{safe}.md)')
        lines.append('')

    return '\n'.join(lines)


def education_cluster_page(db, cluster_id, cluster_pattern):
    """Generate a page for an education cluster."""
    label = cluster_id.replace('-', ' ').title()
    fm = frontmatter({
        'id': cluster_id,
        'title': f'{label} — Education Cluster',
        'type': 'education_cluster',
        'tags': ['education', cluster_id],
    })

    lines = [fm, f'# {label}', '',
             f'Commissioners, MEP leaders, and officials who studied at or attended {label}.', '']

    # Find all educated_at facts matching this cluster
    members = {}
    for row in db.execute("""
        SELECT obj.name as inst_name, e.id as person_id, e.name as person_name, e.category
        FROM fact f JOIN entity e ON e.id = f.entity_id
        JOIN entity obj ON obj.id = f.object
        WHERE f.predicate = 'educated_at' AND e.type = 'person'
    """).fetchall():
        inst_name = row[0]
        if re.search(cluster_pattern, inst_name.lower()):
            pid, pname, cat = row[1], row[2], row[3] or ''
            if pname not in members:
                members[pname] = {'id': pid, 'category': cat, 'institutions': []}
            members[pname]['institutions'].append(inst_name)

    lines.append(f'## Attendees ({len(members)})')
    lines.append('')
    
    comms = {n: m for n, m in members.items() if 'commissioner' in (m['category'] or '').lower()}
    dgs   = {n: m for n, m in members.items() if m['category'] in ('dg','ddg')}
    meps  = {n: m for n, m in members.items() if m['category'] == 'mep_sdt'}
    other = {n: m for n, m in members.items() if n not in {**comms, **dgs, **meps}}

    if comms:
        lines.append('### Commissioners')
        for pname in sorted(comms):
            insts = ' | '.join(comms[pname]['institutions'])
            safe = slugify(pname)
            lines.append(f'- [{pname}](../people/{safe}.md) — {insts}')
        lines.append('')
    if meps:
        lines.append('### MEP Leaders')
        for pname in sorted(meps):
            insts = ' | '.join(meps[pname]['institutions'])
            safe = slugify(pname)
            lines.append(f'- [{pname}](../people/{safe}.md) — {insts}')
        lines.append('')
    if dgs:
        lines.append('### Directors-General & DDGs')
        for pname in sorted(dgs):
            insts = ' | '.join(dgs[pname]['institutions'])
            safe = slugify(pname)
            lines.append(f'- [{pname}](../people/{safe}.md) — {insts}')
        lines.append('')
    if other:
        lines.append('### Other')
        for pname in sorted(other):
            insts = ' | '.join(other[pname]['institutions'])
            safe = slugify(pname)
            lines.append(f'- [{pname}](../people/{safe}.md) — {insts}')
        lines.append('')

    return '\n'.join(lines)


def generate_all(db):
    """Generate all wiki pages."""
    os.makedirs(WIKI_DIR, exist_ok=True)
    for d in ['commissions','organisations','people','education','countries']:
        os.makedirs(os.path.join(WIKI_DIR, d), exist_ok=True)

    entities = db.execute("SELECT id, type, category, country FROM entity ORDER BY id").fetchall()
    count = 0

    for eid, etype, cat, country in entities:
        if etype == 'person':
            page = person_page(db, eid)
            subdir = 'people'
        elif etype == 'organisation':
            page = organisation_page(db, eid)
            subdir = 'organisations'
        elif etype == 'commission':
            page = commission_page(db, eid)
            subdir = 'commissions'
        else:
            continue

        if page:
            safe = slugify(db.execute("SELECT name FROM entity WHERE id=?", (eid,)).fetchone()[0])
            path = os.path.join(WIKI_DIR, subdir, f'{safe}.md')
            with open(path, 'w') as f:
                f.write(page)
            count += 1

    # Education cluster pages
    for cluster_id, pattern in EDUCATION_CLUSTERS:
        page = education_cluster_page(db, cluster_id, pattern)
        if page:
            path = os.path.join(WIKI_DIR, 'education', f'{cluster_id}.md')
            with open(path, 'w') as f:
                f.write(page)

    # Country pages
    cc_count = 0
    for cc_code, cc_name in CC.items():
        commissioners = db.execute(
            "SELECT id, name FROM entity WHERE country = ? AND type = 'person' ORDER BY name",
            (cc_code,)).fetchall()
        if not commissioners:
            continue
        cc_count += 1

        fm = frontmatter({'id': cc_code.lower(), 'title': cc_name, 'type': 'country', 'tags': ['country']})
        lines = [fm, f'# {cc_name}', '', f'## Commissioners ({len(commissioners)})', '']
        for pid, pname in commissioners:
            safe = slugify(pname)
            lines.append(f'- [{pname}](../people/{safe}.md)')
        lines.append('')

        path = os.path.join(WIKI_DIR, 'countries', f'{cc_code.lower()}.md')
        with open(path, 'w') as f:
            f.write('\n'.join(lines))

    print(f'Generated {count} entity pages + {len(EDUCATION_CLUSTERS)} education + {cc_count} country pages')

    # ── Index page ───────────────────────────────────────────────────────
    generate_index_page(db)


def generate_graph_config():
    """Generate .obsidian/graph.json with auto-coloring by tag."""
    os.makedirs(os.path.join(WIKI_DIR, '.obsidian'), exist_ok=True)
    config = {
        "collapse-filter": False, "search": "", "showTags": True,
        "showAttachments": False, "hideUnresolved": False, "showOrphans": True,
        "collapse-color-groups": False,
        "colorGroups": [
            {"query": "tag:#political-elite",       "color": {"a": 1, "rgb": 5077951}},
            {"query": "tag:#economic-elite",        "color": {"a": 1, "rgb": 16733525}},
            {"query": "tag:#administrative-elite",   "color": {"a": 1, "rgb": 4638335}},
            {"query": "tag:#judicial-elite",        "color": {"a": 1, "rgb": 10350619}},
            {"query": "tag:#political-party",        "color": {"a": 1, "rgb": 6553700}},
            {"query": "tag:#think-tank",             "color": {"a": 1, "rgb": 8421504}},
            {"query": "tag:#corporate",              "color": {"a": 1, "rgb": 16744576}},
            {"query": "tag:#government-body",        "color": {"a": 1, "rgb": 10092543}},
            {"query": "tag:#education",              "color": {"a": 1, "rgb": 16766720}},
            {"query": "tag:#hub",                    "color": {"a": 1, "rgb": 16777215}},
        ],
        "collapse-display": False, "showArrow": False, "textFadeMultiplier": 0,
        "nodeSizeMultiplier": 1, "lineSizeMultiplier": 1, "collapse-forces": False,
        "centerStrength": 0.5, "repelStrength": 10, "linkStrength": 1,
        "linkDistance": 250, "scale": 1,
    }
    with open(os.path.join(WIKI_DIR, '.obsidian', 'graph.json'), 'w') as f:
        json.dump(config, f, indent=2)


def generate_index_page(db):
    """Generate the root navigation page — minimal hub."""
    total_facts = db.execute("SELECT COUNT(*) FROM fact").fetchone()[0]
    total_entities = db.execute("SELECT COUNT(*) FROM entity").fetchone()[0]
    
    lines = [
        '---',
        'id: index',
        'title: Euro-SDT Wiki',
        'type: index',
        'tags: [index]',
        f'generated: {TODAY}',
        '---',
        '',
        '# Euro-SDT Wiki',
        '',
        f'*{total_facts} verified facts across {total_entities} entities. Citation-anchored knowledge graph.*',
        '',
        '## Navigation',
        '',
        '- **[Bodies](bodies.md)** — Commissioners, DGs, CJEU, MEP leaders, education clusters, countries',
        '- **[Statistics](stats.md)** — Data quality and coverage charts',
        '- **[Citations](citations.md)** — Primary source index',
        '',
    ]
    
    path = os.path.join(WIKI_DIR, 'index.md')
    with open(path, 'w') as f:
        f.write('\n'.join(lines))

    # ── Bodies index page ─────────────────────────────────────────────────
    generate_bodies_page(db)

    # ── Obsidian graph color config ──────────────────────────────────────
    generate_graph_config()


def generate_bodies_page(db):
    """Generate bodies.md index + sub-pages for each body type."""
    os.makedirs(os.path.join(WIKI_DIR, 'bodies'), exist_ok=True)
    lines = [
        '---',
        'id: bodies',
        'title: EU Institutional Bodies',
        'type: index',
        'tags: [index, bodies]',
        f'generated: {TODAY}',
        '---',
        '',
        '# EU Institutional Bodies',
        '',
        'All commissioners, Directors-General, Deputy Directors-General,',
        'MEP leaders, and Court of Justice members tracked in this database.',
        '',
    ]

    # ── Commissions (link to sub-page) ──────────────────────────────────
    comm_count = db.execute("SELECT COUNT(*) FROM entity WHERE type='commission'").fetchone()[0]
    lines.append('## [European Commissions](bodies/commissions.md)')
    lines.append(f'{comm_count} commissions (1995–2029)')
    lines.append('')

    # ── Directors-General (link to sub-page) ─────────────────────────────
    dg_count = db.execute("SELECT COUNT(*) FROM entity WHERE type='person' AND category IN ('dg','ddg')").fetchone()[0]
    lines.append('## [Directors-General & Deputy Directors-General](bodies/dgs.md)')
    lines.append(f'{dg_count} senior officials')
    lines.append('')

    # ── CJEU (link to sub-page) ──────────────────────────────────────────
    cjeu_count = db.execute("SELECT COUNT(*) FROM entity WHERE type='person' AND category IN ('cjeu_judge','cjeu_ag')").fetchone()[0]
    lines.append('## [Court of Justice (CJEU)](bodies/cjeu.md)')
    lines.append(f'{cjeu_count} members (judges + advocates general)')
    lines.append('')

    # ── MEPs (link to sub-page) ──────────────────────────────────────────
    mep_count = db.execute("SELECT COUNT(*) FROM entity WHERE category = 'mep_sdt'").fetchone()[0]
    if mep_count:
        lines.append('## [SDT-Relevant MEPs](bodies/meps.md)')
        lines.append(f'{mep_count} EP Presidents, Vice Presidents, committee chairs, group leaders')
        lines.append('')

    # ── Corporate Elites (link to sub-page) ──────────────────────────────
    corp_count = db.execute("SELECT COUNT(*) FROM entity WHERE category = 'corporate_elite'").fetchone()[0]
    if corp_count:
        lines.append('## [Transnational Corporate Elites](bodies/corporate.md)')
        lines.append(f'{corp_count} board members and CEOs of multi-European companies')
        lines.append('')

    # ── Education Clusters ───────────────────────────────────────────────
    lines.append('## [Education Clusters](bodies/education-clusters.md)')
    lines.append('Elite institution groupings (Sciences Po/ENA, Oxbridge, LSE, etc.)')
    lines.append('')

    # ── Countries ────────────────────────────────────────────────────────
    country_count = len([c for c in CC.keys() if os.path.exists(os.path.join(WIKI_DIR, 'countries', f'{c.lower()}.md'))])
    lines.append('## [Countries](bodies/countries.md)')
    lines.append(f'{country_count} member states')
    lines.append('')

    # Write main page
    with open(os.path.join(WIKI_DIR, 'bodies.md'), 'w') as f:
        f.write('\n'.join(lines))

    # ── Generate sub-pages ───────────────────────────────────────────────
    # DGs
    dg_lines = ['# Directors-General & Deputy Directors-General', '', f'{dg_count} senior officials', '']
    for row in db.execute("""
        SELECT e.name, e.category, f.object as dept
        FROM entity e LEFT JOIN fact f ON f.entity_id = e.id AND f.predicate = 'held_position'
        WHERE e.type = 'person' AND e.category IN ('dg','ddg')
        ORDER BY e.category DESC, e.name
    """).fetchall():
        safe = slugify(row[0])
        role = 'Director-General' if row[1] == 'dg' else 'Deputy Director-General'
        dept = str(row[2] or '')[:60]
        dg_lines.append(f'- [{row[0]}](../people/{safe}.md) — *{role}* — {dept}')
    with open(os.path.join(WIKI_DIR, 'bodies/dgs.md'), 'w') as f:
        f.write('\n'.join(dg_lines))

    # CJEU
    cjeu_lines = ['# Court of Justice (CJEU)', '', f'{cjeu_count} members', '']
    judges = db.execute("SELECT name FROM entity WHERE type='person' AND category='cjeu_judge' ORDER BY name").fetchall()
    ags = db.execute("SELECT name FROM entity WHERE type='person' AND category='cjeu_ag' ORDER BY name").fetchall()
    if judges:
        cjeu_lines.append(f'## Judges ({len(judges)})')
        cjeu_lines.append('')
        for r in judges:
            cjeu_lines.append(f'- [{r[0]}](../people/{slugify(r[0])}.md)')
        cjeu_lines.append('')
    if ags:
        cjeu_lines.append(f'## Advocates General ({len(ags)})')
        cjeu_lines.append('')
        for r in ags:
            cjeu_lines.append(f'- [{r[0]}](../people/{slugify(r[0])}.md)')
        cjeu_lines.append('')
    with open(os.path.join(WIKI_DIR, 'bodies/cjeu.md'), 'w') as f:
        f.write('\n'.join(cjeu_lines))

    # MEPs
    mep_lines = ['# SDT-Relevant MEPs', '', f'{mep_count} EP Presidents, Vice Presidents, committee chairs, and group leaders across 7 terms', '']
    for row in db.execute("SELECT name FROM entity WHERE category = 'mep_sdt' ORDER BY name").fetchall():
        mep_lines.append(f'- [{row[0]}](../people/{slugify(row[0])}.md)')
    with open(os.path.join(WIKI_DIR, 'bodies/meps.md'), 'w') as f:
        f.write('\n'.join(mep_lines))

    # Corporate
    if corp_count:
        corp_lines = ['# Transnational Corporate Elites', '', f'{corp_count} board members and CEOs of multi-European companies', '']
        for row in db.execute("SELECT name FROM entity WHERE category = 'corporate_elite' ORDER BY name").fetchall():
            corp_lines.append(f'- [{row[0]}](../people/{slugify(row[0])}.md)')
        with open(os.path.join(WIKI_DIR, 'bodies/corporate.md'), 'w') as f:
            f.write('\n'.join(corp_lines))

    # Commissions
    comm_lines = ['# European Commissions', '', f'{comm_count} commissions (1995–2029)', '']
    for row in db.execute("SELECT id, name FROM entity WHERE type = 'commission' ORDER BY id").fetchall():
        count = db.execute("SELECT COUNT(*) FROM fact WHERE predicate='served_on_commission' AND object=?", (row[0],)).fetchone()[0]
        comm_lines.append(f'- [{row[1]}](../commissions/{slugify(row[1])}.md) — {count} members')
    with open(os.path.join(WIKI_DIR, 'bodies/commissions.md'), 'w') as f:
        f.write('\n'.join(comm_lines))

    # Education Clusters
    edu_lines = ['# Education Clusters', '', 'Elite institution groupings used for SDT analysis.', '']
    for cid, _ in EDUCATION_CLUSTERS:
        label = cid.replace('-', ' ').title()
        edu_lines.append(f'- [{label}](../education/{cid}.md)')
    edu_lines.append('')
    with open(os.path.join(WIKI_DIR, 'bodies/education-clusters.md'), 'w') as f:
        f.write('\n'.join(edu_lines))

    # Countries
    ctry_lines = ['# Countries', '', f'{country_count} EU member states', '']
    for cc_code in sorted(CC.keys()):
        if os.path.exists(os.path.join(WIKI_DIR, 'countries', f'{cc_code.lower()}.md')):
            ctry_lines.append(f'- [{CC[cc_code]}](../countries/{cc_code.lower()}.md)')
    with open(os.path.join(WIKI_DIR, 'bodies/countries.md'), 'w') as f:
        f.write('\n'.join(ctry_lines))


def commission_page(db, entity_id):
    """Generate a wiki page for a commission."""
    ent = db.execute("SELECT * FROM entity WHERE id = ?", (entity_id,)).fetchone()
    if not ent: return None

    name = ent[1]
    fm = frontmatter({'id': entity_id, 'title': name, 'type': 'commission', 'tags': ['commission']})

    lines = [fm, f'# {name}', '']

    # Get all commissioners for this commission with portfolios
    commissioners = db.execute(
        "SELECT e.id, e.name FROM fact f JOIN entity e ON e.id = f.entity_id "
        "WHERE f.predicate = 'served_on_commission' AND f.object = ? ORDER BY e.name",
        (entity_id,)).fetchall()

    if commissioners:
        lines.append(f'## Members ({len(commissioners)})')
        lines.append('')
        for pid, pname in commissioners:
            safe = slugify(pname)
            # Get portfolio
            port = db.execute(
                "SELECT object FROM fact WHERE entity_id = ? AND predicate = 'held_portfolio' LIMIT 1",
                (pid,)).fetchone()
            portfolio = port[0] if port else ''
            country = db.execute(
                "SELECT object FROM fact WHERE entity_id = ? AND predicate = 'from_country' LIMIT 1",
                (pid,)).fetchone()
            country_name = CC.get(country[0] if country else '', '')
            line = f'- [{pname}](../people/{safe}.md)'
            if portfolio:
                line += f' — *{portfolio}*'
            if country_name:
                line += f'  ({country_name})'
            lines.append(line)
        lines.append('')

    return '\n'.join(lines)


def main():
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    generate_all(db)
    db.close()


if __name__ == '__main__':
    main()
