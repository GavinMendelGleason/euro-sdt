"""Scrape the Von der Leyen Commission II (2024-2029) from Wikipedia.

Source: https://en.wikipedia.org/wiki/Von_der_Leyen_Commission_II
Outputs: commission_2024_2029.csv

Table 0 on the page has columns: Portfolio | Portrait | Name | EU Party(N.Party) | Member state | Directorate General
"""

import urllib.request
import re
import pandas as pd
from bs4 import BeautifulSoup, Comment

url = "https://en.wikipedia.org/wiki/Von_der_Leyen_Commission_II"
req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
html = urllib.request.urlopen(req).read().decode("utf-8")
soup = BeautifulSoup(html, "lxml")

for comment in soup.find_all(string=lambda t: isinstance(t, Comment)):
    comment.extract()


def clean(text):
    text = re.sub(r"\[.*?\]", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


tables = soup.find_all("table", class_="wikitable")

# Target the first table: Portfolio | Portrait | Name | EU Party(N.Party) | Member state | DG
target_table = tables[0]

rows = target_table.find_all("tr")
commissioners = []

for row in rows[1:]:  # skip header row
    cells = row.find_all(["td", "th"])
    if len(cells) < 4:
        continue

    # Col 0: Portfolio, Col 1: Portrait (image — skip), Col 2: Name, Col 3: EU Party(N.Party), Col 4: Member state
    portfolio = clean(cells[0].get_text())
    name = clean(cells[2].get_text())
    party_raw = clean(cells[3].get_text())  # e.g. "EPP(CDU)" or "PES(PSOE)"
    country = clean(cells[4].get_text()) if len(cells) > 4 else ""
    dg = clean(cells[5].get_text()) if len(cells) > 5 else ""

    # Split EU group and national party: "EPP(CDU)" -> ep_group=EPP, nat_party=CDU
    m = re.match(r"^(.*?)\((.+)\)$", party_raw)
    if m:
        ep_group = m.group(1).strip()
        nat_party = m.group(2).strip()
    else:
        ep_group = party_raw
        nat_party = ""

    if not name or len(name) < 3:
        continue

    commissioners.append([name, portfolio, country, nat_party, ep_group, dg])

df = pd.DataFrame(
    commissioners,
    columns=[
        "Name",
        "Portfolio",
        "Country",
        "National_Party",
        "EP_Group",
        "Directorate_General",
    ],
)

print(f"Found {len(df)} commissioners\n")
print(df[["Name", "Portfolio", "Country", "EP_Group"]].to_string(index=False))

df.to_csv("commission_2024_2029.csv", index=False)
print("\nSaved to commission_2024_2029.csv")
