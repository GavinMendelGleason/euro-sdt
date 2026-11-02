# v2 Audit

## Counts

| Table | Rows |
|---|---:|
| source_document | 821 |
| sentence | 37448 |
| entity | 3650 |
| entity_alias | 6353 |
| claim | 5498 |
| evidence | 6217 |
| assertion | 5498 |
| rejection | 1928 |
| organisation_profile | 856 |
| adjudication | 2664 |
| review | 0 |

## Assertions

| Status | Count |
|---|---:|
| verified | 4153 |
| rejected | 1153 |
| needs_review | 192 |

| Grade | Count |
|---|---:|
| A | 3101 |
| B | 629 |
| C | 1316 |
| none | 452 |

## Evidence locator

| Status | Rows |
|---|---:|
| located | 6051 |
| quote_not_found | 160 |
| empty_quote | 6 |

## Rejections

| Stage | Count |
|---|---:|
| source_resolution | 722 |
| llm_adjudication | 701 |
| locator | 452 |
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
| llm_adjudications | 2664 | informational |
| verified_claims_with_object | 3736 | informational |
| verified_edges_without_quote | 0 | 0 |
| verified_claims_with_quarantined_endpoint | 25 | informational |
| verified_edges_without_doc | 0 | 0 |
| documents_without_path | 0 | 0 |

`duplicate_active_entities` compares exact normalised names within a kind;
fuzzy duplicates are listed separately in `audit/entity_merge.json`.
