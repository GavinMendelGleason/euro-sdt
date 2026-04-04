import urllib.request
import pandas as pd
from bs4 import BeautifulSoup, Comment
import re

url = "https://en.wikipedia.org/wiki/List_of_members_of_the_European_Parliament_(2024%E2%80%932029)"
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
html = urllib.request.urlopen(req).read().decode('utf-8')
soup = BeautifulSoup(html, 'lxml')

for comment in soup.find_all(string=lambda t: isinstance(t, Comment)):
    comment.extract()

countries = ['Austria', 'Belgium', 'Bulgaria', 'Croatia', 'Cyprus', 'Czech Republic',
            'Denmark', 'Estonia', 'Finland', 'France', 'Germany', 'Greece', 'Hungary',
            'Ireland', 'Italy', 'Latvia', 'Lithuania', 'Luxembourg', 'Malta',
            'Netherlands', 'Poland', 'Portugal', 'Romania', 'Slovakia', 'Slovenia',
            'Spain', 'Sweden']

sections = soup.find_all(['h2', 'h3', 'table'])

country_data = []
for i, elem in enumerate(sections):
    if elem.name == 'h2':
        text = elem.get_text(strip=True)
        for c in countries:
            if text.startswith(c):
                if i+1 < len(sections) and sections[i+1].name == 'table':
                    country_data.append((c, sections[i+1]))
                break

meps = []
country_counts = {c: 0 for c in countries}
ep_map = {'RE': 'Renew Europe', 'G/EFA': 'Greens/EFA', 'Left': 'The Left',
         'NI': 'Non-Inscrits', 'PfE': 'Patriots for Europe', 'ESN': 'Europe of Sovereign Nations'}

for country, table in country_data:
    rows = table.find_all('tr')
    if len(rows) < 3:
        continue

    header = rows[0].find_all(['th', 'td'])
    header_text = [h.get_text(strip=True) for h in header]
    has_constituency = 'Constituency' in header_text

    for row in rows:
        cells = row.find_all(['td', 'th'])
        if len(cells) < 5:
            continue
        cell_texts = [c.get_text(strip=True) for c in cells]

        if cell_texts[0] in ['Elected', 'Current', 'Initial', 'In office', 'MEP', 'Constituency']:
            continue

        constituency = ''
        if has_constituency:
            if len(cells) < 14:
                continue
            constituency = cell_texts[0]
            name = cell_texts[1]
            nat_party = cell_texts[3]
            ep_group = cell_texts[7]
            in_office = cell_texts[8]
            birth = cell_texts[10]
            notes = cell_texts[11]
        else:
            if len(cells) < 12:
                continue
            name = cell_texts[0]
            nat_party = cell_texts[2]
            ep_group = cell_texts[6]
            in_office = cell_texts[7]
            birth = cell_texts[9]
            notes = cell_texts[10]

        if not name or len(name) < 3:
            continue

        name = re.sub(r'\[.*?\]', '', name).strip()
        name = re.sub(r'\s+', ' ', name).strip()
        ep_group = ep_map.get(ep_group, ep_group)

        meps.append([name, country, constituency, nat_party, ep_group, in_office, birth, notes])
        country_counts[country] += 1

for c in countries:
    if country_counts[c] > 0:
        print(f'{c}: {country_counts[c]} MEPs')

print(f'Total: {len(meps)}')

df = pd.DataFrame(meps, columns=['Name', 'Country', 'Constituency', 'National_Party', 'EP_Group', 'In_Office_Since', 'Birth_Date', 'Notes'])
df = df.drop_duplicates(subset=['Name', 'Country'])
print(f'After dedup: {len(df)}')
print(df['EP_Group'].value_counts())
df.to_csv('meps_2024_2029.csv', index=False)
print('Saved to meps_2024_2029.csv')
