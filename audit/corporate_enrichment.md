# Corporate elite enrichment

## Coverage

- Corporate people in `role_tenure`: **976**
- Matched to Wikidata via exact Wikipedia title: **62**
- `person_profile` facts stored: **505**
- Role records: **1,019** across **53/53** frame companies

| Attribute | People |
|---|---:|
| Description | 62 |
| Birth date | 53 |
| Citizenship | 51 |
| Education | 42 |
| Occupation | 55 |
| Employer | 30 |
| Position | 27 |
| Member of | 16 |

## Caveats

- Matching uses an exact Wikipedia title only. It is a discovery layer, not a final identity resolution.
- All profile rows use `status='wikidata_title_match'`; they must be checked before analysis.
- Wikidata API rate limits blocked a full 976-person pass. A direct-title batch reached 62 people.
- The remaining people require employer/board-context matching, official biographies, or a Wikidata dump/QLever bulk pass.

## Database

`person_profile` stores `entity_id`, `attribute`, `value`, `value_id`, `quote`, `status`, `source_url`, and `notes`.

`wikidata_matches.csv` records the matched QID and description for review.

After vacuuming, `euro_sdt_v2.db` is 47 MB.
