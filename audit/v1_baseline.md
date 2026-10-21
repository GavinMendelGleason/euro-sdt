# v1 Baseline Audit

Reproduced by `scripts/audit_v1.py` from `euro_sdt.db` and `sources/`.

## Counts

| Metric | Value |
|---|---:|
| facts | 5313 |
| entities | 2504 |
| citations | 632 |
| provenance | 5261 |
| facts without provenance | 52 |
| facts verified | 726 |
| facts confirmed | 5313 |
| affiliation edges | 2552 |
| affiliated with verified | 0 |
| member of verified | 48 |
| distinct affiliation orgs | 2001 |
| degree one orgs | 1750 |
| classification facts | 892 |
| classification llm | 844 |
| classification dataset | 41 |
| citation missing rows | 54 |
| zero fact entities | 1162 |
| isolated entities | 162 |

## Summary

| Metric | Value |
|---|---:|
| quote present in source | 2686 |
| quote present share | 51.1 |
| index resolves under v2 tokenizer | 1012 |
| index resolves share | 19.2 |
| no sentence evidence | 1586 |
| no sentence evidence share | 30.1 |

## Evidence tiers

| Tier | Rows | Share |
|---|---:|---:|
| index-mismatch | 1674 | 31.8% |
| located | 1012 | 19.2% |
| llm-self-classification | 844 | 16.0% |
| quote-not-in-source | 626 | 11.9% |
| synthetic | 383 | 7.3% |
| source-missing | 363 | 6.9% |
| name-presence | 188 | 3.6% |
| no-index | 117 | 2.2% |
| citation-missing | 54 | 1.0% |

`located` means the quote appears at the recorded sentence position under a
deterministic sentence split of the cited `.txt`. It is an upper bound on
locatability, not a check that the sentence entails the relation.
