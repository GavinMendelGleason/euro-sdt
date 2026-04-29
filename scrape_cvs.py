"""Scrape CV/biographical data for current MEPs from Wikidata.

Fetches: education, occupations, employers, previous positions, awards, party history,
birth date/place for all current MEPs (start date >= 2024).
"""
import urllib.request
import urllib.parse
import json
import time
import pandas as pd
from collections import defaultdict

SPARQL_ENDPOINT = "https://query.wikidata.org/sparql"

def run_query(query, timeout=180):
    url = SPARQL_ENDPOINT + "?" + urllib.parse.urlencode({"query": query, "format": "json"})
    req = urllib.request.Request(url, headers={
        'User-Agent': 'euro-sdt-research/1.0 (mailto:research@example.com)',
        'Accept': 'application/json'
    })
    resp = urllib.request.urlopen(req, timeout=timeout)
    return json.loads(resp.read())

def fetch_current_meps(offset=0):
    """Get current MEP Wikidata IDs."""
    query = f"""
    SELECT DISTINCT ?mep ?mepLabel ?startDate WHERE {{
      ?mep p:P39 ?stmt .
      ?stmt ps:P39 wd:Q27169 .
      ?stmt pq:P580 ?startDate .
      FILTER(YEAR(?startDate) >= 2024)
      SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en" }}
    }}
    ORDER BY ?mepLabel
    OFFSET {offset}
    """
    return run_query(query)

def fetch_cv_fields(mep_ids, field_prop, label="items"):
    """Fetch a specific CV field for a batch of MEPs.
    
    Args:
        mep_ids: list of Wikidata IDs (just the Qxxxx part)
        field_prop: Wikidata property P-number for the field (e.g., 'P69' for education)
    """
    values = " ".join(f"wd:{mid}" for mid in mep_ids)
    query = f"""
    SELECT ?mep ?mepLabel ?itemLabel WHERE {{
      VALUES ?mep {{ {values} }}
      OPTIONAL {{ ?mep wdt:{field_prop} ?item }}
      SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en" }}
    }}
    """
    return run_query(query)

def fetch_birthplace(mep_ids):
    """Fetch birth place for MEPs."""
    values = " ".join(f"wd:{mid}" for mid in mep_ids)
    query = f"""
    SELECT ?mep ?mepLabel ?birthDate ?birthPlaceLabel WHERE {{
      VALUES ?mep {{ {values} }}
      OPTIONAL {{ ?mep wdt:P569 ?birthDate }}
      OPTIONAL {{ ?mep wdt:P19 ?birthPlace }}
      SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en" }}
    }}
    """
    return run_query(query)

def fetch_previous_positions(mep_ids):
    """Fetch previous positions for MEPs."""
    values = " ".join(f"wd:{mid}" for mid in mep_ids)
    query = f"""
    SELECT ?mep ?mepLabel ?positionLabel ?startDate ?endDate WHERE {{
      VALUES ?mep {{ {values} }}
      ?mep p:P39 ?stmt .
      ?stmt ps:P39 ?position .
      MINUS {{ ?stmt ps:P39 wd:Q27169 }}
      OPTIONAL {{ ?stmt pq:P580 ?startDate }}
      OPTIONAL {{ ?stmt pq:P582 ?endDate }}
      SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en" }}
    }}
    """
    return run_query(query)

# ---- Main ----
print("Step 1: Fetching current MEP IDs...")
all_meps = []
offset = 0

while True:
    data = fetch_current_meps(offset)
    bindings = data['results']['bindings']
    if not bindings:
        break
    for b in bindings:
        mid = b.get('mep', {}).get('value', '').split('/')[-1]
        if mid:
            all_meps.append({
                'wikidata_id': mid,
                'name': b.get('mepLabel', {}).get('value', ''),
                'term_start': b.get('startDate', {}).get('value', '')[:10] if 'startDate' in b else '',
            })
    print(f"  Got {len(bindings)} (total: {len(all_meps)})")
    if len(bindings) < 600:
        break
    offset += 600
    time.sleep(0.3)

# Deduplicate by ID
seen = set()
unique_meps = []
for m in all_meps:
    if m['wikidata_id'] not in seen:
        seen.add(m['wikidata_id'])
        unique_meps.append(m)

print(f"  {len(unique_meps)} unique MEPs")

# Build field -> MEP mapping
mep_data = {m['wikidata_id']: m for m in unique_meps}
mep_ids = list(mep_data.keys())

# Step 2: Fetch CV fields in batches
batch_size = 200
fields = {
    'P69': 'education',       # educated at
    'P106': 'occupations',    # occupation
    'P108': 'employers',      # employer
    'P102': 'party_history',  # political party
    'P166': 'awards',         # award received
}

print("\nStep 2: Fetching CV fields...")
for prop, field_name in fields.items():
    print(f"  Fetching {field_name} ({prop})...")
    for i in range(0, len(mep_ids), batch_size):
        batch = mep_ids[i:i+batch_size]
        try:
            data = fetch_cv_fields(batch, prop)
            for b in data['results']['bindings']:
                mid = b.get('mep', {}).get('value', '').split('/')[-1]
                item = b.get('itemLabel', {}).get('value', '')
                if mid in mep_data and item:
                    if field_name not in mep_data[mid]:
                        mep_data[mid][field_name] = []
                    mep_data[mid][field_name].append(item)
        except Exception as e:
            print(f"    Error batch {i}: {e}")
        if i + batch_size < len(mep_ids):
            time.sleep(0.3)

# Step 3: Fetch birth data
print("\nStep 3: Fetching birth data...")
for i in range(0, len(mep_ids), batch_size):
    batch = mep_ids[i:i+batch_size]
    try:
        data = fetch_birthplace(batch)
        for b in data['results']['bindings']:
            mid = b.get('mep', {}).get('value', '').split('/')[-1]
            if mid in mep_data:
                bdate = b.get('birthDate', {}).get('value', '')
                mep_data[mid]['birth_date'] = bdate[:10] if bdate else ''
                mep_data[mid]['birth_place'] = b.get('birthPlaceLabel', {}).get('value', '')
    except Exception as e:
        print(f"    Error batch {i}: {e}")
    if i + batch_size < len(mep_ids):
        time.sleep(0.3)

# Step 4: Fetch previous positions
print("\nStep 4: Fetching previous positions...")
for i in range(0, len(mep_ids), batch_size):
    batch = mep_ids[i:i+batch_size]
    try:
        data = fetch_previous_positions(batch)
        for b in data['results']['bindings']:
            mid = b.get('mep', {}).get('value', '').split('/')[-1]
            pos = b.get('positionLabel', {}).get('value', '')
            start = b.get('startDate', {}).get('value', '')[:10] if 'startDate' in b else ''
            end = b.get('endDate', {}).get('value', '')[:10] if 'endDate' in b else ''
            if mid in mep_data and pos:
                if 'prev_positions' not in mep_data[mid]:
                    mep_data[mid]['prev_positions'] = []
                entry = f"{pos}"
                if start and end:
                    entry += f" ({start} to {end})"
                elif start:
                    entry += f" (from {start})"
                mep_data[mid]['prev_positions'].append(entry)
    except Exception as e:
        print(f"    Error batch {i}: {e}")
    if i + batch_size < len(mep_ids):
        time.sleep(0.3)

# Build final DataFrame
rows = []
for mid, data in mep_data.items():
    row = {
        'wikidata_id': mid,
        'name': data.get('name', ''),
        'term_start': data.get('term_start', ''),
        'birth_date': data.get('birth_date', ''),
        'birth_place': data.get('birth_place', ''),
    }
    for field in ['education', 'occupations', 'employers', 'party_history', 'awards', 'prev_positions']:
        vals = data.get(field, [])
        row[field] = ' || '.join(vals) if vals else ''
    rows.append(row)

df_cv = pd.DataFrame(rows)
print(f"\nFinal CVs: {len(df_cv)} MEPs")

# Match with existing MEP list
df_meps = pd.read_csv('meps_2024_2029.csv')
df_meps['Name_upper'] = df_meps['Name'].str.upper()
df_cv['name_upper'] = df_cv['name'].str.upper()

df_merged = df_meps.merge(df_cv, left_on='Name_upper', right_on='name_upper', how='left', suffixes=('', '_wd'))
df_merged = df_merged.drop(columns=['Name_upper', 'name_upper'])
matched = df_merged['wikidata_id'].notna().sum()
print(f"Matched {matched} / {len(df_merged)} MEPs in our list")

# Keep only the matched, enriched MEPs
df_merged.to_csv('meps_2024_2029.csv', index=False)
print("Saved enriched meps_2024_2029.csv")

# Also save standalone CV data
df_cv.to_csv('mep_cv_data.csv', index=False)
print("Saved mep_cv_data.csv")

# Summary
print("\n--- CV Data Summary ---")
for field in ['education', 'occupations', 'employers', 'party_history', 'awards', 'prev_positions', 'birth_date', 'birth_place']:
    if field in df_cv.columns:
        vals = df_cv[field].fillna('')
        non_empty = (vals != '').sum()
        print(f"  {field}: {non_empty}/{len(df_cv)} populated")

# Show some example CVs
print("\n--- Sample CVs ---")
for _, row in df_cv.head(5).iterrows():
    print(f"\n  {row['name']}")
    if row.get('birth_date'): print(f"    Born: {row['birth_date']}, {row.get('birth_place','')}")
    if row.get('education'): print(f"    Education: {row['education'][:200]}")
    if row.get('occupations'): print(f"    Occupations: {row['occupations'][:200]}")
    if row.get('party_history'): print(f"    Parties: {row['party_history'][:200]}")
    if row.get('prev_positions'): print(f"    Previous roles: {row['prev_positions'][:300]}")
