# Judicial education, memberships, fellowships and awards

Extracted from official CJEU biographies for all valid judicial-roster members.

| Metric | Value |
|---|---:|
| Valid members covered | **98** |
| Invalid entries excluded | **8** |
| Affiliation/education rows | **844** |

| Kind | Rows | People |
|---|---:|---:|
| Education | 293 | 98 |
| Membership | 409 | 87 |
| Award | 120 | 47 |
| Fellowship | 22 | 15 |
| Post-CJEU role | 0 | 0 |

## By track

| Track | People | Rows |
|---|---:|---:|
| Court of Justice judges | 31 | 277 |
| Advocates General | 13 | 158 |
| General Court judges | 53 | 407 |
| Registrar | 1 | 2 |

## Coverage

- Education: **98/98** valid members.
- Memberships: **87/98**.
- Awards: **47/98**.
- Fellowships: **15/98**.
- Post-CJEU roles: **0**; the official biographies do not state post-CJEU roles for the covered former members.

## Method

- Source files: `sources/cjeu/*.txt`, `sources/official/cjeu-*.txt`, `sources/official/cjeu-general-court-members.txt`, and `sources/official/cjeu-court-members-current.txt`.
- Every `source_quote` was checked as an exact contiguous substring of its source file.
- No Wikipedia or news sources used.
- The eight invalid roster entries were excluded.
- `judicial_affiliation` stores person, kind, organisation, role, dates, precision, source file and quote.

## Limitation

The biographies are strong for education, memberships, awards and fellowships. They are weak for post-CJEU employment; that requires separate post-retirement declarations, annual reports, or later biographies.
