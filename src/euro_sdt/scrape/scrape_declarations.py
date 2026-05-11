"""Scrape MEP Declarations of Private Interests (DPI) PDFs from the European Parliament.

Extracts Sections A (past occupations/memberships) and C (current board memberships)
for all current MEPs. Saves PDFs to declarations/ and extracted data to CSV.
"""
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
import re
import os
import time
import hashlib
import pandas as pd
from PyPDF2 import PdfReader

DECL_DIR = 'declarations'
os.makedirs(DECL_DIR, exist_ok=True)

def ep_name_to_url(name):
    """Convert an MEP name to the URL-safe slug used by the EP website."""
    # URL-encode each word, preserve underscores between words
    parts = name.split()
    encoded_parts = [urllib.parse.quote(p) for p in parts]
    return '_'.join(encoded_parts)

def extract_sections(text):
    """Extract sections A and C from the declaration text."""
    section_a = ''
    section_c = ''

    a_match = re.search(r'\(A\)\s"[^"]*"(.*?)(?=\(B\)|$)', text, re.DOTALL | re.IGNORECASE)
    c_match = re.search(r'\(C\)\s"[^"]*"(.*?)(?=\(D\)|$)', text, re.DOTALL | re.IGNORECASE)

    if a_match:
        section_a = a_match.group(1).strip()
    if c_match:
        section_c = c_match.group(1).strip()

    # Extract individual items (numbered lines)
    def parse_items(section_text):
        items = []
        lines = section_text.split('\n')
        current_item = None
        for line in lines:
            line = line.strip()
            if not line:
                continue
            m = re.match(r'^(\d+)\.\s*(.*)', line)
            if m:
                if current_item:
                    items.append(current_item)
                current_item = (m.group(1), m.group(2).strip())
            elif current_item:
                current_item = (current_item[0], current_item[1] + ' ' + line)
        if current_item:
            items.append(current_item)
        return items

    return {
        'a_items': parse_items(section_a),
        'c_items': parse_items(section_c),
        'a_raw': section_a,
        'c_raw': section_c,
    }

# Get MEP IDs from EP XML
print("Fetching MEP IDs from European Parliament...")
xml_url = 'https://www.europarl.europa.eu/meps/en/full-list/xml'
req = urllib.request.Request(xml_url, headers={'User-Agent': 'Mozilla/5.0'})
root = ET.fromstring(urllib.request.urlopen(req).read())

meps = []
for m in root.findall('.//mep'):
    meps.append({
        'ep_id': m.find('id').text,
        'name': m.find('fullName').text,
        'country': m.find('country').text,
        'group': m.find('politicalGroup').text,
    })

print(f"Found {len(meps)} MEPs")

results = []
errors = []
success = 0
no_pdf = 0
pdf_fail = 0
parse_fail = 0

for i, mep in enumerate(meps):
    mid = mep['ep_id']
    name = mep['name']
    
    if (i + 1) % 50 == 0:
        print(f"  Progress: {i+1}/{len(meps)} (success: {success}, no PDF: {no_pdf}, fails: {pdf_fail}+{parse_fail})")

    # Step 1: Fetch declarations page
    url_name = ep_name_to_url(name)
    decl_url = f"https://www.europarl.europa.eu/meps/en/{mid}/{url_name}/declarations"
    
    try:
        req = urllib.request.Request(decl_url, headers={'User-Agent': 'Mozilla/5.0'})
        html = urllib.request.urlopen(req, timeout=15).read().decode('utf-8')
    except Exception as e:
        errors.append({'name': name, 'stage': 'decl_page', 'error': str(e)})
        continue

    # Step 2: Find DPI PDF link
    pdf_links = re.findall(r'https?://[^"]*DPI[^"]*\.pdf', html)
    if not pdf_links:
        no_pdf += 1
        continue
    pdf_url = pdf_links[0]

    # Step 3: Download PDF (cache by hash)
    pdf_hash = hashlib.md5(pdf_url.encode()).hexdigest()
    pdf_path = os.path.join(DECL_DIR, f'{mid}_{name.replace(" ", "_").replace("/", "-")[:60]}.pdf')
    
    if not os.path.exists(pdf_path):
        try:
            req = urllib.request.Request(pdf_url, headers={'User-Agent': 'Mozilla/5.0'})
            with open(pdf_path, 'wb') as f:
                f.write(urllib.request.urlopen(req, timeout=30).read())
        except Exception as e:
            pdf_fail += 1
            errors.append({'name': name, 'stage': 'pdf_download', 'error': str(e)})
            continue

    # Step 4: Parse PDF
    try:
        reader = PdfReader(pdf_path)
        text = ''
        for page in reader.pages:
            t = page.extract_text()
            if t:
                text += t
    except Exception as e:
        parse_fail += 1
        errors.append({'name': name, 'stage': 'pdf_parse', 'error': str(e)})
        continue

    if not text.strip():
        parse_fail += 1
        continue

    # Step 5: Extract sections A and C
    sections = extract_sections(text)
    
    # Flatten items for CSV
    a_items_str = ' || '.join([f"{num}. {txt}" for num, txt in sections['a_items']])
    c_items_str = ' || '.join([f"{num}. {txt}" for num, txt in sections['c_items']])
    
    results.append({
        'ep_id': mid,
        'name': name,
        'country': mep['country'],
        'group': mep['group'],
        'section_a_items': a_items_str,
        'section_c_items': c_items_str,
        'section_a_count': len(sections['a_items']),
        'section_c_count': len(sections['c_items']),
        'pdf_path': pdf_path,
    })
    
    success += 1
    
    # Rate limiting
    if (i + 1) % 5 == 0:
        time.sleep(0.3)

print(f"\nDone! Success: {success}, No PDF: {no_pdf}, PDF fails: {pdf_fail}, Parse fails: {parse_fail}")

# Save results
df = pd.DataFrame(results)
df.to_csv('mep_declarations.csv', index=False)
print(f"Saved {len(df)} MEP declarations to mep_declarations.csv")

if errors:
    df_err = pd.DataFrame(errors)
    df_err.to_csv('declaration_errors.csv', index=False)
    print(f"Saved {len(errors)} errors to declaration_errors.csv")

print(f"\nDeclarations with items:")
print(f"  Section A (past): {df['section_a_count'].gt(0).sum()} MEPs")
print(f"  Section C (current): {df['section_c_count'].gt(0).sum()} MEPs")
print(f"  PDFs saved to: {DECL_DIR}/")
