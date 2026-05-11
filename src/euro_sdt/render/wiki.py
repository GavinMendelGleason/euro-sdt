"""Generate a structured, browsable Obsidian wiki from the database.

Produces markdown with YAML frontmatter. Category pages aggregate entities
by type with clickable citation footnotes.

Usage:
    euro-sdt render wiki
    python -m euro_sdt.render.wiki
"""

import os, re, json, unicodedata
from datetime import date

from euro_sdt.config import WIKI_OUTPUT_DIR, DB_PATH
from euro_sdt.db import connect, slugify

TODAY = date.today().isoformat()
WIKI_DIR = WIKI_OUTPUT_DIR

PREDICATE_LABEL = {
    'served_on_commission': 'Served on',
    'served_on_ep': 'EP Term',
    'held_portfolio': 'Portfolio',
    'nominated_by': 'Nominated by',
    'from_country': 'Country',
    'educated_at': 'Educated at',
    'studied_field': 'Field of study',
    'held_degree': 'Degree',
    'affiliated_with': 'Organisation affiliations',
    'member_of': 'Member of',
    'held_position': 'Position',
    'post_mandate_occupation': 'Post-mandate',
    'classified_as': 'Classification',
    'funding_notes': 'Funding',
    'has_description': 'Description',
}

SECTION_ORDER = [
    'served_on_commission', 'served_on_ep', 'held_portfolio', 'nominated_by', 'from_country',
    'educated_at', 'studied_field', 'held_degree',
    'held_position', 'works_at',
    'affiliated_with', 'member_of', 'post_mandate_occupation',
    'classified_as', 'funding_notes', 'has_description',
]

CC = {
    'AUT': 'Austria', 'BEL': 'Belgium', 'BGR': 'Bulgaria', 'CYP': 'Cyprus', 'CZE': 'Czechia',
    'DEU': 'Germany', 'DNK': 'Denmark', 'ESP': 'Spain', 'EST': 'Estonia', 'FIN': 'Finland',
    'FRA': 'France', 'GBR': 'UK', 'GRC': 'Greece', 'HRV': 'Croatia', 'HUN': 'Hungary',
    'IRL': 'Ireland', 'ITA': 'Italy', 'LTU': 'Lithuania', 'LUX': 'Luxembourg', 'LVA': 'Latvia',
    'MLT': 'Malta', 'NLD': 'Netherlands', 'POL': 'Poland', 'PRT': 'Portugal', 'ROU': 'Romania',
    'SVK': 'Slovakia', 'SVN': 'Slovenia', 'SWE': 'Sweden',
}

EDUCATION_CLUSTERS = [
    ('oxbridge', r'oxford|cambridge'),
    ('sciences-po-ena', r'sciences po|sciences-po|iep\b.*paris|\bena\b|ecole nationale.*admin|enarque'),
]


def _slugify(text):
    return slugify(text)


def is_valid_institution_name(name):
    name_lower = name.lower().strip()
    garbage_markers = [
        'not specified', 'implied by context', 'not explicitly', 'without naming',
        'the text', 'unnamed', 'unknown', 'not mentioned', 'unclear',
        'none listed', 'not found', 'n/a', 'various', 'several', 'multiple',
        'the source', 'unable to', 'cannot be determined',
    ]
    if len(name) > 150:
        return False
    if any(m in name_lower for m in garbage_markers):
        return False
    return True


def is_valid_org_name(name):
    name_lower = name.lower().strip()
    award_markers = [
        'order of ', 'grand cross', 'commander ', 'knight ', 'officer of',
        'medal of', 'decoration', 'grand officer', 'adler-orden',
        'grã-cruz', 'chevalier', 'commendatore', 'grande ufficiale',
    ]
    if any(m in name_lower for m in award_markers):
        return False
    journal_markers = ['revue ', 'review ', 'journal ', 'quarterly', 'tijdschrift',
                       'cahiers de', 'european law review']
    if any(m in name_lower for m in journal_markers):
        return False
    heading_markers = [
        'biography and career', 'memberships of', 'honorary titles', 'titles and awards',
        'curriculum vitae', 'professional experience', 'show more', 'show less',
    ]
    if any(m in name_lower for m in heading_markers):
        return False
    if len(name) > 150:
        return False
    if name_lower.startswith(('born ', 'in he began', 'from ', 'on his return')):
        return False
    return True


def get_org_tags(db, entity_id, org_name):
    classified = db.execute("""
        SELECT f.object FROM fact f
        WHERE f.entity_id = ? AND f.predicate = 'classified_as'
        ORDER BY CASE WHEN f.object IN ('think-tank','political-party','corporate',
        'government-body','industry-association','ngo','org-generic') THEN 0 ELSE 1 END
        LIMIT 1
    """, [entity_id]).fetchone()
    if classified:
        cat = classified[0].lower()
        if cat in ['think-tank', 'political-party', 'corporate', 'government-body', 'industry-association', 'ngo']:
            return ['org', cat]

    name_lower = org_name.lower()
    party_kw = ['party', 'parti', 'partido', 'partei', 'partit', 'socialist', 'communist',
                'christian democrat', 'conservative', 'liberal', 'green party', "people's party",
                'labour party', 'social democratic', 'popular party', 'republican']
    if any(k in name_lower for k in party_kw):
        return ['org', 'political-party']

    gov_kw = ['parliament', 'congress', 'senate', 'chamber of deputies', 'bundestag',
              'national assembly', 'diet', 'sejm', 'seimas', 'council of ministers',
              'committee on', 'delegation to', 'parliamentary assembly']
    if any(k in name_lower for k in gov_kw):
        return ['org', 'government-body']

    corp_kw = ['bank', 'insurance', 'energy', 'oil', 'gas', 'steel', 'chemical', 'pharma',
               'automotive', 'aerospace', 'telecom', 'technology',
               'airbus', 'safran', 'rheinmetall', 'leonardo', 'thales',
               'siemens', 'sap', 'asml', 'infineon',
               'shell', 'bp', 'total', 'eni', 'enel', 'iberdrola',
               'santander', 'bnp', 'deutsche bank', 'ing', 'bbva', 'unicredit',
               'allianz', 'axa', 'renault', 'volkswagen', 'stellantis', 'bmw',
               'mercedes', 'lvmh', "l'oréal", 'sanofi', 'bayer',
               'goldman', 'morgan stanley', 'ubs', 'credit suisse', 'barclays', 'hsbc',
               'merrill', 'mckinsey', 'boston consulting', 'kpmg', 'deloitte', 'pwc',
               'ernst', 'accenture', 'blackrock', 'blackstone']
    if any(k in name_lower for k in corp_kw):
        return ['org', 'corporate']

    ind_kw = ['round table', 'chamber of commerce', 'business association',
              'industry association', 'financial services', 'insurance forum',
              'banking federation', 'employers', 'entrepreneurs']
    if any(k in name_lower for k in ind_kw):
        return ['org', 'industry-association']

    tt_kw = ['think tank', 'policy institute', 'research institute', 'policy centre',
             'policy center', 'foundation', 'institute for', 'centre for',
             'center for', 'council on foreign', 'friends of europe',
             'atlantic council', 'ecfr', 'bruegel', 'ceps', 'trilateral',
             'bilderberg', 'munich security']
    if any(k in name_lower for k in tt_kw):
        return ['org', 'think-tank']

    connected = {r[0] for r in db.execute("""
        SELECT DISTINCT e.category FROM fact f
        JOIN entity e ON e.id = f.entity_id
        WHERE f.predicate IN ('affiliated_with','member_of') AND f.object = ?
    """, [entity_id]).fetchall()}
    if 'commissioner' in connected:
        return ['org', 'think-tank']
    if 'mep_sdt' in connected:
        return ['org', 'political-party']
    if 'corporate_elite' in connected:
        return ['org', 'corporate']
    return ['org', 'org-generic']


def get_person_tags(category):
    mapping = {
        'commissioner': ['person', 'commissioner', 'political-elite'],
        'mep_sdt': ['person', 'mep', 'political-elite'],
        'corporate_elite': ['person', 'corporate', 'economic-elite'],
        'dg': ['person', 'dg', 'administrative-elite'],
        'ddg': ['person', 'ddg', 'administrative-elite'],
        'cjeu_judge': ['person', 'cjeu', 'judicial-elite'],
        'cjeu_ag': ['person', 'cjeu', 'judicial-elite'],
    }
    return mapping.get(category, ['person', category or 'unknown'])


def frontmatter(fields):
    lines = ['---']
    for k, v in fields.items():
        if isinstance(v, list):
            lines.append(f'{k}:')
            for item in v:
                lines.append(f'  - {item}')
        elif v is not None and v != '':
            lines.append(f'{k}: {v}')
    lines.append(f'generated: {TODAY}')
    lines.append('---\n')
    return '\n'.join(lines)


def fetch_facts_grouped(db, entity_id):
    facts = db.execute(
        "SELECT * FROM fact WHERE entity_id = ? ORDER BY predicate, start_date",
        (entity_id,)).fetchall()
    grouped = {}
    for f in facts:
        pred = f[2]
        if pred not in grouped:
            grouped[pred] = []
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
    lines = []
    for predicate in SECTION_ORDER:
        if predicate not in grouped:
            continue
        label = PREDICATE_LABEL.get(predicate, predicate)
        lines.append(f'{"#" * heading_level} {label}\n')

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

            for cit in fact['citations']:
                src_name, url, quote, phrase_idx, context = cit
                if quote:
                    lines.append(f'  > "{quote[:200]}"')
                if url:
                    lines.append(f'  > {src_name}')
                else:
                    lines.append(f'  > *{src_name}*')
                if context:
                    lines.append(f'  > {context[:150]}')
            lines.append('')

        lines.append('')
    return lines


def person_page(db, entity_id):
    ent = db.execute("SELECT * FROM entity WHERE id = ?", (entity_id,)).fetchone()
    if not ent:
        return None
    name, etype, category, country_code = ent[1], ent[2], ent[3] or '', ent[4] or ''

    fm = frontmatter({
        'id': entity_id, 'title': name, 'type': etype,
        'category': category, 'country': country_code,
        'tags': get_person_tags(category),
    })
    lines = [fm, f'# {name}', '']
    if country_code:
        country_name = CC.get(country_code, country_code)
        lines.append(f'**{category.replace("_", " ").title()}** · [{country_name}](../countries/{country_code.lower()}.md)')
    lines.append('')
    lines.append(f'*← [Bodies](../bodies.md)*\n')

    grouped = fetch_facts_grouped(db, entity_id)
    lines.extend(render_facts(grouped))

    edu_facts = grouped.get('educated_at', [])
    if edu_facts:
        lines.append('### Education clusters')
        clusters_found = set()
        for fact in edu_facts:
            obj_lower = fact['object'].lower()
            for cluster_id, pattern in EDUCATION_CLUSTERS:
                if re.search(pattern, obj_lower) and cluster_id not in clusters_found:
                    clusters_found.add(cluster_id)
                    lines.append(f'- [{cluster_id.replace("-", " ").title()}](../education/{cluster_id}.md)')
    return '\n'.join(lines)


def organisation_page(db, entity_id):
    ent = db.execute("SELECT * FROM entity WHERE id = ?", (entity_id,)).fetchone()
    if not ent:
        return None
    name = ent[1]
    fm = frontmatter({
        'id': entity_id, 'title': name, 'type': 'organisation',
        'tags': get_org_tags(db, entity_id, name),
    })
    lines = [fm, f'# {name}', '', '## Profile', '']
    grouped = fetch_facts_grouped(db, entity_id)
    for pred in ['classified_as', 'funding_notes', 'has_description']:
        if pred in grouped:
            for fact in grouped[pred]:
                lines.append(f'- {fact["object"]}')
    lines.append('')

    members = db.execute(
        "SELECT e.id, e.name FROM fact f JOIN entity e ON e.id = f.entity_id "
        "WHERE f.predicate IN ('member_of', 'affiliated_with') AND f.object = ? ORDER BY e.name",
        (entity_id,)).fetchall()
    if members:
        lines.append('## Members')
        lines.append(f'({len(members)} people)\n')
        for mid, mname in members:
            safe = _slugify(mname)
            lines.append(f'- [{mname}](../people/{safe}.md)')
        lines.append('')
    return '\n'.join(lines)


def education_cluster_page(db, cluster_id, cluster_pattern):
    label = cluster_id.replace('-', ' ').title()
    fm = frontmatter({
        'id': cluster_id, 'title': f'{label} — Education Cluster',
        'type': 'education_cluster', 'tags': ['education', cluster_id],
    })
    lines = [fm, f'# {label}\n',
             f'Commissioners, MEP leaders, and officials who studied at or attended {label}.\n']
    members = {}
    for inst_name, pid, pname, cat in db.execute("""
        SELECT obj.name, e.id, e.name, e.category
        FROM fact f JOIN entity e ON e.id = f.entity_id
        JOIN entity obj ON obj.id = f.object
        WHERE f.predicate = 'educated_at' AND e.type = 'person'
    """).fetchall():
        if re.search(cluster_pattern, inst_name.lower()):
            if pname not in members:
                members[pname] = {'id': pid, 'category': cat or '', 'institutions': []}
            members[pname]['institutions'].append(inst_name)

    lines.append(f'## Attendees ({len(members)})\n')
    comms = {n: m for n, m in members.items() if 'commissioner' in (m['category'] or '').lower()}
    dgs = {n: m for n, m in members.items() if m['category'] in ('dg', 'ddg')}
    meps = {n: m for n, m in members.items() if m['category'] == 'mep_sdt'}
    other = {n: m for n, m in members.items() if n not in {**comms, **dgs, **meps}}

    for heading, group in [('Commissioners', comms), ('MEP Leaders', meps),
                            ('Directors-General & DDGs', dgs), ('Other', other)]:
        if group:
            lines.append(f'### {heading}')
            for pname in sorted(group):
                insts = ' | '.join(group[pname]['institutions'])
                safe = _slugify(pname)
                lines.append(f'- [{pname}](../people/{safe}.md) — {insts}')
            lines.append('')
    return '\n'.join(lines)


def commission_page(db, entity_id):
    ent = db.execute("SELECT * FROM entity WHERE id = ?", (entity_id,)).fetchone()
    if not ent:
        return None
    name = ent[1]
    fm = frontmatter({'id': entity_id, 'title': name, 'type': 'commission', 'tags': ['commission']})
    lines = [fm, f'# {name}\n']
    commissioners = db.execute(
        "SELECT e.id, e.name FROM fact f JOIN entity e ON e.id = f.entity_id "
        "WHERE f.predicate = 'served_on_commission' AND f.object = ? ORDER BY e.name",
        (entity_id,)).fetchall()
    if commissioners:
        lines.append(f'## Members ({len(commissioners)})\n')
        for pid, pname in commissioners:
            safe = _slugify(pname)
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


def generate_graph_config():
    os.makedirs(os.path.join(WIKI_DIR, '.obsidian'), exist_ok=True)
    config = {
        "collapse-filter": False, "search": "", "showTags": True,
        "showAttachments": False, "hideUnresolved": False, "showOrphans": True,
        "collapse-color-groups": False,
        "colorGroups": [
            {"query": "tag:#political-elite", "color": {"a": 1, "rgb": 5077951}},
            {"query": "tag:#economic-elite", "color": {"a": 1, "rgb": 16733525}},
            {"query": "tag:#administrative-elite", "color": {"a": 1, "rgb": 4638335}},
            {"query": "tag:#judicial-elite", "color": {"a": 1, "rgb": 10350619}},
            {"query": "tag:#political-party", "color": {"a": 1, "rgb": 6553700}},
            {"query": "tag:#think-tank", "color": {"a": 1, "rgb": 8421504}},
            {"query": "tag:#corporate", "color": {"a": 1, "rgb": 16744576}},
            {"query": "tag:#government-body", "color": {"a": 1, "rgb": 10092543}},
            {"query": "tag:#education", "color": {"a": 1, "rgb": 16766720}},
            {"query": "tag:#hub", "color": {"a": 1, "rgb": 16777215}},
        ],
        "collapse-display": False, "showArrow": False, "textFadeMultiplier": 0,
        "nodeSizeMultiplier": 1, "lineSizeMultiplier": 1, "collapse-forces": False,
        "centerStrength": 0.5, "repelStrength": 10, "linkStrength": 1,
        "linkDistance": 250, "scale": 1,
    }
    with open(os.path.join(WIKI_DIR, '.obsidian', 'graph.json'), 'w') as f:
        json.dump(config, f, indent=2)


def generate_index_page(db):
    total_facts = db.execute("SELECT COUNT(*) FROM fact").fetchone()[0]
    total_entities = db.execute("SELECT COUNT(*) FROM entity").fetchone()[0]
    lines = [
        '---', 'id: index', 'title: Euro-SDT Wiki', 'type: index',
        'tags: [index]', f'generated: {TODAY}', '---', '',
        '# Euro-SDT Wiki', '',
        f'*{total_facts} verified facts across {total_entities} entities. Citation-anchored knowledge graph.*',
        '', '## Navigation', '',
        '- **[Bodies](bodies.md)** — Commissioners, DGs, CJEU, MEP leaders, education clusters, countries',
        '- **[Statistics](stats.md)** — Data quality and coverage charts',
        '- **[Citations](citations.md)** — Primary source index', '',
    ]
    path = os.path.join(WIKI_DIR, 'index.md')
    with open(path, 'w') as f:
        f.write('\n'.join(lines))


def generate_body_subpages(db):
    """Generate bodies.md and all sub-pages."""
    os.makedirs(os.path.join(WIKI_DIR, 'bodies'), exist_ok=True)
    dg_count = db.execute("SELECT COUNT(*) FROM entity WHERE type='person' AND category IN ('dg','ddg')").fetchone()[0]
    cjeu_count = db.execute("SELECT COUNT(*) FROM entity WHERE type='person' AND category IN ('cjeu_judge','cjeu_ag')").fetchone()[0]
    mep_count = db.execute("SELECT COUNT(*) FROM entity WHERE category = 'mep_sdt'").fetchone()[0]
    corp_count = db.execute("SELECT COUNT(*) FROM entity WHERE category = 'corporate_elite'").fetchone()[0]
    comm_count = db.execute("SELECT COUNT(*) FROM entity WHERE type='commission'").fetchone()[0]
    country_count = len([c for c in CC if os.path.exists(os.path.join(WIKI_DIR, 'countries', f'{c.lower()}.md'))])

    lines = [
        '---', 'id: bodies', 'title: EU Institutional Bodies', 'type: index',
        'tags: [index, bodies]', f'generated: {TODAY}', '---', '',
        '# EU Institutional Bodies', '',
        'All commissioners, Directors-General, MEP leaders, and Court of Justice members.',
        '',
        f'## [European Commissions](bodies/commissions.md)\n{comm_count} commissions (1995–2029)\n',
        f'## [Directors-General](bodies/dgs.md)\n{dg_count} senior officials\n',
        f'## [Court of Justice](bodies/cjeu.md)\n{cjeu_count} members\n',
    ]
    if mep_count:
        lines.append(f'## [SDT-Relevant MEPs](bodies/meps.md)\n{mep_count} EP leaders\n')
    if corp_count:
        lines.append(f'## [Transnational Corporate Elites](bodies/corporate.md)\n{corp_count} board members\n')
    lines.append('## [Education Clusters](bodies/education-clusters.md)\nElite institution groupings\n')
    lines.append(f'## [Countries](bodies/countries.md)\n{country_count} member states\n')
    with open(os.path.join(WIKI_DIR, 'bodies.md'), 'w') as f:
        f.write('\n'.join(lines))

    # DGs sub-page
    dg_lines = ['# Directors-General & Deputy Directors-General\n', f'{dg_count} senior officials\n']
    for name, cat, dept in db.execute("""
        SELECT e.name, e.category, f.object FROM entity e
        LEFT JOIN fact f ON f.entity_id = e.id AND f.predicate = 'held_position'
        WHERE e.type = 'person' AND e.category IN ('dg','ddg')
        ORDER BY e.category DESC, e.name
    """).fetchall():
        safe = _slugify(name)
        role = 'Director-General' if cat == 'dg' else 'Deputy Director-General'
        dg_lines.append(f'- [{name}](../people/{safe}.md) — *{role}* — {str(dept or "")[:60]}')
    with open(os.path.join(WIKI_DIR, 'bodies/dgs.md'), 'w') as f:
        f.write('\n'.join(dg_lines))

    # CJEU sub-page
    cjeu_lines = ['# Court of Justice (CJEU)\n', f'{cjeu_count} members\n']
    for label, cat in [('Judges', 'cjeu_judge'), ('Advocates General', 'cjeu_ag')]:
        rows = db.execute("SELECT name FROM entity WHERE type='person' AND category=? ORDER BY name", [cat]).fetchall()
        if rows:
            cjeu_lines.append(f'## {label} ({len(rows)})\n')
            for r in rows:
                cjeu_lines.append(f'- [{r[0]}](../people/{_slugify(r[0])}.md)')
            cjeu_lines.append('')
    with open(os.path.join(WIKI_DIR, 'bodies/cjeu.md'), 'w') as f:
        f.write('\n'.join(cjeu_lines))

    # MEPs sub-page
    if mep_count:
        mep_lines = ['# SDT-Relevant MEPs\n', f'{mep_count} EP leaders\n']
        for r in db.execute("SELECT name FROM entity WHERE category='mep_sdt' ORDER BY name").fetchall():
            mep_lines.append(f'- [{r[0]}](../people/{_slugify(r[0])}.md)')
        with open(os.path.join(WIKI_DIR, 'bodies/meps.md'), 'w') as f:
            f.write('\n'.join(mep_lines))

    # Corporate sub-page
    if corp_count:
        corp_lines = ['# Transnational Corporate Elites\n', f'{corp_count} board members and CEOs\n']
        for r in db.execute("SELECT name FROM entity WHERE category='corporate_elite' ORDER BY name").fetchall():
            corp_lines.append(f'- [{r[0]}](../people/{_slugify(r[0])}.md)')
        with open(os.path.join(WIKI_DIR, 'bodies/corporate.md'), 'w') as f:
            f.write('\n'.join(corp_lines))

    # Commissions sub-page
    comm_lines = ['# European Commissions\n', f'{comm_count} commissions (1995–2029)\n']
    for cid, cname in db.execute("SELECT id, name FROM entity WHERE type='commission' ORDER BY id").fetchall():
        count = db.execute("SELECT COUNT(*) FROM fact WHERE predicate='served_on_commission' AND object=?", (cid,)).fetchone()[0]
        comm_lines.append(f'- [{cname}](../commissions/{_slugify(cname)}.md) — {count} members')
    with open(os.path.join(WIKI_DIR, 'bodies/commissions.md'), 'w') as f:
        f.write('\n'.join(comm_lines))

    # Education clusters sub-page
    edu_lines = ['# Education Clusters\n', 'Elite institution groupings.\n']
    for cid, _ in EDUCATION_CLUSTERS:
        label = cid.replace('-', ' ').title()
        edu_lines.append(f'- [{label}](../education/{cid}.md)')
    edu_lines.append('\n## Individual Institutions\n')
    seen = set()
    for inst_name, count, inst_id in db.execute("""
        SELECT obj.name, COUNT(DISTINCT f.entity_id), obj.id
        FROM fact f JOIN entity obj ON obj.id = f.object
        WHERE f.predicate = 'educated_at'
        GROUP BY obj.name HAVING COUNT(DISTINCT f.entity_id) >= 3 ORDER BY COUNT(DISTINCT f.entity_id) DESC
    """).fetchall():
        cluster_id = _slugify(inst_name)
        if cluster_id in seen:
            continue
        seen.add(cluster_id)
        skip = any(re.search(pattern, inst_name.lower()) for _, pattern in EDUCATION_CLUSTERS)
        if skip:
            continue
        edu_lines.append(f'- [{inst_name}](../education/{cluster_id}.md) — {count}')
    edu_lines.append('')
    with open(os.path.join(WIKI_DIR, 'bodies/education-clusters.md'), 'w') as f:
        f.write('\n'.join(edu_lines))

    # Countries sub-page
    ctry_lines = ['# Countries\n', f'{country_count} EU member states\n']
    for cc_code in sorted(CC):
        if os.path.exists(os.path.join(WIKI_DIR, 'countries', f'{cc_code.lower()}.md')):
            ctry_lines.append(f'- [{CC[cc_code]}](../countries/{cc_code.lower()}.md)')
    with open(os.path.join(WIKI_DIR, 'bodies/countries.md'), 'w') as f:
        f.write('\n'.join(ctry_lines))


def generate_all(db):
    os.makedirs(WIKI_DIR, exist_ok=True)
    for d in ['commissions', 'organisations', 'people', 'education', 'countries']:
        os.makedirs(os.path.join(WIKI_DIR, d), exist_ok=True)

    entities = db.execute("SELECT id, type, category, country FROM entity ORDER BY id").fetchall()
    count = 0
    print(f'  Processing {len(entities)} entities...')

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
            ent = db.execute("SELECT name FROM entity WHERE id=?", (eid,)).fetchone()
            safe = _slugify(ent[0])
            path = os.path.join(WIKI_DIR, subdir, f'{safe}.md')
            with open(path, 'w') as f:
                f.write(page)
            count += 1

    for cluster_id, pattern in EDUCATION_CLUSTERS:
        page = education_cluster_page(db, cluster_id, pattern)
        if page:
            with open(os.path.join(WIKI_DIR, 'education', f'{cluster_id}.md'), 'w') as f:
                f.write(page)

    auto_count = 0
    for inst_name, inst_id, attendee_count in db.execute("""
        SELECT obj.name, obj.id, COUNT(DISTINCT f.entity_id)
        FROM fact f JOIN entity obj ON obj.id = f.object
        WHERE f.predicate = 'educated_at'
        GROUP BY obj.name HAVING COUNT(DISTINCT f.entity_id) >= 3 ORDER BY COUNT(DISTINCT f.entity_id) DESC
    """).fetchall():
        if not is_valid_institution_name(inst_name):
            continue
        cluster_id = _slugify(inst_name)
        if any(re.search(pattern, inst_name.lower()) for _, pattern in EDUCATION_CLUSTERS):
            continue
        pattern = re.escape(inst_name.lower())
        page = education_cluster_page(db, cluster_id, pattern)
        if page:
            with open(os.path.join(WIKI_DIR, 'education', f'{cluster_id}.md'), 'w') as f:
                f.write(page)
            auto_count += 1
            if auto_count <= 5:
                print(f'  Auto: {inst_name[:40]} ({attendee_count} attendees) → {cluster_id[:40]}.md')

    cc_count = 0
    for cc_code, cc_name in CC.items():
        commissioners = db.execute(
            "SELECT id, name FROM entity WHERE country = ? AND type = 'person' ORDER BY name",
            (cc_code,)).fetchall()
        if not commissioners:
            continue
        cc_count += 1
        fm = frontmatter({'id': cc_code.lower(), 'title': cc_name, 'type': 'country', 'tags': ['country']})
        lines = [fm, f'# {cc_name}\n', f'## Commissioners ({len(commissioners)})\n']
        for pid, pname in commissioners:
            safe = _slugify(pname)
            lines.append(f'- [{pname}](../people/{safe}.md)')
        lines.append('')
        with open(os.path.join(WIKI_DIR, 'countries', f'{cc_code.lower()}.md'), 'w') as f:
            f.write('\n'.join(lines))

    print(f'Generated {count} entity pages + {len(EDUCATION_CLUSTERS) + auto_count} education + {cc_count} country pages')
    generate_index_page(db)
    generate_body_subpages(db)
    generate_graph_config()


def main():
    db = connect()
    generate_all(db)
    db.close()


if __name__ == '__main__':
    main()
