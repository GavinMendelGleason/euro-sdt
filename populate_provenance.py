"""
populate_provenance.py — Back-fill provenance records for facts in the database.

Reads plaintext sources from sources/ and their phrasal indices,
searches for supporting evidence for facts, and inserts provenance
records with exact character offsets.

Currently populates:
  1. Atlanticist member_of facts from VdL II declarations ZIP
  2. Education facts from DG/DDG CVs

Extendable to other fact types and sources.

Usage:
    python populate_provenance.py
"""
import sqlite3
import json
import os
import re
import pandas as pd

DB_PATH = 'euro_sdt.db'
SOURCES_DIR = 'sources'

# ── Helpers ─────────────────────────────────────────────────────────────────

def slugify(text):
    import unicodedata
    text = unicodedata.normalize('NFD', text)
    text = ''.join(c for c in text if unicodedata.category(c) != 'Mn')
    text = re.sub(r'[^a-zA-Z0-9\s\-]', '', text)
    return text.strip().lower().replace(' ', '-').replace('--', '-')


def read_source(subdir, doc_id):
    """Read plaintext and phrase index for a source document."""
    tpath = os.path.join(SOURCES_DIR, subdir, f'{doc_id}.txt')
    ppath = os.path.join(SOURCES_DIR, subdir, f'{doc_id}.phrases')
    if not os.path.exists(tpath) or not os.path.exists(ppath):
        return '', []
    with open(tpath) as f:
        text = f.read()
    phrases = []
    with open(ppath) as f:
        for line in f:
            parts = line.strip().split('\t')
            if len(parts) >= 3:
                phrases.append((int(parts[0]), int(parts[1]), parts[2]))
    return text, phrases


def find_quoting_phrase(text, phrases, org_name, commissioner_name=None):
    """Find the best matching phrase that mentions an organisation,
    optionally verifying the commissioner context.
    Returns (phrase_index, quote_text) or (None, '')."""
    candidates = []
    org_lower = org_name.lower()

    for idx, (start, end, sent) in enumerate(phrases):
        sent_lower = sent.lower()
        if org_lower not in sent_lower:
            # Also check raw text around the phrase boundaries
            chunk = text[max(0,start-50):end+50].lower()
            if org_lower not in chunk:
                continue
        # Prefer sentences that also mention the commissioner
        score = 1
        if commissioner_name:
            if commissioner_name.lower() in sent_lower:
                score += 5
            elif commissioner_name.lower() in text[max(0,start-200):end+200].lower():
                score += 2
        candidates.append((score, idx, sent.strip()))

    if not candidates:
        # Fall back: search raw text for any match
        idx = text.lower().find(org_lower)
        if idx >= 0:
            return 0, text[max(0, idx-100):idx+200].strip()
        return None, ''

    candidates.sort(key=lambda x: -x[0])
    _, phrase_idx, sent = candidates[0]
    return phrase_idx, sent


# ── Organisation name variants for fuzzy matching ───────────────────────────

ORG_VARIANTS = {
    'World Economic Forum': [
        'World Economic Forum', 'WEF', 'Board of Trustees', 'Global Advisory Committee'],
    'Munich Security Conference': [
        'Munich Security Conference', 'MSC', 'Advisory Board', 'Munich Security'],
    'Atlantic Council': [
        'Atlantic Council', 'Board of Advisors', 'EuroGrowth Initiative'],
    'Atlantic Council of Finland': [
        'Atlantic Council of Finland', 'Finnish Atlantic'],
    'Slovak Atlantic Commission': [
        'Slovak Atlantic Commission', 'SAC'],
    'ECFR': [
        'European Council on Foreign Relations', 'ECFR'],
    'GLOBSEC': [
        'GLOBSEC', 'Globsec'],
    'Friends of Europe': [
        'Friends of Europe', 'Board of Trustees'],
    'European Leadership Network': [
        'European Leadership Network', 'ELN'],
    'Elcano Royal Institute': [
        'Elcano', 'Elcano Royal Institute'],
    'IRI': [
        'International Republican Institute', 'IRI', 'NED'],
    'RAND Europe': [
        'RAND', 'RAND Corporation', 'RAND Europe'],
    'Bilderberg Group': [
        'Bilderberg'],
    'Trilateral Commission': [
        'Trilateral Commission'],
    'German Marshall Fund': [
        'German Marshall Fund', 'GMF'],
    'Council on Foreign Relations': [
        'Council on Foreign Relations', 'CFR'],
    'Wilfried Martens Centre': [
        'Wilfried Martens', 'Martens Centre'],
    'New Direction': [
        'New Direction', 'Foundation for European Conservatism'],
}


def find_org_in_text(text, org_name):
    """Check if any variant of an org name appears in text."""
    variants = ORG_VARIANTS.get(org_name, [org_name])
    for v in variants:
        if v.lower() in text.lower():
            return v
    return None


# ── Population logic ────────────────────────────────────────────────────────

def populate_declaration_provenance(db):
    """Match Atlanticist affiliation facts from the declarations ZIP."""
    print("Populating provenance from declarations ZIP...")

    # Build commissioner name → declaration doc_id mapping by scanning the directory
    name_docid = {}
    decl_dir = os.path.join(SOURCES_DIR, 'declarations')

    for fn in os.listdir(decl_dir):
        if not fn.endswith('.txt'): continue
        doc_id = fn.replace('.txt', '')
        # Read first 300 chars to find the commissioner name
        with open(os.path.join(decl_dir, fn)) as f:
            header = f.read(500)
        # Match: "Full Name : Andrius Kubilius" or similar
        m = re.search(r'Full\s*Name\s*:\s*([A-ZÁÉÍÓÚÀÈÌÒÙÄËÏÖÜČŠŽĆĐ][^\n<]{3,60})', header)
        if m:
            decl_name = m.group(1).strip()
            name_docid[decl_name] = doc_id
            print(f'    Mapped: {decl_name} → {doc_id}')

    # Get all Atlanticist member_of facts from the DB
    orgs = pd.read_csv('organisations_classified.csv')
    atl_orgs = orgs[orgs['atlanticist'] == True]['organisation'].tolist()

    # Get all commissioner → organisation member_of facts from comparison table
    atl_df = pd.read_csv('atlanticist_comparison.csv')
    body = atl_df[atl_df['Organisation'] != 'TOTAL (unique commissioners)']

    provenances = []
    unmatched = []
    count = 0

    for _, row in body.iterrows():
        org_name = row['Organisation']
        # Map comparison table name to canonical org entity
        short_name = re.sub(r'\s*\([^)]*\).*', '', org_name).strip()
        short_name = re.sub(r'\s*/\s*\w*$', '', short_name).strip()
        org_eid = slugify(short_name)

        # Map to organisations_classified.csv canonical
        canonical_map = {
            'iri': 'international-republican-institute',
            'nato-pa': 'nato-parliamentary-assembly',
            'bilderberg': 'bilderberg-group',
        }
        org_eid = canonical_map.get(org_eid, org_eid)

        col_map = {
            'VdL_II_202429': 'VdL_II_202429_commissioners',
        }
        names_str = str(row.get('VdL_II_202429_commissioners', ''))
        if not names_str or names_str == 'nan':
            continue

        for person_name in names_str.split(','):
            person_name = person_name.strip()
            if not person_name:
                continue
            person_eid = slugify(person_name)

            # Find corresponding fact in DB
            fact_row = db.execute(
                "SELECT id FROM fact WHERE entity_id=? AND predicate='member_of' AND object=?",
                (person_eid, org_eid)).fetchone()
            if not fact_row:
                # Try variant lookups
                for alt_oid in canonical_map.values():
                    fact_row = db.execute(
                        "SELECT id FROM fact WHERE entity_id=? AND predicate='member_of' AND object=?",
                        (person_eid, alt_oid)).fetchone()
                    if fact_row:
                        break
            if not fact_row:
                unmatched.append((person_name, org_name))
                continue

            # Find the declaration document
            doc_id = name_docid.get(person_name, '')
            if not doc_id:
                # Try variations of the name
                for n, did in name_docid.items():
                    if person_name.lower() in n.lower() or n.lower() in person_name.lower():
                        doc_id = did
                        break
            if not doc_id:
                unmatched.append((person_name, f'{org_name} (no decl doc)'))
                continue

            # Read source and find the quote
            text, phrases = read_source('declarations', doc_id)
            if not text:
                unmatched.append((person_name, f'{org_name} (source not found)'))
                continue

            phrase_idx, quote = find_quoting_phrase(
                text, phrases, short_name, person_name)

            if not quote:
                # Try broader search with variants
                for variant in ORG_VARIANTS.get(short_name, [short_name]):
                    phrase_idx, quote = find_quoting_phrase(
                        text, phrases, variant, person_name)
                    if quote:
                        break

            if quote and phrase_idx is not None:
                pid = f'prov-{fact_row[0][:8]}-{slugify(doc_id)[:20]}'
                # Get surrounding context from the phrases array
                ctx_sentences = []
                ctx_start = max(0, phrase_idx - 1)
                ctx_end   = min(len(phrases), phrase_idx + 2)
                for ci in range(ctx_start, ctx_end):
                    ctx_sentences.append(phrases[ci][2])
                context = ' '.join(ctx_sentences)

                db.execute(
                    "INSERT OR REPLACE INTO provenance (id, fact_id, citation_id, "
                    "quote_text, phrase_index, context_text) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    (pid, fact_row[0], 'cit-vdl2-declarations',
                     quote, phrase_idx, context))
                provenances.append((person_name, org_name, quote[:80]))
                count += 1
                if count % 5 == 0:
                    print(f'    {count} provenances...')
            else:
                unmatched.append((person_name, f'{org_name} (not found in decl)'))

    print(f'  {len(provenances)} provenances created')
    if unmatched:
        print(f'  {len(unmatched)} unmatched (sample):')
        for p, o in unmatched[:10]:
            print(f'    {p} → {o}')


def populate_dg_education_provenance(db):
    """Match education facts from DG/DDG CV PDFs."""
    print("\nPopulating provenance for DG/DDG education...")
    edu_facts = db.execute(
        "SELECT f.id, f.entity_id, f.object, f.object_type, "
        "  CASE WHEN f.object_type = 'entity_id' THEN e2.name ELSE f.object END as display_name, "
        "  e.name as person_name "
        "FROM fact f "
        "JOIN entity e ON e.id = f.entity_id "
        "LEFT JOIN entity e2 ON f.object_type = 'entity_id' AND e2.id = f.object "
        "WHERE f.predicate IN ('educated_at','studied_field','held_degree') "
        "AND e.type='person' AND e.category IN ('dg','ddg')"
    ).fetchall()

    count = 0
    for fact_id, entity_id, obj_raw, obj_type, display_name, person_name in edu_facts:
        safe_id = slugify(person_name)
        text, phrases = read_source('dg_cvs', safe_id)
        if not text:
            continue

        # Search for the display name in the CV text
        phrase_idx, quote = find_quoting_phrase(text, phrases, display_name)

        if quote and phrase_idx is not None:
            pid = f'prov-{fact_id[:8]}-edu'
            ctx_sentences = []
            ctx_start = max(0, phrase_idx - 1)
            ctx_end   = min(len(phrases), phrase_idx + 2)
            for ci in range(ctx_start, ctx_end):
                ctx_sentences.append(phrases[ci][2])
            context = ' '.join(ctx_sentences)

            db.execute(
                "INSERT OR REPLACE INTO provenance (id, fact_id, citation_id, "
                "quote_text, phrase_index, context_text) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (pid, fact_id, 'cit-dg-cvs',
                 quote, phrase_idx, context))
            count += 1

    print(f'  {count} education provenances for DG/DDGs')


# ── Main ────────────────────────────────────────────────────────────────────

def main():
    db = sqlite3.connect(DB_PATH)
    db.execute("PRAGMA foreign_keys = ON")

    populate_declaration_provenance(db)
    populate_dg_education_provenance(db)

    db.commit()

    total = db.execute("SELECT COUNT(*) FROM provenance").fetchone()[0]
    facts_w_prov = db.execute(
        "SELECT COUNT(DISTINCT fact_id) FROM provenance").fetchone()[0]
    total_facts = db.execute("SELECT COUNT(*) FROM fact").fetchone()[0]
    print(f'\nProvenance table: {total} records backing {facts_w_prov} facts '
          f'(of {total_facts} total facts)')
    db.close()


if __name__ == '__main__':
    main()
