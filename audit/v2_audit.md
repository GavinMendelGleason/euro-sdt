# v2 Audit

## Counts

| Table | Rows |
|---|---:|
| source_document | 991 |
| sentence | 51270 |
| entity | 4774 |
| entity_alias | 7485 |
| claim | 6716 |
| evidence | 7485 |
| assertion | 6716 |
| rejection | 1926 |
| organisation_profile | 971 |
| adjudication | 2664 |
| review | 0 |

## Assertions

| Status | Count |
|---|---:|
| verified | 5331 |
| rejected | 1150 |
| needs_review | 235 |

| Grade | Count |
|---|---:|
| A | 4272 |
| B | 636 |
| C | 1359 |
| none | 449 |

## Evidence locator

| Status | Rows |
|---|---:|
| located | 7319 |
| quote_not_found | 160 |
| empty_quote | 6 |

## Rejections

| Stage | Count |
|---|---:|
| source_resolution | 721 |
| llm_adjudication | 701 |
| locator | 451 |
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
| quarantined_entities | 39 | informational |
| documents_without_sentences | 0 | 0 |
| documents_without_hash | 0 | 0 |
| recovered_evidence | 1051 | informational |
| llm_adjudications | 2664 | informational |
| verified_claims_with_object | 4914 | informational |
| verified_edges_without_quote | 0 | 0 |
| verified_claims_with_quarantined_endpoint | 26 | informational |
| verified_edges_without_doc | 0 | 0 |
| documents_without_path | 0 | 0 |

`duplicate_active_entities` compares exact normalised names within a kind;
fuzzy duplicates are listed separately in `audit/entity_merge.json`.
