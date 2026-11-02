# Euro-SDT v2 Report

Generated from `euro_sdt_v2.db`, `audit/v1_baseline.json`, and `graph/metrics.json`.

## v1 to v2

| Metric | v1 | v2 |
|---|---:|---:|
| Assertions / facts | 5313 | 5707 |
| Verified | 726 | 4326 |
| Needs review | — | 229 |
| Rejected | — | 1152 |
| Source documents | 0 hashed | 823 hashed |
| Sentences | 0 | 37481 |

The v1 counts are not directly comparable: v1 called every row `confirmed`,
and 30.1% of its provenance rows had no sentence evidence. v2 reports the
verified subset and keeps rejected candidates in `rejection`.

## Assertions

| Status | Grade | Count |
|---|---|---:|
| needs_review | B | 8 |
| needs_review | C | 221 |
| rejected | B | 138 |
| rejected | C | 563 |
| rejected | none | 451 |
| verified | A | 3267 |
| verified | B | 490 |
| verified | C | 569 |

## Predicate results

| Predicate | Status | Count |
|---|---|---:|
| advisory_board | needs_review | 6 |
| advisory_board | rejected | 19 |
| advisory_board | verified | 107 |
| affiliated_with | needs_review | 16 |
| affiliated_with | rejected | 93 |
| affiliated_with | verified | 437 |
| attendee | needs_review | 4 |
| attendee | rejected | 2 |
| attendee | verified | 26 |
| award_received | verified | 2 |
| awarded_by | verified | 1 |
| board_member | needs_review | 20 |
| board_member | rejected | 53 |
| board_member | verified | 395 |
| chair | needs_review | 18 |
| chair | rejected | 79 |
| chair | verified | 544 |
| educated_at | needs_review | 25 |
| educated_at | rejected | 115 |
| educated_at | verified | 640 |
| employed_by | needs_review | 47 |
| employed_by | rejected | 21 |
| employed_by | verified | 370 |
| fellow | verified | 28 |
| founder | needs_review | 12 |
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
| member | needs_review | 23 |
| member | rejected | 285 |
| member | verified | 1239 |
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
| education | deepseek-chat | 2026-10-23T22:46:22+00:00 |  |
| education | deepseek-chat | 2026-10-23T22:46:38+00:00 |  |
| education | deepseek-chat | 2026-10-23T23:02:29+00:00 |  |
| education | deepseek-chat | 2026-10-24T05:46:00+00:00 |  |
| education | deepseek-chat | 2026-10-24T05:47:27+00:00 |  |
| education | deepseek-chat | 2026-10-24T05:48:31+00:00 |  |
| education | deepseek-chat | 2026-10-24T05:49:54+00:00 |  |
| declaration_extraction | deepseek-chat | 2026-11-02T13:28:08+00:00 |  |

Claims from full-document extraction: **1127**.


## Evidence and adjudication

| Rejection stage | Count |
|---|---:|
| source_resolution | 721 |
| llm_adjudication | 701 |
| locator | 451 |
| migration | 51 |
| party_group_guard | 2 |

| LLM verdict | Count |
|---|---:|
| SUPPORTED | 1744 |
| UNSUPPORTED | 742 |
| AMBIGUOUS | 170 |
| ERROR | 8 |

## Sources

| Kind | Documents | Characters |
|---|---:|---:|
| wikipedia | 494 | 4948475 |
| cjeu | 92 | 227327 |
| dg_cv | 82 | 177208 |
| revolving_door | 67 | 48681 |
| official | 40 | 129798 |
| declaration | 29 | 307404 |
| entity_md | 12 | 26559 |
| org_site | 7 | 237607 |

## Graph

| Metric | All verified | Network only |
|---|---:|---:|
| Nodes | 3101 | 2285 |
| Edges | 3884 | 2784 |
| Largest component | 2801 | 2049 |
| Degree-1 nodes | 2356 | 1737 |

### Edges by class

| Class | Edges |
|---|---:|
| award | 3 |
| education | 632 |
| institutional | 94 |
| network | 2784 |
| occupational | 369 |
| other | 2 |

### Top hubs

| Entity | Kind | Degree |
|---|---|---:|
| European Commission | organisation | 72 |
| European Parliament | organisation | 54 |
| Kaja Kallas | person | 46 |
| Ursula von der Leyen | person | 43 |
| Henna Virkkunen | person | 35 |
| Pascal Lamy | person | 35 |
| Neelie Kroes | person | 34 |
| Ria Oomen-Ruijten | person | 34 |
| Thierry Breton | person | 33 |
| Wopke Hoekstra | person | 33 |
| Federica Mogherini | person | 32 |
| Pierre Moscovici | person | 32 |

## Remaining limitations

- MEP and corporate Wikipedia coverage is incomplete; claims without a local
  source document are rejected rather than assigned a guessed quote.
- `revolving_door` documents are treated as summaries, not primary sentences;
  they are excluded from `served_on_commission` recovery.
- Organisation classifications remain a manually researched seed. They are
  marked `manual_seed` and are not counted as verified assertions.
- `post_mandate_occupation` coverage remains low because the source corpus
  contains summaries rather than the underlying ethics decisions.
