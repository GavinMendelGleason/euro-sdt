"""
verify.py — AI-powered fact checker for the citation-anchored knowledge graph.

For each provenance record:
  1. Loads the source plaintext 
  2. Retrieves the quoted sentence at phrase_index
  3. Sends both the claim and the quote to DeepSeek V4 for verification
  4. Records the verdict (supported / unsupported / ambiguous)

Usage:
    export DEEPSEEK_API_KEY="your-key"
    python verify.py

Output:
    verification_report.csv — per-fact verdict with confidence scores
    updates the fact.confidence field in the DB (confirmed / disputed / ambiguous)
"""

from euro_sdt.config import DB_PATH, DEEPSEEK_API_KEY, DEEPSEEK_API_URL, MANIFEST_DIR, WIKI_DIR, WIKI_IMG_DIR, WIKIDATA_SPARQL
import sqlite3
import json
import os
import re
import time
import urllib.request
import urllib.parse
import pandas as pd
from datetime import date

DB_PATH = DB_PATH
SOURCES_DIR = 'sources'
API_KEY = DEEPSEEK_API_KEY
API_URL = DEEPSEEK_API_URL
TODAY = date.today().isoformat()

PREDICATE_CONTEXT = {
    'member_of':                'This person is a member of, serves on the board of, or has an advisory role with this organisation.',
    'educated_at':              'This person studied at or attended this university or educational institution.',
    'studied_field':            'This person has a degree or studied in this academic field.',
    'held_degree':              'This person holds this degree qualification (PhD, doctorate, etc).',
    'held_position':            'This person held this specific job title or role.',
    'held_portfolio':           'This person held this portfolio or responsibility as a European Commissioner.',
    'served_on_commission':     'This person served on this European Commission.',
    'from_country':             'This person is from this country.',
    'nominated_by':             'This person was nominated by this country.',
    'post_mandate_occupation':  'This person took up this occupation after leaving their commissioner post.',
    'classified_as':            'This organisation is classified as having this characteristic.',
    'funding_notes':            'This describes the funding sources for this organisation.',
}


def call_deepseek(prompt, max_tokens=200, timeout=30):
    """Call DeepSeek V4 API with a prompt and return the response text."""
    if not API_KEY:
        return None

    payload = json.dumps({
        'model': 'deepseek-v4-pro',
        'messages': [{'role': 'user', 'content': prompt}],
        'max_tokens': max_tokens,
        'temperature': 0.0, 'thinking': {'type': 'disabled'},  # deterministic for fact verification
    }).encode()

    req = urllib.request.Request(
        API_URL, data=payload,
        headers={
            'Authorization': f'Bearer {API_KEY}',
            'Content-Type': 'application/json',
            'User-Agent': 'euro-sdt-verifier/1.0'
        }
    )
    try:
        resp = urllib.request.urlopen(req, timeout=timeout)
        data = json.loads(resp.read())
        return data['choices'][0]['message']['content'].strip()
    except Exception as e:
        return f'ERROR: {e}'


def build_verification_prompt(fact, provenance, entity_name, obj_display, org_display):
    """Build a prompt for the AI to verify a fact against its source quote."""
    predicate = fact[2]
    qualifier = fact[5] or ''
    phrase_idx= provenance[4]
    
    # For batch-cited facts (phrase_index=0 or -1), verify differently
    if phrase_idx <= 0:
        source_name = provenance[2]  # citation_id
        context = provenance[5] or ''  # context_text is element 5
        return f"""You are a fact-checker. Verify whether a claimed fact is supported by its source context.

CLAIM: {entity_name} — {predicate}: {obj_display}
MEANING: {PREDICATE_CONTEXT.get(predicate, '')}

SOURCE CONTEXT (excerpt from the cited document):
  {context[:800]}

TASK: Compare the claim against the source context. Is the claim supported?
Check carefully for misclassifications — e.g., is the organisation in the claim
the SAME as the one mentioned in the context? Reply with:
  SUPPORTED — the context confirms the claim
  UNSUPPORTED — the context contradicts or does not match the claim
  AMBIGUOUS — unclear

VERDICT: <SUPPORTED|UNSUPPORTED|AMBIGUOUS>
REASON: <one sentence>"""

    context = PREDICATE_CONTEXT.get(predicate, '')
    quote = provenance[3]

    return f"""You are a fact-checking assistant. Your job is to determine whether a source quote supports a claimed fact.

CLAIM:
  Entity: {entity_name}
  Predicate: {predicate}
  Claimed object: {obj_display}
  Qualifier: {qualifier}
  Meaning: {context}

SOURCE QUOTE (from phrase index {phrase_idx}):
  "{quote}"

TASK: Does the source quote support the claim? Reply with exactly ONE of:
  SUPPORTED - the quote clearly confirms the claim
  UNSUPPORTED - the quote contradicts or does not match the claim
  AMBIGUOUS - the quote is about the right entity but the specific claim cannot be clearly verified

Reply in this exact format:
VERDICT: <SUPPORTED|UNSUPPORTED|AMBIGUOUS>
REASON: <one sentence explaining why>"""


def read_source_phrase(subdir, doc_id, phrase_idx):
    """Read a specific phrase from a source document."""
    ppath = os.path.join(SOURCES_DIR, subdir, f'{doc_id}.phrases')
    if not os.path.exists(ppath):
        return None
    with open(ppath) as f:
        for i, line in enumerate(f):
            if i == phrase_idx:
                parts = line.strip().split('\t')
                if len(parts) >= 3:
                    return parts[2]
    return None


def verify_all(db, limit=None, dry_run=False):
    """Run verification on all provenance records."""
    query = """
        SELECT p.id, p.fact_id, p.citation_id, p.quote_text, p.phrase_index,
               p.context_text,
               f.id as fid, f.entity_id, f.predicate, f.object, f.object_type,
               f.qualifier, f.confidence,
               e.name as entity_name,
               CASE WHEN f.object_type = 'entity_id'
                    THEN (SELECT name FROM entity WHERE id = f.object)
                    ELSE f.object END as obj_display,
               c.source_name
        FROM provenance p
        JOIN fact f ON p.fact_id = f.id
        JOIN entity e ON e.id = f.entity_id
        JOIN citation c ON p.citation_id = c.id
            WHERE p.phrase_index > 0
            AND (f.verified_at IS NULL OR f.confidence = 'disputed')
        ORDER BY f.predicate, e.name
    """
    if limit:
        query += f' LIMIT {limit}'

    rows = db.execute(query).fetchall()
    total = len(rows)
    results = []
    supported = unsupported = ambiguous = errored = 0

    for i, row in enumerate(rows):
        (prov_id, fact_id, cit_id, quote, phrase_idx, context_txt,
         fid, entity_id, predicate, obj, obj_type, qualifier, confidence,
         entity_name, obj_display, source_name) = row

        if dry_run:
            print(f'  [{i+1}/{total}] {entity_name} → {obj_display} [{predicate}]')
            continue

        # Get full context from the source
        full_quote = quote
        if phrase_idx > 0 and cit_id.startswith('cit-dg-cvs'):
            # Try to get the exact phrase from the source
            for subdir in ['dg_cvs', 'declarations', 'wikipedia']:
                # Extract doc_id from provenance id
                doc_match = re.search(r'prov-[^-]+-(.*)', prov_id)
                if doc_match:
                    doc = doc_match.group(1)
                    exact = read_source_phrase(subdir, doc, phrase_idx)
                    if exact:
                        full_quote = exact
                        break

        prompt = build_verification_prompt(
            row, (prov_id, fact_id, cit_id, full_quote, phrase_idx, context_txt),
            entity_name, obj_display, obj_display)

        if not API_KEY:
            verdict = 'NO_API_KEY'
            reason = 'No DEEPSEEK_API_KEY set'
        else:
            response = call_deepseek(prompt)
            if response and 'ERROR' not in str(response):
                # Parse response
                v_match = re.search(r'VERDICT:\s*(SUPPORTED|UNSUPPORTED|AMBIGUOUS|TRACEABLE|UNTRACEABLE)', response, re.I)
                r_match = re.search(r'REASON:\s*(.+?)$', response, re.I|re.MULTILINE)
                verdict = v_match.group(1).upper() if v_match else 'PARSE_ERROR'
                reason  = r_match.group(1).strip() if r_match else response[:200]

                # Normalise: TRACEABLE → SUPPORTED, UNTRACEABLE → UNSUPPORTED (legacy)
                if verdict == 'TRACEABLE': verdict = 'SUPPORTED'
                if verdict == 'UNTRACEABLE': verdict = 'UNSUPPORTED'
            else:
                verdict = 'API_ERROR'
                reason = str(response)

        if verdict == 'SUPPORTED':    supported += 1
        elif verdict == 'UNSUPPORTED': unsupported += 1
        elif verdict == 'AMBIGUOUS':   ambiguous += 1
        else:                          errored += 1

        results.append({
            'prov_id':      prov_id,
            'fact_id':      fact_id,
            'entity':       entity_name,
            'predicate':    predicate,
            'claimed_object': obj_display,
            'quote':        full_quote[:200],
            'phrase_index': phrase_idx,
            'verdict':      verdict,
            'reason':       reason,
            'source':       source_name,
        })

        # Update confidence in DB
        confidence_map = {
            'SUPPORTED': 'confirmed', 'UNSUPPORTED': 'disputed',
            'AMBIGUOUS': 'ambiguous'
        }
        new_conf = confidence_map.get(verdict, confidence)
        db.execute("UPDATE fact SET confidence = ?, updated_at = ?, verified_at = ? WHERE id = ?",
                   (new_conf, TODAY, TODAY, fact_id))

        if i % 10 == 0 or i == total - 1:
            print(f'  [{i+1}/{total}] S:{supported} U:{unsupported} A:{ambiguous} E:{errored}')
            # Incremental write so status.py can monitor
            if results:
                pd.DataFrame(results).to_csv('verification_report.csv', index=False)

        time.sleep(0.5)  # rate limit

    db.commit()
    print(f'\nVerification complete: {supported} supported, {unsupported} unsupported, '
          f'{ambiguous} ambiguous, {errored} errors')

    return results


def main():
    if not API_KEY:
        print("WARNING: No DEEPSEEK_API_KEY set. Set it to run actual verification.")
        print("Running in dry-run mode to show what would be checked.\n")

    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row

    if not API_KEY:
        verify_all(db, limit=20, dry_run=True)
    else:
        results = verify_all(db)
        df = pd.DataFrame(results)
        df.to_csv('verification_report.csv', index=False)
        print(f'\nSaved verification_report.csv ({len(df)} facts checked)')

    db.close()


if __name__ == '__main__':
    main()
