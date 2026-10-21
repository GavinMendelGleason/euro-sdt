# Euro-SDT v2 Report

Generated from `euro_sdt_v2.db`, `audit/v1_baseline.json`, and `graph/metrics.json`.

## v1 to v2

| Metric | v1 | v2 |
|---|---:|---:|
| Assertions / facts | 5313 | 5380 |
| Verified | 726 | 4036 |
| Needs review | — | 177 |
| Rejected | — | 1167 |
| Source documents | 0 hashed | 707 hashed |
| Sentences | 0 | 33901 |

The v1 counts are not directly comparable: v1 called every row `confirmed`,
and 30.1% of its provenance rows had no sentence evidence. v2 reports the
verified subset and keeps rejected candidates in `rejection`.

## Assertions

| Status | Grade | Count |
|---|---|---:|
| needs_review | B | 8 |
| needs_review | C | 169 |
| rejected | B | 139 |
| rejected | C | 565 |
| rejected | none | 463 |
| verified | A | 2990 |
| verified | B | 477 |
| verified | C | 569 |

## Predicate results

| Predicate | Status | Count |
|---|---|---:|
| advisory_board | needs_review | 3 |
| advisory_board | rejected | 19 |
| advisory_board | verified | 100 |
| affiliated_with | needs_review | 15 |
| affiliated_with | rejected | 93 |
| affiliated_with | verified | 413 |
| attendee | needs_review | 4 |
| attendee | rejected | 2 |
| attendee | verified | 26 |
| board_member | needs_review | 19 |
| board_member | rejected | 53 |
| board_member | verified | 360 |
| chair | needs_review | 17 |
| chair | rejected | 79 |
| chair | verified | 510 |
| educated_at | needs_review | 11 |
| educated_at | rejected | 126 |
| educated_at | verified | 533 |
| employed_by | needs_review | 25 |
| employed_by | rejected | 21 |
| employed_by | verified | 362 |
| fellow | rejected | 1 |
| fellow | verified | 19 |
| founder | needs_review | 7 |
| founder | rejected | 8 |
| founder | verified | 64 |
| from_country | needs_review | 6 |
| from_country | rejected | 77 |
| from_country | verified | 62 |
| held_degree | needs_review | 2 |
| held_degree | rejected | 1 |
| held_degree | verified | 17 |
| held_portfolio | needs_review | 10 |
| held_portfolio | rejected | 32 |
| held_portfolio | verified | 141 |
| held_position | needs_review | 5 |
| held_position | rejected | 56 |
| held_position | verified | 58 |
| member | needs_review | 18 |
| member | rejected | 288 |
| member | verified | 1176 |
| nominated_by | needs_review | 5 |
| nominated_by | rejected | 80 |
| nominated_by | verified | 60 |
| post_mandate_occupation | needs_review | 12 |
| post_mandate_occupation | rejected | 143 |
| post_mandate_occupation | verified | 1 |
| served_on_commission | needs_review | 17 |
| served_on_commission | rejected | 70 |
| served_on_commission | verified | 94 |
| started_on | rejected | 7 |
| studied_field | needs_review | 1 |
| studied_field | rejected | 11 |
| studied_field | verified | 40 |

## Runs

| Kind | Model | Started | Finished |
|---|---|---|---|
| extraction | deepseek-chat | 2026-10-21T08:55:41+00:00 |  |
| extraction | deepseek-chat | 2026-10-21T08:56:27+00:00 | 2026-10-21T08:56:51+00:00 |

Claims from full-document extraction: **1127**.


## Evidence and adjudication

| Rejection stage | Count |
|---|---:|
| source_resolution | 722 |
| llm_adjudication | 702 |
| locator | 463 |
| migration | 51 |
| party_group_guard | 2 |

| LLM verdict | Count |
|---|---:|
| SUPPORTED | 1744 |
| UNSUPPORTED | 743 |
| AMBIGUOUS | 170 |
| ERROR | 8 |

## Sources

| Kind | Documents | Characters |
|---|---:|---:|
| wikipedia | 418 | 4502718 |
| cjeu | 92 | 227327 |
| dg_cv | 82 | 177208 |
| revolving_door | 67 | 48681 |
| declaration | 29 | 307404 |
| entity_md | 12 | 26559 |
| org_site | 7 | 237607 |

## Graph

| Metric | All verified | Network only |
|---|---:|---:|
| Nodes | 2834 | 2147 |
| Edges | 3594 | 2612 |
| Largest component | 2598 | 1914 |
| Degree-1 nodes | 2146 | 1610 |

### Edges by class

| Class | Edges |
|---|---:|
| education | 525 |
| institutional | 94 |
| network | 2612 |
| occupational | 361 |
| other | 2 |

### Top hubs

| Entity | Kind | Degree |
|---|---|---:|
| European Commission | organisation | 72 |
| European Parliament | organisation | 51 |
| Kaja Kallas | person | 41 |
| Pascal Lamy | person | 35 |
| Neelie Kroes | person | 34 |
| Ria Oomen-Ruijten | person | 34 |
| Thierry Breton | person | 33 |
| Federica Mogherini | person | 32 |
| Pierre Moscovici | person | 32 |
| Mario Monti | person | 30 |
| António Vitorino | person | 29 |
| Günther Oettinger | person | 29 |

## Remaining limitations

- MEP and corporate Wikipedia coverage is incomplete; claims without a local
  source document are rejected rather than assigned a guessed quote.
- `revolving_door` documents are treated as summaries, not primary sentences;
  they are excluded from `served_on_commission` recovery.
- Organisation classifications remain a manually researched seed. They are
  marked `manual_seed` and are not counted as verified assertions.
- `post_mandate_occupation` coverage remains low because the source corpus
  contains summaries rather than the underlying ethics decisions.
