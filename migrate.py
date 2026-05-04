"""
migrate.py — Populate the citation-anchored knowledge graph from existing CSV/JSON data.

Reads all existing datasets and populates SQLite tables: entity, fact, citation, provenance.
Run after creating the database with schema.sql.

Usage:
    sqlite3 euro_sdt.db < schema.sql
    python migrate.py
"""
import sqlite3
import uuid
import re
import json
import pandas as pd
from datetime import date

DB_PATH = 'euro_sdt.db'
TODAY   = date.today().isoformat()


# ── Helpers ─────────────────────────────────────────────────────────────────

def slug(text):
    """Generate a URL-safe slug from a display name."""
    import unicodedata
    text = unicodedata.normalize('NFD', text)
    text = ''.join(c for c in text if unicodedata.category(c) != 'Mn')
    text = re.sub(r'[^a-zA-Z0-9\s\-]', '', text)
    return text.strip().lower().replace(' ', '-').replace('--', '-')

def uid():
    return str(uuid.uuid4())[:12]

def insert_entity(db, id_, name, type_, category=None, country=None):
    db.execute(
        "INSERT OR REPLACE INTO entity (id, name, type, category, country, updated_at) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (id_, name, type_, category, country, TODAY))

def insert_fact(db, fact_id, entity_id, predicate, obj, obj_type='literal',
                qualifier=None, start_date=None, end_date=None, confidence='confirmed'):
    db.execute(
        "INSERT OR REPLACE INTO fact (id, entity_id, predicate, object, object_type, "
        "qualifier, start_date, end_date, confidence, updated_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (fact_id, entity_id, predicate, obj, obj_type,
         qualifier, start_date, end_date, confidence, TODAY))

def insert_citation(db, id_, source_name, source_type, url=None,
                    access_date=None, file_path=None, description=None):
    db.execute(
        "INSERT OR REPLACE INTO citation (id, source_name, source_type, url, "
        "access_date, file_path, description) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (id_, source_name, source_type, url, access_date, file_path, description))

def insert_provenance(db, id_, fact_id, citation_id, quote_text,
                      phrase_start=0, phrase_end=0, context_text=None):
    db.execute(
        "INSERT OR REPLACE INTO provenance (id, fact_id, citation_id, quote_text, "
        "phrase_start, phrase_end, context_text) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (id_, fact_id, citation_id, quote_text, phrase_start, phrase_end, context_text or quote_text))


# ── Main migration ──────────────────────────────────────────────────────────

def migrate():
    db = sqlite3.connect(DB_PATH)
    db.execute("PRAGMA foreign_keys = ON")

    # ── 1. Citations (sources) ──────────────────────────────────────────────

    CITATIONS = [
        ('cit-vdl2-declarations',
         "VdL II Declarations of Interests — Machine-Readable ZIP",
         'ec_declaration',
         'https://commission.europa.eu/publications/declarations-interests-commissioners-machine-readable-format_en',
         '2026-04-28',
         'Machine-Readable-DOIs.zip',
         'Downloaded April 2026 ZIP; parsed with parse_declarations.py'),

        ('cit-vdl2-wikipedia',
         "Wikipedia — Von der Leyen Commission II page",
         'wikipedia',
         'https://en.wikipedia.org/wiki/Von_der_Leyen_Commission_II',
         '2026-04-28', None,
         'Scraped with scrape_commission.py'),

        ('cit-commission-cvs-wikidata',
         "Wikidata SPARQL — Commissioner CVs (all commissions)",
         'wikidata',
         'https://query.wikidata.org/sparql',
         '2026-04-28', None,
         'CV data fetched via P39, P69, P106, P108, P102, P39, P569, P19 queries'),

        ('cit-dg-cvs',
         "Commission persons directory — DG/DDG CV PDFs",
         'commission_cv_pdf',
         'https://commission.europa.eu/persons_en',
         '2026-04-30',
         'commission_dg_cvs.csv',
         'CV PDFs linked from individual person pages; extracted with pypdf'),

        ('cit-cijeweb',
         "CJEU website — Members page",
         'cjeu_website',
         'https://www.curia.europa.eu/jcms/jcms/Jo2_7026/en/',
         '2026-04-29',
         'cjeu_bios_full.json',
         '10 biography blocks scraped from JS-rendered CJEU page'),

        ('cit-atlanticist-comparison',
         "Cross-commission Atlanticist comparison table (derived from multiple sources)",
         'dataset',
         None, None,
         'atlanticist_comparison.csv',
         'Aggregation of declaration, Wikidata, and Wikipedia keyword extraction'),

        ('cit-orgs-classified',
         "Organisations classified dataset (manually researched)",
         'dataset',
         None, None,
         'organisations_classified.csv',
         '34 orgs researched from websites, EU Transparency Register, annual reports'),

        ('cit-revolving-door',
         "EC ethics page — Revolving door decisions",
         'dataset',
         'https://commission.europa.eu/about/service-standards-and-principles/eth'
         'ics-and-good-administration/commissioners-and-ethics/former-european-commissioners-authorised-occupations_en',
         '2026-04-29',
         'commission_revolving_door.csv',
         'Scraped from EC ethics page; 194 approved post-mandate decisions'),
    ]

    for c in CITATIONS:
        insert_citation(db, *c)

    print("Citations: done.")

    # ── 2. Entities — Commissions ───────────────────────────────────────────

    COMMISSIONS = [
        ('commission-santer',  'Santer Commission',  'commission', None,    '1995-01-01', '1999-09-15', 20),
        ('commission-prodi',   'Prodi Commission',   'commission', None,    '1999-09-16', '2004-11-21', 21),
        ('commission-barroso-i','Barroso I',          'commission', None,    '2004-11-22', '2010-02-09', 30),
        ('commission-barroso-ii','Barroso II',         'commission', None,    '2010-02-10', '2014-10-31', 28),
        ('commission-juncker', 'Juncker Commission',   'commission', None,    '2014-11-01', '2019-11-30', 28),
        ('commission-vdl-i',   'VdL I Commission',     'commission', None,    '2019-12-01', '2024-11-30', 30),
        ('commission-vdl-ii',  'VdL II Commission',    'commission', None,    '2024-12-01', None,         27),
    ]

    for c in COMMISSIONS:
        id_, name, type_, _cat, start, end, _size = c
        insert_entity(db, id_, name, type_)
        db.execute("INSERT OR REPLACE INTO fact (id, entity_id, predicate, object, "
                   "object_type, qualifier, start_date, end_date, confidence, updated_at) "
                   "VALUES (?, ?, ?, ?, 'literal', NULL, ?, NULL, 'confirmed', ?)",
                   (uid(), id_, 'started_on', start, start, TODAY))

    print("Commissions: done.")

    # ── 3. Entities — Commissioners ─────────────────────────────────────────

    CC = {
        'AUT':'Austria','BEL':'Belgium','BGR':'Bulgaria','CYP':'Cyprus','CZE':'Czechia',
        'DEU':'Germany','DNK':'Denmark','ESP':'Spain','EST':'Estonia','FIN':'Finland',
        'FRA':'France','GBR':'UK','GRC':'Greece','HRV':'Croatia','HUN':'Hungary',
        'IRL':'Ireland','ITA':'Italy','LTU':'Lithuania','LUX':'Luxembourg','LVA':'Latvia',
        'MLT':'Malta','NLD':'Netherlands','POL':'Poland','PRT':'Portugal','ROU':'Romania',
        'SVK':'Slovakia','SVN':'Slovenia','SWE':'Sweden',
    }

    vdl1_countries = {
        'Ursula von der Leyen':'DEU','Margrethe Vestager':'DNK','Frans Timmermans':'NLD',
        'Valdis Dombrovskis':'LVA','Maroš Šefčovič':'SVK','Josep Borrell Fontelles':'ESP',
        'Věra Jourová':'CZE','Dubravka Šuica':'HRV','Margaritis Schinas':'GRC',
        'Johannes Hahn':'AUT','Nicolas Schmit':'LUX','Paolo Gentiloni':'ITA',
        'Janusz Wojciechowski':'POL','Elisa Ferreira':'PRT','Stella Kyriakides':'CYP',
        'Didier Reynders':'BEL','Helena Dalli':'MLT','Ylva Johansson':'SWE',
        'Janez Lenarčič':'SVN','Olivér Várhelyi':'HUN','Jutta Urpilainen':'FIN',
        'Kadri Simson':'EST','Mairead McGuinness':'IRL','Iliana Ivanova':'BGR',
        'Wopke Hoekstra':'NLD','Thierry Breton':'FRA','Mariya Gabriel':'BGR',
        'Phil Hogan':'IRL','Virginijus Sinkevičius':'LTU','Adina-Ioana Vălean':'ROU',
    }

    commission_files = [
        ('commission-santer',  'commission_santer_1995_1999.csv'),
        ('commission-prodi',   'commission_prodi_1999_2004.csv'),
        ('commission-barroso-i','commission_barroso_i_2004_2009.csv'),
        ('commission-barroso-ii','commission_barroso_ii_2010_2014.csv'),
        ('commission-juncker', 'commission_juncker_2014_2019.csv'),
        ('commission-vdl-i',   'commission_i_2019_2024.csv'),
        ('commission-vdl-ii',  'commission_2024_2029.csv'),
    ]

    for comm_id, csv_path in commission_files:
        df = pd.read_csv(csv_path)
        for _, row in df.iterrows():
            name = row['Name'].strip()
            eid  = slug(name)
            cc   = row.get('Country','') if 'Country' in row else vdl1_countries.get(name, '')
            cc   = str(cc).strip()
            country_name = CC.get(cc, cc)
            insert_entity(db, eid, name, 'person', 'commissioner', cc)

            # Served on commission
            insert_fact(db, uid(), eid, 'served_on_commission', comm_id,
                        obj_type='entity_id', confidence='confirmed',
                        start_date=str(row.get('start_date',''))[:10] if 'start_date' in row else None)

            # Country
            if cc:
                insert_fact(db, uid(), eid, 'nominated_by', cc,
                            obj_type='literal', confidence='confirmed')
            if country_name:
                insert_fact(db, uid(), eid, 'from_country', country_name,
                            obj_type='literal', confidence='confirmed')

            # Portfolio
            portfolio = row.get('Portfolio','')
            if portfolio and str(portfolio).strip():
                insert_fact(db, uid(), eid, 'held_portfolio', str(portfolio).strip())

    print(f"Commissioners: done. Entities: {db.execute('SELECT COUNT(*) FROM entity').fetchone()[0]}")

    # ── 4. Entities — Organisations ─────────────────────────────────────────

    # Map of canonical short-name → (long-name, full row) to avoid duplicate entities
    org_entities = {}

    orgs = pd.read_csv('organisations_classified.csv')
    for _, row in orgs.iterrows():
        name = row['organisation'].strip()
        short_name = re.sub(r'\s*\([^)]*\).*', '', name).strip()
        short_name = re.sub(r'\s*/\s*BofA.*', '', short_name).strip()
        oid = slug(short_name)

        if oid not in org_entities:
            org_entities[oid] = (short_name, row)
            insert_entity(db, oid, short_name, 'organisation', row.get('type',''),
                          row.get('headquarters',''))
        else:
            # Already exists — use the first entry's data
            pass

        # Classify
        if row.get('atlanticist'):
            insert_fact(db, uid(), oid, 'classified_as', 'atlanticist')
        if row.get('nato_adjacent'):
            insert_fact(db, uid(), oid, 'classified_as', 'nato_adjacent')
        if row.get('us_linked'):
            insert_fact(db, uid(), oid, 'classified_as', 'us_linked')

        # Funding and description
        if pd.notna(row.get('funding_notes','')):
            insert_fact(db, uid(), oid, 'funding_notes',
                        str(row['funding_notes']).strip())
        if pd.notna(row.get('description','')):
            insert_fact(db, uid(), oid, 'has_description',
                        str(row['description']).strip())

    print(f"Organisations: done.")

    # ── 5. Facts — Atlanticist affiliations from comparison table ────────────

    atl = pd.read_csv('atlanticist_comparison.csv')
    body = atl[atl['Organisation'] != 'TOTAL (unique commissioners)']

    col_map = {
        'Santer_199599': ('commission-santer',  'Santer_199599_commissioners'),
        'Prodi_199904':  ('commission-prodi',   'Prodi_199904_commissioners'),
        'Barroso_I_200409': ('commission-barroso-i','Barroso_I_200409_commissioners'),
        'Barroso_II_201014': ('commission-barroso-ii','Barroso_II_201014_commissioners'),
        'Juncker_201419': ('commission-juncker','Juncker_201419_commissioners'),
        'VdL_I_201924':   ('commission-vdl-i',  'VdL_I_201924_commissioners'),
        'VdL_II_202429':  ('commission-vdl-ii', 'VdL_II_202429_commissioners'),
    }

    # Manual mapping for abbreviation cases in atlanticist_comparison.csv
    ORG_ID_FIX = {
        'iri':                          'international-republican-institute',
        'iri-ned':                      'international-republican-institute',
        'irineg':                       'international-republican-institute',
        'german-marshall-fund':         'german-marshall-fund',
        'rand-europe':                  'rand-europe',
    }

    for _, row in body.iterrows():
        org_name = row['Organisation']
        short_name = re.sub(r'\s*\([^)]*\).*', '', org_name).strip()
        short_name = re.sub(r'\s*/\s*.*', '', short_name).strip()
        oid = slug(short_name)
        # Resolve known disambiguation cases
        oid = ORG_ID_FIX.get(oid, oid)
        for col_key, (comm_id, names_col) in col_map.items():
            names_str = str(row.get(names_col, ''))
            if not names_str or names_str == 'nan':
                continue
            for person_name in names_str.split(','):
                person_name = person_name.strip()
                if person_name:
                    eid = slug(person_name)
                    insert_fact(db, uid(), eid, 'member_of', oid,
                                obj_type='entity_id',
                                qualifier=org_name,
                                confidence='confirmed')

    print(f"Atlanticist facts: done.")

    # ── 6. Facts — Education from commissioner_education_by_country.csv ──────

    edu = pd.read_csv('commissioner_education_by_country.csv')
    edu = edu.drop_duplicates(subset='Name')

    for _, row in edu.iterrows():
        eid = slug(row['Name'])
        if row.get('Has_PhD'):
            insert_fact(db, uid(), eid, 'held_degree', 'PhD', confidence='confirmed')
        if row.get('Has_Law'):
            insert_fact(db, uid(), eid, 'studied_field', 'Law', confidence='confirmed')
        if row.get('Has_Economics'):
            insert_fact(db, uid(), eid, 'studied_field', 'Economics', confidence='confirmed')
        if row.get('Has_PolSci'):
            insert_fact(db, uid(), eid, 'studied_field', 'Political Science', confidence='confirmed')

        named = str(row.get('Named_institutions', ''))
        if named and named != 'nan':
            for inst in named.split('|'):
                inst = inst.strip()
                if inst:
                    iid = slug(inst)
                    insert_entity(db, iid, inst, 'institution', 'university')
                    insert_fact(db, uid(), eid, 'educated_at', iid,
                                obj_type='entity_id', confidence='confirmed')

    print(f"Education facts: done.")

    # ── 7. Facts — Senior officials (DG/DDG) ────────────────────────────────

    dg = pd.read_csv('commission_senior_officials.csv')
    dg = dg[~dg['role'].isin({'Commissioner','Executive Vice-President','Vice-President','President','President of the'})]

    for _, row in dg.iterrows():
        name = row['name'].strip()
        if len(name) < 3: continue
        eid = slug(name)
        cat = 'dg' if 'Director-General' in str(row['role']) or 'Secretary-General' in str(row['role']) else 'ddg'
        insert_entity(db, eid, name, 'person', cat)

        insert_fact(db, uid(), eid, 'held_position',
                    f"{row['role']} → {row.get('department','')}",
                    obj_type='literal',
                    confidence='confirmed')

    print(f"Senior officials: done.")

    # ── 7b. Facts — DG/DDG Education (from CV PDFs) ─────────────────────────

    dg_cvs = pd.read_csv('commission_dg_cvs.csv')
    dg_cvs = dg_cvs[dg_cvs['cv_text'].fillna('') != '']

    # Education patterns for CV text
    DG_UNI_PATTERNS = [
        ('College of Europe',            r'college of europe|collège d.europe'),
        ('ULB Brussels',                 r'université libre de bruxelles|\bulb\b|free university.*brussels'),
        ('University of Oxford',         r'corpus christi.*oxford|oxford university|university of oxford'),
        ('University of Cambridge',      r'trinity hall|king.s college.*cambridge|cambridge university|university of cambridge'),
        ('Harvard University',           r'harvard'),
        ('LSE',                          r'london school of economics|\blse\b'),
        ('Sciences Po',                  r'sciences po|institut d.études politiques'),
        ('University of Bonn',           r'\bbonn\b.*universit|universit.*bonn'),
        ('Trinity College Dublin',       r'trinity.*dublin'),
        ('University College Dublin',    r'university college dublin|\bucd\b'),
        ('University of Heidelberg',     r'heidelberg.*universit|universit.*heidelberg'),
        ('University of Freiburg',       r'freiburg.*universit|universit.*freiburg'),
        ('University of Amsterdam',      r'universiteit van amsterdam|university of amsterdam'),
        ('University of Warsaw',         r'warsaw.*universit|uniwersytet warszawski'),
        ('University of Lund',           r'lund.*universit|universit.*lund'),
        ('University of Vienna',         r'wien.*universit|university of vienna|universität wien'),
        ('University of Helsinki',       r'helsinki.*universit|universit.*helsinki'),
        ('Bocconi University',           r'bocconi'),
        ('Stockholm University',         r'stockholm.*universit|universit.*stockholm'),
        ('Central European University',  r'central european university|\bceu\b'),
        ('UNWE Sofia',                   r'national and world economy|unwe'),
        ('University of Glasgow',        r'glasgow.*universit|universit.*glasgow'),
        ('University of Hull',           r'hull.*universit|universit.*hull'),
        ('University of Montpellier',    r'montpellier'),
        ('Université Catholique Louvain',r'catholique.*louvain|uclouvain'),
        ('KU Leuven',                    r'ku leuven|katholieke universiteit leuven'),
        ('VUB Brussels',                 r'vrije universiteit brussel|\bvub\b'),
    ]

    DG_DEG_PATTERNS = [
        ('Economics',           r'economics|économie|économiste|economic(?!.*development)'),
        ('Law',                 r'law degree|studied law|faculty of law|\bllm\b|\bllb\b|master.*law|maître en droit|doctor.*law|juris'),
        ('Political Science',   r'political science|sciences politiques|politique'),
        ('Public Administration', r'public administration|administrative|governance'),
        ('European Studies',    r'european studies|european affairs|études européennes'),
        ('Agronomy',            r'agronomi|ingénieur.*agri|génie rural'),
    ]

    edu_count = 0
    for _, row in dg_cvs.iterrows():
        name = row['name'].strip()
        if not name or len(name) < 3:
            continue
        eid = slug(name)
        text = str(row['cv_text']).lower()

        for uni_label, uni_pat in DG_UNI_PATTERNS:
            m = re.search(uni_pat, text, re.I)
            if m:
                # Get exact matched text for the institution name
                matched_text = m.group(0).strip()
                # Normalise university entity ID
                uni_eid = slug(matched_text[:40])  # cap for very long matches
                # Use canonical slug for known institutions
                canonical = {
                    slug('lse'):                        'lse',
                    slug('bocconi'):                    'bocconi-university',
                    slug('sciences-po'):                'sciences-po',
                    slug('harvard'):                    'harvard-university',
                    slug('vub-brussels'):               'vub-brussels',
                    slug('université-catholique-louvain'):'universite-catholique-louvain',
                }
                uni_eid = canonical.get(uni_eid, uni_eid)
                # Ensure entity exists
                insert_entity(db, uni_eid, matched_text[:80].title(), 'institution', 'university')
                insert_fact(db, uid(), eid, 'educated_at', uni_eid,
                            obj_type='entity_id', confidence='confirmed')
                edu_count += 1

        # Parse academic qualification lines for degree types
        qual_matches = re.findall(
            r'(?:academic qualif|qualif).*?(?:\n.*?){0,30}(?:professional experience|$)', text, re.I|re.S)
        qual_text = ' '.join(qual_matches) if qual_matches else text[:2000]
        for deg_label, deg_pat in DG_DEG_PATTERNS:
            if re.search(deg_pat, qual_text, re.I):
                insert_fact(db, uid(), eid, 'studied_field', deg_label,
                            obj_type='literal', confidence='confirmed')
                edu_count += 1

        # PhD
        if re.search(r'\bphd\b|ph\.d\.|doctorate|doctor of(?! law)|dr\. iur|doktor', text, re.I):
            insert_fact(db, uid(), eid, 'held_degree', 'PhD / Doctorate',
                        obj_type='literal', confidence='confirmed')
            edu_count += 1

    print(f"DG/DDG education facts: {edu_count}")

    # ── 8. Facts — Revolving door ───────────────────────────────────────────

    rd = pd.read_csv('commission_revolving_door.csv')
    for _, row in rd.iterrows():
        name = str(row['name']).strip()
        if not name or name == 'nan': continue
        eid = slug(name)
        # Ensure entity exists (some revolving-door names not in commissioner CSVs)
        insert_entity(db, eid, name, 'person', 'commissioner')
        occupation = str(row.get('occupation','')).strip()
        if occupation and occupation != 'nan':
            insert_fact(db, uid(), eid, 'post_mandate_occupation',
                        occupation,
                        obj_type='literal',
                        qualifier=str(row.get('commission','')),
                        start_date=str(row.get('year',''))[:4],
                        confidence='confirmed')

    print(f"Revolving door: done.")

    # ── 9. Facts — CJEU ─────────────────────────────────────────────────────

    cjeu = pd.read_csv('cjeu_members_list.csv')
    for _, row in cjeu.iterrows():
        name = row['Name'].strip()
        eid = slug(name)
        insert_entity(db, eid, name, 'person', 'cjeu_judge' if row['Court']=='CJ' else 'cjeu_ag',
                      row.get('Country',''))
        insert_fact(db, uid(), eid, 'held_position', row['Role'],
                    obj_type='literal', confidence='confirmed')

    print(f"CJEU: done.")

    db.commit()
    stats = {
        'entities':  db.execute('SELECT COUNT(*) FROM entity').fetchone()[0],
        'facts':     db.execute('SELECT COUNT(*) FROM fact').fetchone()[0],
        'citations': db.execute('SELECT COUNT(*) FROM citation').fetchone()[0],
    }
    print(f"\nMigration complete. {stats['entities']} entities, {stats['facts']} facts, {stats['citations']} citations.")
    db.close()


if __name__ == '__main__':
    migrate()
