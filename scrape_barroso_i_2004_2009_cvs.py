"""Scrape CV/biographical data for current EU Commissioners from Wikidata.

Fetches: education, occupations, employers, previous positions, awards, party history,
birth date/place for all current EU Commissioners (Von der Leyen Commission II).

Requires commission_barroso_i_2004_2009.csv to exist (run scrape_commission.py first).
Outputs: commission_barroso_i_2004_2009_cv_data.csv  and enriches commission_barroso_i_2004_2009.csv
"""
import urllib.request
import urllib.parse
import json
import time
import pandas as pd

SPARQL_ENDPOINT = "https://query.wikidata.org/sparql"

def run_query(query, timeout=60):
    url = SPARQL_ENDPOINT + "?" + urllib.parse.urlencode({"query": query, "format": "json"})
    req = urllib.request.Request(url, headers={
        'User-Agent': 'euro-sdt-research/1.0 (mailto:research@example.com)',
        'Accept': 'application/json'
    })
    resp = urllib.request.urlopen(req, timeout=timeout)
    return json.loads(resp.read())

def lookup_qid_by_name(name):
    """Find a person's Wikidata QID by their English label."""
    query = f"""
    SELECT ?person WHERE {{
      ?person wdt:P31 wd:Q5 .
      ?person rdfs:label "{name}"@en .
    }}
    LIMIT 3
    """
    try:
        data = run_query(query, timeout=20)
        bindings = data['results']['bindings']
        if bindings:
            return bindings[0]['person']['value'].split('/')[-1]
    except Exception as e:
        print(f"    Lookup error for {name}: {e}")
    return None

def fetch_cv_fields(person_ids, field_prop):
    """Fetch a specific CV field for a batch of people."""
    values = " ".join(f"wd:{pid}" for pid in person_ids)
    query = f"""
    SELECT ?person ?personLabel ?itemLabel WHERE {{
      VALUES ?person {{ {values} }}
      OPTIONAL {{ ?person wdt:{field_prop} ?item }}
      SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en" }}
    }}
    """
    return run_query(query)


def fetch_birthplace(person_ids):
    """Fetch birth date and birth place."""
    values = " ".join(f"wd:{pid}" for pid in person_ids)
    query = f"""
    SELECT ?person ?personLabel ?birthDate ?birthPlaceLabel WHERE {{
      VALUES ?person {{ {values} }}
      OPTIONAL {{ ?person wdt:P569 ?birthDate }}
      OPTIONAL {{ ?person wdt:P19 ?birthPlace }}
      SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en" }}
    }}
    """
    return run_query(query)


def fetch_previous_positions(person_ids):
    """Fetch all positions held, excluding the current commissioner role."""
    values = " ".join(f"wd:{pid}" for pid in person_ids)
    query = f"""
    SELECT ?person ?personLabel ?positionLabel ?startDate ?endDate WHERE {{
      VALUES ?person {{ {values} }}
      ?person p:P39 ?stmt .
      ?stmt ps:P39 ?position .
      # Exclude current EU Commissioner/President roles (start >= 2024 handled below)
      OPTIONAL {{ ?stmt pq:P580 ?startDate }}
      OPTIONAL {{ ?stmt pq:P582 ?endDate }}
      # Only include positions that have ended or started before 2024
      FILTER(!BOUND(?startDate) || YEAR(?startDate) < 2024 || BOUND(?endDate))
      SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en" }}
    }}
    """
    return run_query(query)


# ---- Main ----
print("Step 1: Loading commissioners from CSV and looking up Wikidata IDs...")
df_commission = pd.read_csv('commission_barroso_i_2004_2009.csv')
names = df_commission['Name'].tolist()

person_data = {}
for name in names:
    qid = lookup_qid_by_name(name)
    if qid:
        person_data[qid] = {'wikidata_id': qid, 'name': name}
        print(f"  Found {name} -> {qid}")
    else:
        print(f"  NOT FOUND: {name}")
    time.sleep(0.2)

print(f"  {len(person_data)} / {len(names)} commissioners matched on Wikidata")
person_ids = list(person_data.keys())

# Step 2: Fetch CV fields
batch_size = 50  # smaller batches — fewer commissioners than MEPs
fields = {
    "P69": "education",  # educated at
    "P106": "occupations",  # occupation
    "P108": "employers",  # employer
    "P102": "party_history",  # political party
    "P166": "awards",  # award received
}

print("\nStep 2: Fetching CV fields...")
for prop, field_name in fields.items():
    print(f"  Fetching {field_name} ({prop})...")
    for i in range(0, len(person_ids), batch_size):
        batch = person_ids[i : i + batch_size]
        try:
            data = fetch_cv_fields(batch, prop)
            for b in data["results"]["bindings"]:
                pid = b.get("person", {}).get("value", "").split("/")[-1]
                item = b.get("itemLabel", {}).get("value", "")
                if pid in person_data and item:
                    if field_name not in person_data[pid]:
                        person_data[pid][field_name] = []
                    person_data[pid][field_name].append(item)
        except Exception as e:
            print(f"    Error batch {i}: {e}")
        if i + batch_size < len(person_ids):
            time.sleep(0.3)

# Step 3: Fetch birth data
print("\nStep 3: Fetching birth data...")
for i in range(0, len(person_ids), batch_size):
    batch = person_ids[i : i + batch_size]
    try:
        data = fetch_birthplace(batch)
        for b in data["results"]["bindings"]:
            pid = b.get("person", {}).get("value", "").split("/")[-1]
            if pid in person_data:
                bdate = b.get("birthDate", {}).get("value", "")
                person_data[pid]["birth_date"] = bdate[:10] if bdate else ""
                person_data[pid]["birth_place"] = b.get("birthPlaceLabel", {}).get(
                    "value", ""
                )
    except Exception as e:
        print(f"    Error batch {i}: {e}")
    if i + batch_size < len(person_ids):
        time.sleep(0.3)

# Step 4: Fetch previous positions
print("\nStep 4: Fetching previous positions...")
for i in range(0, len(person_ids), batch_size):
    batch = person_ids[i : i + batch_size]
    try:
        data = fetch_previous_positions(batch)
        for b in data["results"]["bindings"]:
            pid = b.get("person", {}).get("value", "").split("/")[-1]
            pos = b.get("positionLabel", {}).get("value", "")
            start = (
                b.get("startDate", {}).get("value", "")[:10] if "startDate" in b else ""
            )
            end = b.get("endDate", {}).get("value", "")[:10] if "endDate" in b else ""
            if pid in person_data and pos:
                if "prev_positions" not in person_data[pid]:
                    person_data[pid]["prev_positions"] = []
                entry = pos
                if start and end:
                    entry += f" ({start} to {end})"
                elif start:
                    entry += f" (from {start})"
                person_data[pid]["prev_positions"].append(entry)
    except Exception as e:
        print(f"    Error batch {i}: {e}")
    if i + batch_size < len(person_ids):
        time.sleep(0.3)

# Build final DataFrame
rows = []
for pid, data in person_data.items():
    row = {
        "wikidata_id": pid,
        "name": data.get("name", ""),
        "term_start": data.get("term_start", ""),
        "wikidata_position": data.get("wikidata_position", ""),
        "birth_date": data.get("birth_date", ""),
        "birth_place": data.get("birth_place", ""),
    }
    for field in [
        "education",
        "occupations",
        "employers",
        "party_history",
        "awards",
        "prev_positions",
    ]:
        vals = data.get(field, [])
        row[field] = (
            " || ".join(dict.fromkeys(vals)) if vals else ""
        )  # deduplicate order-preserving
    rows.append(row)

df_cv = pd.DataFrame(rows)
print(f"\nFinal CVs: {len(df_cv)} commissioners")

# Save standalone CV data
df_cv.to_csv("commission_barroso_i_2004_2009_cv_data.csv", index=False)
print("Saved commission_barroso_i_2004_2009_cv_data.csv")

# Merge with commission list if it exists
try:
    df_commission = pd.read_csv("commission_barroso_i_2004_2009.csv")
    df_commission["Name_upper"] = df_commission["Name"].str.upper()
    df_cv["name_upper"] = df_cv["name"].str.upper()

    df_merged = df_commission.merge(
        df_cv,
        left_on="Name_upper",
        right_on="name_upper",
        how="left",
        suffixes=("", "_wd"),
    )
    df_merged = df_merged.drop(columns=["Name_upper", "name_upper"])
    matched = df_merged["wikidata_id"].notna().sum()
    print(
        f"Matched {matched} / {len(df_merged)} commissioners from commission_barroso_i_2004_2009.csv"
    )

    df_merged.to_csv("commission_barroso_i_2004_2009.csv", index=False)
    print("Saved enriched commission_barroso_i_2004_2009.csv")
except FileNotFoundError:
    print("commission_barroso_i_2004_2009.csv not found — run scrape_commission.py first.")

# Summary
print("\n--- CV Data Summary ---")
for field in [
    "education",
    "occupations",
    "employers",
    "party_history",
    "awards",
    "prev_positions",
    "birth_date",
    "birth_place",
]:
    if field in df_cv.columns:
        non_empty = (df_cv[field].fillna("") != "").sum()
        print(f"  {field}: {non_empty}/{len(df_cv)} populated")

# Sample output
print("\n--- Sample Commissioner CVs ---")
for _, row in df_cv.head(5).iterrows():
    print(f"\n  {row['name']} ({row.get('wikidata_position', '')})")
    if row.get("birth_date"):
        print(f"    Born: {row['birth_date']}, {row.get('birth_place', '')}")
    if row.get("education"):
        print(f"    Education: {row['education'][:200]}")
    if row.get("occupations"):
        print(f"    Occupations: {row['occupations'][:200]}")
    if row.get("party_history"):
        print(f"    Parties: {row['party_history'][:200]}")
    if row.get("prev_positions"):
        print(f"    Previous roles: {row['prev_positions'][:300]}")
