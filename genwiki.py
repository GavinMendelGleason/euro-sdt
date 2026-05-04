"""
genwiki.py — Generate a wiki view from the citation-anchored knowledge graph.

Reads euro_sdt.db and produces markdown pages in wiki/ directory.
The wiki is a build artefact — never edit it by hand.
"""
import sqlite3
import os
import re
from datetime import date

DB_PATH = 'euro_sdt.db'
WIKI_DIR = 'wiki'
TODAY = date.today().isoformat()


# ── Predicate display names ─────────────────────────────────────────────────

PREDICATE_LABEL = {
    'served_on_commission':     'Served on commission',
    'held_portfolio':           'Portfolio',
    'nominated_by':             'Nominated by',
    'from_country':             'Country',
    'educated_at':              'Educated at',
    'studied_field':            'Field of study',
    'held_degree':              'Degree',
    'held_position':            'Position held',
    'member_of':                'Member of',
    'member_of_board':          'Board member of',
    'member_of_advisory':       'Advisory board of',
    'works_at':                 'Works at',
    'classified_as':            'Classification',
    'post_mandate_occupation':  'Post-mandate occupation',
    'funding_notes':            'Funding',
    'started_on':               'Started',
    'born_in':                  'Born in',
    'born_on':                  'Born on',
    'headed_by':                'Headed by',
    'founded_in':               'Founded',
    'headquartered_in':         'Headquarters',
    'has_sector':               'Sector',
}

SECTION_ORDER = [
    'served_on_commission', 'held_portfolio', 'nominated_by', 'from_country',
    'born_on', 'born_in',
    'educated_at', 'studied_field', 'held_degree',
    'held_position', 'works_at',
    'member_of', 'member_of_board', 'member_of_advisory',
    'post_mandate_occupation',
    'classified_as', 'funding_notes', 'headquartered_in', 'founded_in', 'started_on',
]


def slugify(text):
    return text.lower().replace(' ', '-').replace(',','').replace("'",'')

def fetch_entity(db, eid):
    return db.execute("SELECT * FROM entity WHERE id = ?", (eid,)).fetchone()

def fetch_facts(db, eid):
    return db.execute(
        "SELECT * FROM fact WHERE entity_id = ? ORDER BY predicate, start_date",
        (eid,)).fetchall()

def fetch_citations_for_fact(db, fact_id):
    return db.execute(
        """SELECT c.source_name, c.source_type, c.url, c.access_date,
                  p.quote_text, p.phrase_start, p.phrase_end, p.context_text
           FROM provenance p JOIN citation c ON p.citation_id = c.id
           WHERE p.fact_id = ?""",
        (fact_id,)).fetchall()

def fmt_date(d):
    if not d: return ''
    return d[:10] if len(d) > 10 else d

def entity_type_label(typ, cat):
    if typ == 'person':
        return cat.replace('_',' ').title() if cat else 'Person'
    if typ == 'organisation':
        return cat.replace('_',' ').title() if cat else 'Organisation'
    if typ == 'commission':
        return 'Commission'
    if typ == 'institution':
        return 'Institution'
    return typ.title()

def group_facts_by_predicate(db, eid):
    """Fetch all facts and group by predicate."""
    facts = fetch_facts(db, eid)
    grouped = {}
    for f in facts:
        pred = f[2]
        if pred not in grouped:
            grouped[pred] = []
        # Append fact row + citations
        citations = fetch_citations_for_fact(db, f[0])
        grouped[pred].append((f, citations))
    return grouped


def generate_entity_page(db, eid):
    ent = fetch_entity(db, eid)
    if not ent: return None

    grouped = group_facts_by_predicate(db, eid)

    lines = []
    # Frontmatter
    lines.append('---')
    lines.append(f'id: {ent[0]}')
    lines.append(f'name: "{ent[1]}"')
    lines.append(f'type: {ent[2]}')
    if ent[3]: lines.append(f'category: {ent[3]}')
    if ent[4]: lines.append(f'country: {ent[4]}')
    lines.append(f'generated: {TODAY}')
    lines.append('---')
    lines.append('')

    # Header
    etype = entity_type_label(ent[2], ent[3])
    lines.append(f'# {ent[1]}')
    lines.append(f'**{etype}**')
    if ent[4]: lines.append(f'*{ent[4]}*')
    lines.append('')

    # Facts by section
    fact_count = 0
    for predicate in SECTION_ORDER:
        if predicate not in grouped:
            continue
        label = PREDICATE_LABEL.get(predicate, predicate)
        lines.append(f'## {label}')
        lines.append('')

        for fact_row, citations in grouped[predicate]:
            fact_count += 1
            obj = fact_row[3]
            obj_type = fact_row[4]        # col 4 = object_type
            qualifier = fact_row[5] if fact_row[5] else ''  # col 5 = qualifier
            # Resolve entity_id references to display names
            if obj_type == 'entity_id':
                ref = fetch_entity(db, obj)
                obj = ref[1] if ref else obj
            date_str = ''
            if fact_row[6]:
                date_str = fmt_date(fact_row[6])
                if fact_row[7]:
                    date_str += f' → {fmt_date(fact_row[7])}'

            # Main line
            line = f'- **{obj}**'
            if qualifier:
                line += f' — {qualifier}'
            if date_str:
                line += f' ({date_str})'
            confidence = fact_row[8]  # col 8 = confidence
            if confidence and confidence != 'confirmed':
                line += f' [{confidence}]'
            lines.append(line)

            # Citation footnotes
            for i, cit in enumerate(citations):
                ref_num = fact_count if len(citations) == 1 else f'{fact_count}.{i+1}'
                lines.append(f'  ^{{{ref_num}}} *{cit[0]}* ({cit[1]})')
                if cit[5]:
                    lines.append(f'  > "{cit[4][:300]}"')
                if cit[2]:
                    lines.append(f'  > [{cit[2]}]({cit[2]}) accessed {cit[3]}')
                lines.append('')
            if not citations:
                lines.append('')  # no citation — flag for review

        lines.append('')

    # Footer
    lines.append(f'---')
    lines.append(f'Generated {TODAY}. {fact_count} facts.')
    if fact_count == 0:
        lines.append('⚠️ No facts recorded for this entity.')

    return '\n'.join(lines)


def generate_index_page(db):
    """List of all entities grouped by type."""
    entities = db.execute(
        "SELECT id, name, type, category, country FROM entity ORDER BY type, category, name"
    ).fetchall()

    lines = ['---',
             'generated: ' + TODAY,
             '---',
             '',
             '# Entity Index',
             '']

    current_type = ''
    for eid, name, typ, cat, country in entities:
        if typ != current_type:
            current_type = typ
            lines.append(f'## {typ.title()}s')
            lines.append('')

        flag = f' {country}' if country else ''
        cat_label = f'[{cat.replace("_"," ").title()}]' if cat else ''
        lines.append(f'- [{name}]({eid}.md) {cat_label}{flag}')

    lines.append('')
    lines.append('---')
    lines.append(f'Generated {TODAY}. {len(entities)} entities.')
    return '\n'.join(lines)


def generate_citations_page(db):
    """List of all citations."""
    citations = db.execute(
        "SELECT id, source_name, source_type, url, access_date, description "
        "FROM citation ORDER BY id").fetchall()

    lines = ['---',
             'generated: ' + TODAY,
             '---',
             '',
             '# Citations',
             '',
             'All sources backing facts in this knowledge graph.',
             '']

    for cid, name, stype, url, access, desc in citations:
        lines.append(f'## {name}')
        lines.append(f'- **ID:** `{cid}`')
        lines.append(f'- **Type:** {stype}')
        if url: lines.append(f'- **URL:** [{url}]({url})')
        if access: lines.append(f'- **Accessed:** {access}')
        if desc: lines.append(f'- **Note:** {desc}')
        lines.append('')

    lines.append('---')
    lines.append(f'Generated {TODAY}. {len(citations)} citations.')
    return '\n'.join(lines)


def main():
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    os.makedirs(WIKI_DIR, exist_ok=True)

    entities = db.execute("SELECT id FROM entity ORDER BY id").fetchall()
    count = 0

    for (eid,) in entities:
        page = generate_entity_page(db, eid)
        if page:
            path = os.path.join(WIKI_DIR, f'{eid}.md')
            with open(path, 'w') as f:
                f.write(page)
            count += 1

    # Index
    with open(os.path.join(WIKI_DIR, 'index.md'), 'w') as f:
        f.write(generate_index_page(db))

    # Citations
    with open(os.path.join(WIKI_DIR, 'citations.md'), 'w') as f:
        f.write(generate_citations_page(db))

    db.close()
    print(f"Generated {count} entity pages + index + citations in {WIKI_DIR}/")


if __name__ == '__main__':
    main()
