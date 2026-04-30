"""Parse the machine-readable Declarations of Interests ZIP from the European Commission.

Downloads (or uses existing) Machine-Readable-DOIs.zip and extracts structured data
from each commissioner's OOXML declaration form.

Outputs:
  - commission_declarations.csv   : one row per commissioner with key fields
  - commission_affiliations.csv   : one row per affiliation/position entry (long format)
"""

import zipfile
import re
from xml.etree import ElementTree as ET
from collections import defaultdict
import pandas as pd

NS = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"

ZIP_PATH = "Machine-Readable-DOIs.zip"

# Section tags of interest mapped to short names
SECTION_FIELDS = {
    # Previous activities
    "c11": "prev_foundations_role",
    "c21": "prev_foundations_name",
    "c31": "prev_foundations_activity",
    "c12": "prev_education_role",
    "c22": "prev_education_name",
    "c13": "prev_governing_role",
    "c23": "prev_governing_name",
    "c33": "prev_governing_activity",
    "c14": "prev_other_activities",
    # Current outside activities
    "c15": "current_honorary_role",
    "c25": "current_honorary_name",
    "c35": "current_honorary_activity",
    "c16": "current_other_functions",
    # Spouse/partner financial interests
    "c1spouse": "spouse_financial",
}

SCALAR_FIELDS = {
    "DOI_FullName": "name",
    "DOI_Language": "language",
}


def get_text(el):
    return "".join(t.text or "" for t in el.iter(NS + "t")).strip()


def parse_xml(xml_bytes):
    root = ET.fromstring(xml_bytes)
    data = defaultdict(list)
    scalar = {}

    for sdt in root.iter(NS + "sdt"):
        props = sdt.find(NS + "sdtPr")
        alias = ""
        if props is not None:
            a = props.find(NS + "alias")
            tag_el = props.find(NS + "tag")
            if a is not None:
                alias = a.get(NS + "val", "")
            elif tag_el is not None:
                alias = tag_el.get(NS + "val", "")

        if not alias:
            continue

        content = sdt.find(NS + "sdtContent")
        text = get_text(content) if content is not None else ""

        if alias in SCALAR_FIELDS:
            scalar[SCALAR_FIELDS[alias]] = text
        elif alias in SECTION_FIELDS:
            if text and text not in ("NOT APPLICABLE", "YES", "NO", "N/A", ""):
                data[SECTION_FIELDS[alias]].append(text)

    return scalar, data


def build_rows(name, scalar, data):
    """Build affiliation rows (long format) for all entries."""
    rows = []
    commissioner = scalar.get("name", name)

    # Section I.1 – foundations/similar bodies (role, name, activity in sync)
    roles = data.get("prev_foundations_role", [])
    names_ = data.get("prev_foundations_name", [])
    acts = data.get("prev_foundations_activity", [])
    for i in range(max(len(roles), len(names_), len(acts))):
        rows.append(
            {
                "commissioner": commissioner,
                "section": "I.1 Previous - Foundations/similar bodies",
                "role": roles[i] if i < len(roles) else "",
                "organisation": names_[i] if i < len(names_) else "",
                "description": acts[i] if i < len(acts) else "",
            }
        )

    # Section I.2 – educational institutions
    edu_roles = data.get("prev_education_role", [])
    edu_names = data.get("prev_education_name", [])
    for i in range(max(len(edu_roles), len(edu_names))):
        rows.append(
            {
                "commissioner": commissioner,
                "section": "I.2 Previous - Educational institutions",
                "role": edu_roles[i] if i < len(edu_roles) else "",
                "organisation": edu_names[i] if i < len(edu_names) else "",
                "description": "",
            }
        )

    # Section I.3 – governing/supervisory/advisory organs
    gov_roles = data.get("prev_governing_role", [])
    gov_names = data.get("prev_governing_name", [])
    gov_acts = data.get("prev_governing_activity", [])
    for i in range(max(len(gov_roles), len(gov_names), len(gov_acts))):
        rows.append(
            {
                "commissioner": commissioner,
                "section": "I.3 Previous - Governing/supervisory/advisory",
                "role": gov_roles[i] if i < len(gov_roles) else "",
                "organisation": gov_names[i] if i < len(gov_names) else "",
                "description": gov_acts[i] if i < len(gov_acts) else "",
            }
        )

    # Section I.4 – other professional activities (free text, single column)
    for entry in data.get("prev_other_activities", []):
        rows.append(
            {
                "commissioner": commissioner,
                "section": "I.4 Previous - Other professional activities",
                "role": entry,
                "organisation": "",
                "description": "",
            }
        )

    # Section II.1 – current honorary posts
    cur_roles = data.get("current_honorary_role", [])
    cur_names = data.get("current_honorary_name", [])
    cur_acts = data.get("current_honorary_activity", [])
    for i in range(max(len(cur_roles), len(cur_names), len(cur_acts))):
        rows.append(
            {
                "commissioner": commissioner,
                "section": "II.1 Current - Honorary posts",
                "role": cur_roles[i] if i < len(cur_roles) else "",
                "organisation": cur_names[i] if i < len(cur_names) else "",
                "description": cur_acts[i] if i < len(cur_acts) else "",
            }
        )

    # Section II.2 – other current functions
    for entry in data.get("current_other_functions", []):
        rows.append(
            {
                "commissioner": commissioner,
                "section": "II.2 Current - Other functions",
                "role": entry,
                "organisation": "",
                "description": "",
            }
        )

    return rows


# ---- Main ----
all_rows = []
summary = []

with zipfile.ZipFile(ZIP_PATH) as zf:
    xml_files = [
        n for n in zf.namelist() if n.endswith(".xml") and "Test Form" not in n
    ]
    print(f"Found {len(xml_files)} declaration files\n")

    for fname in sorted(xml_files):
        # Derive commissioner name from filename
        base = fname.split("/")[-1]
        base = re.sub(r"\.xml$", "", base, flags=re.I)
        base = re.sub(r"^DOI-", "", base)
        base = re.sub(r"-(EN|FR|DE)\s*(\(\d+\))?$", "", base).strip()

        try:
            xml_bytes = zf.read(fname)
            scalar, data = parse_xml(xml_bytes)
            rows = build_rows(base, scalar, data)
            all_rows.extend(rows)

            commissioner_name = scalar.get("name", base)
            n_entries = len(rows)
            print(f"  {commissioner_name}: {n_entries} affiliation entries")
            summary.append(
                {"commissioner": commissioner_name, "total_entries": n_entries}
            )

        except Exception as e:
            print(f"  ERROR {base}: {e}")

df_aff = pd.DataFrame(
    all_rows, columns=["commissioner", "section", "role", "organisation", "description"]
)
df_aff.to_csv("commission_affiliations.csv", index=False)
print(f"\nSaved {len(df_aff)} affiliation rows to commission_affiliations.csv")

# Also produce a wide summary per commissioner
df_sum = pd.DataFrame(summary)
print(f"\n--- Summary ---")
print(df_sum.to_string(index=False))

# Quick look at the most common organisations
print("\n--- Top 20 organisations mentioned ---")
orgs = df_aff[df_aff["organisation"] != ""]["organisation"]
print(orgs.value_counts().head(20).to_string())
