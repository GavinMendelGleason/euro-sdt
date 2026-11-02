# Provenance audit

## Strong linkage

| Dataset | Linkage |
|---|---|
| `judicial_affiliation` | Source file + exact quote; source URL where available |
| `judicial_career` | Source document + source file + exact quote |
| `institution_cohort` | Source URL + source file for every row |
| `institution_completion` | Source URL + source file |
| `candidate_pool` | Source URL + source file |
| `role_intake` base events | Source document (CURIA Press Release 174/24) |
| `role_intake` institution links | Source file + exact education quote after the provenance repair |

## Partial linkage

| Dataset | Issue |
|---|---|
| `position_census` | Official URL and local file for CJEU stock rows; Commission DG/DDG row remains internal-frame based |
| `judicial_affiliation` | 302 rows have no source URL, but all have a local source file and exact quote |
| `judicial_career` | 72 rows have no source URL, but all have source document, file and quote |
| `education claims` | Evidence rows link claims to documents/sentences |

## Weak / explicit status

| Dataset | Status |
|---|---|
| `institution_profile` | 10 provisional profiles; no external source URL yet |
| `institution_metric` | `source_status='observed_only'`; derived from education counts, not a primary source |

## Rule going forward

No derived metric should be treated as observed data. `institution_metric` currently contains observed alumni counts only; production, openings, placement and overproduction fields are null.
