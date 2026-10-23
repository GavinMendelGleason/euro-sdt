# v2 Audit

## Counts

| Table | Rows |
|---|---:|
| source_document | 783 |
| sentence | 36873 |
| entity | 3631 |
| entity_alias | 6330 |
| claim | 5462 |
| evidence | 6182 |
| assertion | 5462 |
| rejection | 1929 |
| organisation_profile | 856 |
| adjudication | 2665 |
| review | 0 |

## Assertions

| Status | Count |
|---|---:|
| verified | 4122 |
| rejected | 1154 |
| needs_review | 186 |

| Grade | Count |
|---|---:|
| A | 3074 |
| B | 625 |
| C | 1311 |
| none | 452 |

## Evidence locator

| Status | Rows |
|---|---:|
| located | 6016 |
| quote_not_found | 160 |
| empty_quote | 6 |

## Rejections

| Stage | Count |
|---|---:|
| source_resolution | 722 |
| llm_adjudication | 702 |
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
| llm_adjudications | 2665 | informational |
| verified_claims_with_object | 3705 | informational |
| verified_edges_without_quote | 0 | 0 |
| verified_claims_with_quarantined_endpoint | 25 | informational |
| verified_edges_without_doc | 0 | 0 |
| documents_without_path | 0 | 0 |

`duplicate_active_entities` compares exact normalised names within a kind;
fuzzy duplicates are listed separately in `audit/entity_merge.json`.
