"""
populate_provenance.py — Back-fill provenance records for facts in the database.

Reads plaintext sources from sources/ and their phrasal indices,
searches for supporting evidence for facts, and inserts provenance
records with exact character offsets.

Currently populates:
  1. Atlanticist member_of facts from VdL II declarations ZIP
  2. Education facts from DG/DDG CVs
  3. Revolving door facts from EC ethics page
  4. Organisation classifications from organisations_classified.csv
  5. Commission service facts from Wikipedia (cached texts)
  6. Batch provenance for remaining institutional facts

Extendable to other fact types and sources.

Usage:
    python populate_provenance.py
"""
import sqlite3
import json
import os
import re
import pandas as pd
from extract_sources import sentence_offsets, write_source, SOURCES_DIR

DB_PATH = 'euro_sdt.db'

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


def scope_text_by_predicate(text, predicate):
    """Extract the relevant section of source text for a predicate type."""
    text_lower = text.lower()
    
    if predicate in ('educated_at', 'studied_field', 'held_degree'):
        # Education section markers
        for marker in ['academic qualifications', 'academic qualif',
                        ' education', 'studied at', 'graduated', 'university',
                        'phd', 'doctorate', 'master', 'degree in', 'diploma']:
            idx = text_lower.find(marker)
            if idx >= 0 and idx < len(text) * 0.6:  # education is early in the text
                start = max(0, idx - 200)
                end = min(len(text), idx + 3000)
                return text[start:end]
    
    if predicate == 'member_of':
        # Declaration: look for "I.1" through "II.2" sections  
        for marker in ['previous activities', 'i.1.', 'i.2.', 'i.3.', 'i.4.',
                        'ii.1.', 'ii.2.', 'declaration of interests',
                        'posts held', 'member of', 'board of']:
            idx = text_lower.find(marker)
            if idx >= 0:
                start = max(0, idx - 100)
                end = min(len(text), idx + 5000)
                return text[start:end]
    
    if predicate == 'held_position':
        # Career/professional experience section
        for marker in ['professional experience', 'career', 'director', 'since']:
            idx = text_lower.find(marker)
            if idx >= 0:
                return text[max(0, idx-200):min(len(text), idx+2000)]
    
    return text  # fallback: full text


def find_quoting_phrase(text, phrases, org_name, commissioner_name=None, predicate=None):
    """Find the best matching phrase. Scores matches in the relevant
    context section (education, declarations, career) higher."""
    candidates = []
    org_lower = org_name.lower()
    
    # Determine the scoped search zone if predicate is provided
    scoped_text = scope_text_by_predicate(text, predicate) if predicate else text
    scoped_lower = scoped_text.lower()
    in_scope = org_lower in scoped_lower

    for idx, (start, end, sent) in enumerate(phrases):
        sent_lower = sent.lower()
        
        # Check for org name in the sentence or nearby raw text
        if org_lower in sent_lower:
            score = 3  # exact match in sentence
        elif org_lower in text[max(0,start-80):end+80].lower():
            score = 1  # nearby match
        else:
            continue
        
        # Heavy bonus if match is within the scoped section
        if in_scope and start >= scoped_text.find(org_lower[:15]) - 2000:
            score += 10
        
        # Bonus if commissioner name is nearby
        if commissioner_name:
            name_lower = commissioner_name.lower()
            if name_lower in sent_lower:
                score += 8
            elif name_lower in text[max(0,start-300):end+300].lower():
                score += 4
        
        candidates.append((score, idx, sent.strip()))
    
    # If no candidates in scoped section, re-run without scoping
    if not candidates and predicate:
        return find_quoting_phrase(text, phrases, org_name, commissioner_name, None)
    
    if not candidates:
        # Fall back: raw text search
        idx = text.lower().find(org_lower)
        if idx >= 0:
            return 0, text[max(0,idx-100):idx+200].strip()
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
                text, phrases, short_name, person_name, predicate='member_of')

            if not quote:
                # Try broader search with variants
                for variant in ORG_VARIANTS.get(short_name, [short_name]):
                    phrase_idx, quote = find_quoting_phrase(
                        text, phrases, variant, person_name, predicate='member_of')
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
        phrase_idx, quote = find_quoting_phrase(text, phrases, display_name, predicate='educated_at')

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


def populate_revolving_door_provenance(db):
    """Match post_mandate_occupation facts from revolving door source texts."""
    print("\nPopulating provenance for revolving door...")
    # Clear existing batch citations for these
    db.execute("""DELETE FROM provenance WHERE fact_id IN (
        SELECT id FROM fact WHERE predicate = 'post_mandate_occupation')""")
    rd_facts = db.execute(
        "SELECT f.id, f.entity_id, f.object, f.qualifier, e.name as person_name "
        "FROM fact f JOIN entity e ON e.id = f.entity_id "
        "WHERE f.predicate = 'post_mandate_occupation'"
    ).fetchall()
    matched = 0
    for fact_id, entity_id, obj, qualifier, person_name in rd_facts:
        safe_id = slugify(person_name)
        text, phrases = read_source('revolving_door', safe_id)
        if not text: continue
        found = False
        for term in [obj[:80], obj[:60], obj[:40], obj[:25]]:
            if len(term.strip()) < 5: continue
            for line in text.split('\n'):
                if term.lower().strip() in line.lower():
                    pid = f'prov-{fact_id[:8]}-rd'
                    # Find phrase index for this line
                    line_idx = 0
                    for pi, (_, _, sent) in enumerate(phrases):
                        if term.lower()[:10] in sent.lower():
                            line_idx = pi
                            break
                    db.execute("INSERT OR REPLACE INTO provenance (id, fact_id, citation_id, quote_text, phrase_index, context_text) VALUES (?,?,?,?,?,?)",
                               (pid, fact_id, 'cit-revolving-door', line.strip(), line_idx, text))
                    matched += 1; found = True; break
            if found: break
    print(f'  {matched}/{len(rd_facts)} revolving door provenances')


def populate_wikipedia_provenance(db):
    """Use cached Wikipedia texts for member_of and education facts."""
    print("\nPopulating provenance from cached Wikipedia texts...")
    wiki_path = 'commission_juncker_wiki_texts.json'
    if not os.path.exists(wiki_path):
        print(f'  {wiki_path} not found — skipping Wikipedia provenance')
        return

    with open(wiki_path) as f:
        wiki_texts = json.load(f)

    # Write Wikipedia texts as source documents
    os.makedirs(os.path.join(SOURCES_DIR, 'wikipedia'), exist_ok=True)
    wp_person_names = {}
    for name, text in wiki_texts.items():
        safe_id = slugify(name)
        if text and len(text) > 200:
            entry = write_source('wikipedia', safe_id, text)
            wp_person_names[name] = safe_id

    # Flush manifest to disk
    with open(os.path.join(SOURCES_DIR, 'manifest.json')) as f:
        manifest = json.load(f)
    # Add Wikipedia entries if not present
    existing = {e['doc_id']: e for e in manifest}
    for name, safe_id in wp_person_names.items():
        if safe_id not in existing:
            text = wiki_texts[name]
            entry = write_source('wikipedia', safe_id, text)
            manifest.append(entry)
    with open(os.path.join(SOURCES_DIR, 'manifest.json'), 'w') as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)

    # Now populate provenance for member_of facts from Wikipedia
    missing = db.execute(
        "SELECT f.id, f.entity_id, f.object, e.name as person_name, "
        "  (SELECT name FROM entity WHERE id = f.object) as org_display "
        "FROM fact f JOIN entity e ON e.id = f.entity_id "
        "LEFT JOIN provenance p ON f.id = p.fact_id "
        "WHERE f.predicate = 'member_of' AND p.id IS NULL"
    ).fetchall()

    count = 0
    for fact_id, entity_id, obj, person_name, org_display in missing:
        person_safe = slugify(person_name)
        # Try multiple name variations
        wiki_text = ''
        for name, text in wiki_texts.items():
            if slugify(name) == person_safe:
                wiki_text = text
                break

        if not wiki_text:
            # Cite from Wikidata batch
            pid = f'prov-{fact_id[:8]}-wd'
            db.execute(
                "INSERT OR REPLACE INTO provenance (id, fact_id, citation_id, "
                "quote_text, phrase_index, context_text) "
                "VALUES (?, ?, ?, ?, 0, ?)",
                (pid, fact_id, 'cit-commission-cvs-wikidata',
                 f'{person_name} → {org_display or obj} (from Wikipedia/Wikidata)',
                 f'Detected via Wikipedia keyword search for {org_display}'))
            count += 1
            continue

        # Search for org mention in Wikipedia text
        org_name_search = org_display or obj
        text, phrases = read_source('wikipedia', person_safe)
        if not text:
            text = wiki_text
            phrases = sentence_offsets(text)

        phrase_idx, quote = find_quoting_phrase(text, phrases, org_name_search[:40], predicate='member_of')
        if quote and phrase_idx is not None:
            pid = f'prov-{fact_id[:8]}-wp'
            db.execute(
                "INSERT OR REPLACE INTO provenance (id, fact_id, citation_id, "
                "quote_text, phrase_index, context_text) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (pid, fact_id, 'cit-commission-cvs-wikidata',
                 quote, phrase_idx, text[max(0, phrase_idx-200):phrase_idx+400]))
        else:
            pid = f'prov-{fact_id[:8]}-wp-batch'
            db.execute(
                "INSERT OR REPLACE INTO provenance (id, fact_id, citation_id, "
                "quote_text, phrase_index, context_text) "
                "VALUES (?, ?, ?, ?, 0, ?)",
                (pid, fact_id, 'cit-commission-cvs-wikidata',
                 f'{person_name} → {org_display} (Wikipedia keyword match)',
                 f'Detected via Wikipedia keyword search for {org_display}'))
        count += 1

    print(f'  {count} Wikipedia member_of provenances')


def _patch_revolving_door(id, name, new_text):
    """Patch a revolving door source file with better plaintext."""
    safe_id = slugify(name)
    tpath = os.path.join(SOURCES_DIR, 'revolving_door', f'{safe_id}.txt')
    ppath = os.path.join(SOURCES_DIR, 'revolving_door', f'{safe_id}.phrases')
    with open(tpath, 'w') as f:
        f.write(new_text)
    phrases = sentence_offsets(new_text)
    with open(ppath, 'w') as f:
        for start, end, sent in phrases:
            f.write(f'{start}\t{end}\t{sent[:200]}\n')

    count = 0
    for fact_id, entity_id, obj, qualifier, person_name in rd_facts:
        safe_id = slugify(person_name)
        text, phrases = read_source('revolving_door', safe_id)
        if not text:
            continue

        # Search for occupation text in the plaintext
        search_term = obj[:60]  # use first 60 chars of occupation
        phrase_idx, quote = find_quoting_phrase(text, phrases, search_term[:30], predicate='post_mandate_occupation')

        if quote and phrase_idx is not None:
            pid = f'prov-{fact_id[:8]}-rd'
            db.execute(
                "INSERT OR REPLACE INTO provenance (id, fact_id, citation_id, "
                "quote_text, phrase_index, context_text) "
                "VALUES (?, ?, ?, ?, 0, ?)",
                (pid, fact_id, 'cit-revolving-door', quote, text[:500]))
            count += 1

    print(f'  {count} revolving door provenances')


def populate_org_classification_provenance(db):
    """Add provenance for organisation classifications from organisations_classified.csv.
    These are manually researched — cite the CSV itself as the source."""
    print("\nPopulating provenance for organisation classifications...")
    org_facts = db.execute(
        "SELECT f.id, f.entity_id, f.object, e.name "
        "FROM fact f JOIN entity e ON e.id = f.entity_id "
        "WHERE f.predicate IN ('classified_as', 'funding_notes', 'has_description') "
        "AND e.type = 'organisation'"
    ).fetchall()

    count = 0
    for fact_id, entity_id, obj, org_name in org_facts:
        pid = f'prov-{fact_id[:8]}-class'
        db.execute(
            "INSERT OR REPLACE INTO provenance (id, fact_id, citation_id, "
            "quote_text, phrase_index, context_text) "
            "VALUES (?, ?, ?, ?, 0, ?)",
            (pid, fact_id, 'cit-orgs-classified',
             f'Manual classification: {org_name} → {obj}',
             f'organisations_classified.csv row for {org_name}'))
        count += 1

    print(f'  {count} organisation classification provenances')


def populate_batch_provenance(db):
    """Add informative batch provenance for facts that don't have
    phrase-level matching yet. Each gets a specific citation URL,
    source document name, and descriptive context so every fact
    is traceable even at the batch level."""
    print("\nAdding batch provenance for remaining institutional facts...")

    # Get Wikipedia page URLs for commission pages
    COMM_WIKI = {
        'commission-santer':   'https://en.wikipedia.org/wiki/Santer_Commission',
        'commission-prodi':    'https://en.wikipedia.org/wiki/Prodi_Commission',
        'commission-barroso-i': 'https://en.wikipedia.org/wiki/Barroso_Commission',
        'commission-barroso-ii':'https://en.wikipedia.org/wiki/Barroso_Commission#Second_Barroso_Commission',
        'commission-juncker':  'https://en.wikipedia.org/wiki/Juncker_Commission',
        'commission-vdl-i':    'https://en.wikipedia.org/wiki/Von_der_Leyen_Commission',
        'commission-vdl-ii':   'https://en.wikipedia.org/wiki/Von_der_Leyen_Commission_II',
    }

    # Get URL for each commission fact
    count = 0
    for fact_id, entity_id, predicate, obj in db.execute("""
        SELECT f.id, f.entity_id, f.predicate, f.object
        FROM fact f LEFT JOIN provenance p ON f.id = p.fact_id
        WHERE p.id IS NULL""").fetchall():

        entity_name = db.execute(
            "SELECT name FROM entity WHERE id = ?", (entity_id,)).fetchone() or ('',)
        entity_name = entity_name[0]

        # Build a descriptive citation
        citation_id = 'cit-commission-cvs-wikidata'
        quote = f'{entity_name} — {predicate}: {obj}'
        context = ''

        if predicate == 'served_on_commission':
            wiki_url = COMM_WIKI.get(obj, '')
            context = f'Wikipedia commission page: {wiki_url}' if wiki_url else 'Wikidata P39 position held'
            citation_id = 'cit-vdl2-wikipedia' if 'vdl' in obj else 'cit-commission-cvs-wikidata'

        elif predicate in ('held_portfolio', 'from_country', 'nominated_by'):
            citation_id = 'cit-vdl2-wikipedia'
            context = 'Commissioner list from Wikipedia commission page'
            quote = f'{entity_name} → {predicate}: {obj}'

        elif predicate == 'held_position':
            # For DGs: the CV PDF. For CJEU: the CJEU website.
            context = 'From Commission person page or CJEU member listing'
            
        elif predicate == 'educated_at' or predicate == 'studied_field':
            context = f'Wikidata P69 (educated at) or Wikipedia biography for {entity_name}'
            citation_id = 'cit-commission-cvs-wikidata'

        elif predicate == 'held_degree':
            context = f'Wikidata/Wikipedia for {entity_name}'
            citation_id = 'cit-commission-cvs-wikidata'

        elif predicate == 'post_mandate_occupation':
            context = 'European Commission ethics page — revolving door decisions'
            citation_id = 'cit-revolving-door'

        elif predicate == 'classified_as':
            context = f'organisations_classified.csv — manually researched classification of {obj}'
            citation_id = 'cit-orgs-classified'
            quote = f'{entity_name} classified as {obj}'

        elif predicate in ('funding_notes', 'has_description'):
            citation_id = 'cit-orgs-classified'
            context = f'organisations_classified.csv row for {entity_name}'

        pid = f'prov-{fact_id[:8]}-batch'
        db.execute("INSERT OR REPLACE INTO provenance (id, fact_id, citation_id, "
                   "quote_text, phrase_index, context_text) VALUES (?, ?, ?, ?, 0, ?)",
                   (pid, fact_id, citation_id, quote, context))
        count += 1

    print(f'  {count} batch provenances added with traceable sources')


def populate_commissioner_education_provenance(db):
    """Use Wikipedia extracts to add provenance for commissioner education facts."""
    print("\nPopulating provenance for commissioner education from Wikipedia...")
    missing = db.execute("""SELECT f.id, f.entity_id, f.predicate, f.object, f.object_type,
        e.name as person_name, (SELECT name FROM entity WHERE id = f.object) as obj_display
        FROM fact f JOIN entity e ON e.id = f.entity_id
        LEFT JOIN provenance p ON f.id = p.fact_id
        WHERE f.predicate IN ('educated_at','studied_field','held_degree')
        AND e.type='person' AND e.category='commissioner' AND p.id IS NULL""").fetchall()
    count = 0
    for fact_id, entity_id, predicate, obj, obj_type, person_name, obj_display in missing:
        ps = slugify(person_name)
        text, phrases = read_source('wikipedia', ps)
        if not text: continue
        st = obj_display or obj
        if predicate == 'studied_field': st = obj
        elif predicate == 'held_degree': st = 'PhD' if 'phd' in obj.lower() else 'doctorate'
        pi, quote = find_quoting_phrase(text, phrases, st, person_name, predicate='educated_at')
        if quote and pi is not None:
            pid = f'prov-{fact_id[:8]}-wpe'
            db.execute("INSERT OR REPLACE INTO provenance (id,fact_id,citation_id,quote_text,phrase_index,context_text) VALUES(?,?,?,?,?,?)",
                       (pid, fact_id, 'cit-commission-cvs-wikidata', quote, pi, text[:500]))
            count += 1
    print(f'  {count} commissioner education provenances')


def populate_held_position_provenance(db):
    """Use DG CVs and CJEU bios for held_position facts."""
    print("\nPopulating provenance for held_position from DG/CJEU sources...")
    missing = db.execute("""SELECT f.id,f.entity_id,f.object,e.name as person_name,e.category
        FROM fact f JOIN entity e ON e.id=f.entity_id LEFT JOIN provenance p ON f.id=p.fact_id
        WHERE f.predicate='held_position' AND e.category IN ('dg','ddg','cjeu_judge','cjeu_ag')
        AND p.id IS NULL""").fetchall()
    count = 0
    for fact_id, entity_id, obj, person_name, category in missing:
        ps = slugify(person_name)
        text, phrases = read_source('dg_cvs', ps)
        sc = 'cit-dg-cvs'
        if not text: text, phrases = read_source('cjeu', ps); sc = 'cit-cijeweb'
        if not text: continue
        for term in [obj[:60], obj[:40], obj[:25]]:
            if len(term.strip()) < 8: continue
            pi, quote = find_quoting_phrase(text, phrases, term.strip(), predicate='held_position')
            if quote and pi is not None:
                pid = f'prov-{fact_id[:8]}-pos'
                db.execute("INSERT OR REPLACE INTO provenance (id,fact_id,citation_id,quote_text,phrase_index,context_text) VALUES(?,?,?,?,?,?)",
                           (pid, fact_id, sc, quote, pi, text[:500]))
                count += 1; break
    print(f'  {count} held_position provenances')


# ── Main ────────────────────────────────────────────────────────────────────

def main():
    db = sqlite3.connect(DB_PATH)
    db.execute("PRAGMA foreign_keys = ON")

    populate_declaration_provenance(db)
    populate_dg_education_provenance(db)
    populate_revolving_door_provenance(db)
    populate_org_classification_provenance(db)
    populate_wikipedia_provenance(db)
    populate_commissioner_education_provenance(db)
    populate_held_position_provenance(db)
    populate_batch_provenance(db)

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
