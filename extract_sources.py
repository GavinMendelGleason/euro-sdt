"""
extract_sources.py — Extract plaintext from all source documents and build
phrasal chunk indices for provenance citation.

Processes:
  - Commission declarations ZIP (OOXML)
  - DG/DDG CV PDFs
  - Commissioner Wikipedia articles (via Wikidata sitelinks)
  - CJEU website biographies
  - Revolving door decisions
  - EP hearing PDFs

Output:
  sources/manifest.json           — index of all source documents
  sources/{type}/{doc_id}.txt     — cleaned plaintext
  sources/{type}/{doc_id}.phrases — sentence boundary offsets (character-indexed)

Usage:
    python extract_sources.py
"""
import os
import re
import json
import zipfile
import io
import urllib.request
import urllib.parse
from datetime import date
from xml.etree import ElementTree as ET
import pandas as pd

SOURCES_DIR = 'sources'
TODAY = date.today().isoformat()

NS = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'


# ── Sentence tokenisation ───────────────────────────────────────────────────

try:
    import spacy
    nlp = spacy.load('en_core_web_sm')
    USE_SPACY = True
    print("spaCy available — using for sentence tokenisation")
except (ImportError, OSError):
    USE_SPACY = False
    print("spaCy not available — using regex fallback for sentence tokenisation")


def sentence_offsets(text):
    """Return list of (start, end, sentence_text) tuples."""
    if USE_SPACY:
        doc = nlp(text)
        return [(sent.start_char, sent.end_char, sent.text) for sent in doc.sents]

    # Regex fallback: split on sentence-ending punctuation followed by space + capital
    offsets = []
    for m in re.finditer(r'(.*?[.!?])\s+(?=[A-ZÁÉÍÓÚÀÈÌÒÙÄËÏÖÜČŠŽĆĐ])', text):
        start = m.start()
        end = m.end()
        offsets.append((start, end - len(m.group(2)) if m.lastindex else end,
                        m.group(1).strip()))
    # Last sentence
    if offsets:
        last_end = offsets[-1][1]
        remaining = text[last_end:].strip()
        if remaining:
            offsets.append((last_end, len(text), remaining))
    else:
        offsets.append((0, len(text), text.strip()))
    return offsets


# ── Helpers ─────────────────────────────────────────────────────────────────

def write_source(subdir, doc_id, text):
    """Write plaintext + phrase index, update manifest."""
    # Sanitise doc_id: strip non-ASCII chars for filesystem safety
    import unicodedata
    safe_id = unicodedata.normalize('NFD', doc_id)
    safe_id = ''.join(c for c in safe_id if unicodedata.category(c) != 'Mn')
    safe_id = re.sub(r'[^a-zA-Z0-9\s\-\.]', '', safe_id)
    safe_id = safe_id.strip().replace(' ', '-').replace('--', '-')

    subdir_path = os.path.join(SOURCES_DIR, subdir)
    os.makedirs(subdir_path, exist_ok=True)
    tpath = os.path.join(subdir_path, f'{safe_id}.txt')
    ppath = os.path.join(subdir_path, f'{safe_id}.phrases')

    with open(tpath, 'w') as f:
        f.write(text)

    phrases = sentence_offsets(text)
    with open(ppath, 'w') as f:
        for start, end, sent in phrases:
            f.write(f'{start}\t{end}\t{sent[:200]}\n')

    return {
        'doc_id': safe_id,
        'subdir': subdir,
        'char_count': len(text),
        'sentence_count': len(phrases),
        'path': f'{subdir}/{safe_id}.txt',
    }


def fetch_html(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    try:
        return urllib.request.urlopen(req, timeout=15).read().decode('utf-8', errors='ignore')
    except Exception as e:
        print(f'    Error fetching {url}: {e}')
        return ''


# ── Source extractors ───────────────────────────────────────────────────────

def extract_declarations():
    """Extract plaintext from Machine-Readable-DOIs.zip (OOXML)."""
    manifest = []
    zip_path = 'Machine-Readable-DOIs.zip'
    if not os.path.exists(zip_path):
        print('  Declarations ZIP not found — skipping')
        return manifest

    with zipfile.ZipFile(zip_path) as zf:
        xml_files = [n for n in zf.namelist() if n.endswith('.xml') and 'Test Form' not in n]
        for fname in xml_files:
            doc_id = re.sub(r'\.xml$', '', fname.split('/')[-1])
            doc_id = re.sub(r'\s*\(\d+\)$', '', doc_id)
            doc_id = doc_id.lower().replace(' ', '-').replace('--', '-')
            try:
                xml_bytes = zf.read(fname)
                root = ET.fromstring(xml_bytes)
                # Extract all text runs
                texts = []
                for t in root.iter(NS + 't'):
                    if t.text:
                        texts.append(t.text)
                full_text = ' '.join(texts)
                if len(full_text) > 100:
                    entry = write_source('declarations', doc_id, full_text)
                    manifest.append(entry)
            except Exception as e:
                print(f'    Error {fname}: {e}')

    print(f'  Declarations: {len(manifest)} documents')
    return manifest


def extract_dg_cvs():
    """Extract plaintext from DG/DDG CV PDFs already downloaded."""
    manifest = []
    cv_path = 'commission_dg_cvs.csv'
    if not os.path.exists(cv_path):
        print('  DG CVs CSV not found — skipping')
        return manifest

    df = pd.read_csv(cv_path)
    df = df[df['cv_text'].fillna('') != '']
    for _, row in df.iterrows():
        text = str(row['cv_text'])
        doc_id = re.sub(r'[^a-zA-Z0-9\s\-]', '', row['name']).strip().lower().replace(' ', '-')
        if len(text) > 100:
            entry = write_source('dg_cvs', doc_id, text)
            manifest.append(entry)

    print(f'  DG CVs: {len(manifest)} documents')
    return manifest


def extract_wikipedia_articles():
    """Extract plaintext from commissioner Wikipedia articles via Wikidata sitelinks."""
    manifest = []
    # Load all commissioner Wikidata IDs
    eds = pd.read_csv('commissioner_education_by_country.csv')
    commissioner_names = eds['Name'].drop_duplicates().tolist()

    # Collect all QIDs
    cv_files = [
        'commission_santer_1995_1999_cv_data.csv',
        'commission_prodi_1999_2004_cv_data.csv',
        'commission_barroso_i_2004_2009_cv_data.csv',
        'commission_barroso_ii_2010_2014_cv_data.csv',
        'commission_juncker_cv_data.csv',
        'commission_i_cv_data.csv',
        'commission_cv_data.csv',
    ]
    qid_map = {}
    for f in cv_files:
        if not os.path.exists(f): continue
        df = pd.read_csv(f)
        for _, r in df.iterrows():
            qid_map[r['name']] = r.get('wikidata_id', '')

    print(f'  Fetching Wikipedia texts for {len(commissioner_names)} commissioners...')
    count = 0
    for name in commissioner_names:
        qid = qid_map.get(name, '')
        if not qid or str(qid) == 'nan' or pd.isna(qid):
            continue
        # Get sitelink
        try:
            edata_url = f'https://www.wikidata.org/wiki/Special:EntityData/{qid}.json'
            edata = json.loads(fetch_html(edata_url))
            title = edata['entities'].get(str(qid), {}).get('sitelinks', {}).get('enwiki', {}).get('title', '')
            if not title: continue
            # Get article extract
            api_url = 'https://en.wikipedia.org/w/api.php?' + urllib.parse.urlencode({
                'action': 'query', 'titles': title, 'prop': 'extracts',
                'explaintext': True, 'exsectionformat': 'plain', 'format': 'json'
            })
            pages = json.loads(fetch_html(api_url))['query']['pages']
            text = next(iter(pages.values())).get('extract', '')
            if len(text) > 200:
                doc_id = re.sub(r'[^a-zA-Z0-9\s\-]', '', name).strip().lower().replace(' ', '-')
                entry = write_source('wikipedia', doc_id, text)
                manifest.append(entry)
                count += 1
                if count % 10 == 0:
                    print(f'    Fetched {count}...')
        except Exception as e:
            pass

    print(f'  Wikipedia: {len(manifest)} articles')
    return manifest


def extract_cjeu_bios():
    """Extract plaintext from CJEU biography JSON."""
    manifest = []
    if not os.path.exists('cjeu_bios_full.json'):
        print('  CJEU bios JSON not found — skipping')
        return manifest

    with open('cjeu_bios_full.json') as f:
        bios = json.load(f)
    for b in bios:
        # Use bio_excerpt or construct from available fields
        text = b.get('bio_excerpt', '') or b.get('bio_text', '')
        if not text and b.get('education'):
            text = b.get('education', '')
        if not text:
            parts = [str(v) for k,v in b.items() if k not in ('name','role') and v]
            text = ' '.join(parts)
        if len(text) > 100:
            name = b.get('name', f"cjeu-{len(manifest)}")
            doc_id = re.sub(r'[^a-zA-Z0-9\s\-]', '', name).strip().lower().replace(' ', '-')
            entry = write_source('cjeu', doc_id, text)
            manifest.append(entry)

    print(f'  CJEU: {len(manifest)} bios')
    return manifest


def extract_revolving_door():
    """Extract plaintext from revolving door decisions."""
    manifest = []
    if not os.path.exists('commission_revolving_door.csv'):
        print('  Revolving door CSV not found — skipping')
        return manifest

    df = pd.read_csv('commission_revolving_door.csv')
    # Group all decisions per person into one text
    for name, grp in df.groupby('name'):
        lines = [f"{r['occupation']} ({r['commission']}, {r.get('year','')})" for _, r in grp.iterrows()]
        text = f"Post-mandate occupations for {name}:\n" + '\n'.join(lines)
        if len(text) > 50:
            doc_id = re.sub(r'[^a-zA-Z0-9\s\-]', '', name).strip().lower().replace(' ', '-')
            entry = write_source('revolving_door', doc_id, text)
            manifest.append(entry)

    print(f'  Revolving door: {len(manifest)} persons')
    return manifest


# ── Main ────────────────────────────────────────────────────────────────────

def main():
    os.makedirs(SOURCES_DIR, exist_ok=True)
    for d in ['declarations','commission_cvs','dg_cvs','wikipedia','cjeu','revolving_door','ep_hearings']:
        os.makedirs(os.path.join(SOURCES_DIR, d), exist_ok=True)

    manifest = []

    print('Extracting declarations...')
    manifest.extend(extract_declarations())

    print('Extracting DG CVs...')
    manifest.extend(extract_dg_cvs())

    print('Extracting Wikipedia articles...')
    manifest.extend(extract_wikipedia_articles())

    print('Extracting CJEU bios...')
    manifest.extend(extract_cjeu_bios())

    print('Extracting revolving door...')
    manifest.extend(extract_revolving_door())

    # Save manifest
    with open(os.path.join(SOURCES_DIR, 'manifest.json'), 'w') as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)

    total_chars = sum(m['char_count'] for m in manifest)
    total_sents = sum(m['sentence_count'] for m in manifest)
    print(f'\nDone. {len(manifest)} source documents, {total_chars:,} chars, {total_sents:,} sentences.')
    print(f'Manifest saved to {SOURCES_DIR}/manifest.json')


if __name__ == '__main__':
    main()
