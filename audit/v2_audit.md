# v2 Audit

## Counts

| Table | Rows |
|---|---:|
| source_document | 707 |
| sentence | 33901 |
| entity | 3588 |
| entity_alias | 6286 |
| claim | 5380 |
| evidence | 6084 |
| assertion | 5380 |
| rejection | 1940 |
| organisation_profile | 856 |
| adjudication | 1927 |

## Assertions

| Status | Count |
|---|---:|
| verified | 4162 |
| rejected | 1167 |
| needs_review | 51 |

| Grade | Count |
|---|---:|
| A | 2990 |
| B | 624 |
| C | 1303 |
| none | 463 |

## Evidence locator

| Status | Rows |
|---|---:|
| located | 5918 |
| quote_not_found | 160 |
| empty_quote | 6 |

## Rejections

| Stage | Count |
|---|---:|
| source_resolution | 722 |
| llm_adjudication | 702 |
| locator | 463 |
| migration | 51 |
| party_group_guard | 2 |

## Invariants

| Check | Value | Expected |
|---|---:|---|
| verified_without_located_evidence | 0 | 0 |
| verified_grade_none | 0 | 0 |
| located_evidence_without_sentence | 0 | 0 |
| evidence_without_doc | 0 | 0 |
| claims_without_object | 0 | 0 |
| duplicate_active_entities | 0 | 0 |
| quarantined_entities | 38 | informational |
| documents_without_sentences | 0 | 0 |
| documents_without_hash | 0 | 0 |
| recovered_evidence | 1051 | informational |
| llm_adjudications | 1927 | informational |
| verified_claims_with_object | 3723 | informational |

`duplicate_active_entities` compares exact normalised names within a kind;
fuzzy duplicates are listed separately in `audit/entity_merge.json`.
