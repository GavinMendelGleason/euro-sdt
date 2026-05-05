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
    'held_portfolio':        'Portfolio',
    'nominated_by':          'Nominated by',
    'from_country':          'Country',
    'educated_at':           'Educated at',
    'studied_field':         'Field of study',
    'held_degree':           'Degree',
    'member_of':             'Member of',
    'held_position':         'Position',
    'post_mandate_occupation':'Post-mandate',
    'classified_as':         'Classification',
    'funding_notes':         'Funding',
    'has_description':       'Description',
}

SECTION_ORDER = [
    'served_on_commission','held_portfolio','nominated_by','from_country',
    'educated_at','studied_field','held_degree',
    'held_position','works_at',
    'member_of','post_mandate_occupation',
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

# Education cluster definitions
EDUCATION_CLUSTERS = [
    ('sciences-po',           r'sciences po|sciences-po|iep\b.*paris|sciencespo'),
    ('ena',                   r'\bena\b|ecole nationale.*admin|enarque'),
    ('college-of-europe',     r'college of europe|college-of-europe|collège d.europe'),
    ('oxbridge',              r'oxford|cambridge'),
    ('lse',                   r'london school of economics|\blse\b'),
    ('harvard',               r'harvard'),
    ('ulb-brussels',          r'ulb|universite libre.*bruxelles|free university.*brussels'),
    ('eui-florence',          r'european university institute|\beui\b'),
    ('georgetown',            r'georgetown'),
    ('eastern-european',      r'mgimo|central european university|\bceu\b|sgh warsaw|charles university|comenius'),
]


def slugify(text):
    import unicodedata
    text = unicodedata.normalize('NFD', text)
    text = ''.join(c for c in text if unicodedata.category(c) != 'Mn')
    text = re.sub(r'[^a-zA-Z0-9\s\-]', '', text)
    return text.strip().lower().replace(' ', '-').replace('--', '-')


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
        if f[4] == 'entity_id':
            ref = db.execute("SELECT name FROM entity WHERE id = ?", (obj,)).fetchone()
            obj = ref[0] if ref else obj
        citations = db.execute(
            """SELECT c.source_name, c.url, p.quote_text, p.phrase_index, p.context_text
               FROM provenance p JOIN citation c ON p.citation_id = c.id
               WHERE p.fact_id = ?""", (f[0],)).fetchall()
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
        'tags': [etype, category] if category else [etype],
    })

    lines = [fm, f'# {name}', '']
    if country_code:
        country_name = CC.get(country_code, country_code)
        lines.append(f'**{category.replace("_"," ").title()}** · [{country_name}](../countries/{country_code.lower()}.md)')
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
        'tags': ['organisation'],
    })

    lines = [fm, f'# {name}', '', '## Profile', '']

    # Classification facts
    grouped = fetch_facts_grouped(db, entity_id)
    for pred in ['classified_as', 'funding_notes', 'has_description']:
        if pred in grouped:
            for fact in grouped[pred]:
                lines.append(f'- {fact["object"]}')
    lines.append('')

    # Members
    members = db.execute(
        "SELECT e.id, e.name FROM fact f JOIN entity e ON e.id = f.entity_id "
        "WHERE f.predicate = 'member_of' AND f.object = ? ORDER BY e.name",
        (entity_id,)).fetchall()
    if members:
        lines.append('## Members')
        lines.append(f'({len(members)} commissioners/officials)')
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
             f'Commissioners and officials who studied at or attended {label}.', '']

    # Find all educated_at facts matching this cluster
    members = {}
    for row in db.execute("""
        SELECT f.object, e.id as person_id, e.name as person_name
        FROM fact f JOIN entity e ON e.id = f.entity_id
        WHERE f.predicate = 'educated_at' AND e.type = 'person'
    """).fetchall():
        obj = row[0]
        if re.search(cluster_pattern, obj.lower()):
            pid, pname = row[1], row[2]
            if pname not in members:
                members[pname] = {'id': pid, 'institutions': []}
            members[pname]['institutions'].append(obj)

    lines.append(f'## Attendees ({len(members)})')
    lines.append('')
    for pname in sorted(members.keys()):
        insts = ' | '.join(members[pname]['institutions'])
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
