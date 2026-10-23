# Euro-SDT v2 Report

Generated from `euro_sdt_v2.db`, `audit/v1_baseline.json`, and `graph/metrics.json`.

## v1 to v2

| Metric | v1 | v2 |
|---|---:|---:|
| Assertions / facts | 5313 | 5462 |
| Verified | 726 | 4122 |
| Needs review | — | 186 |
| Rejected | — | 1154 |
| Source documents | 0 hashed | 783 hashed |
| Sentences | 0 | 36873 |

The v1 counts are not directly comparable: v1 called every row `confirmed`,
and 30.1% of its provenance rows had no sentence evidence. v2 reports the
verified subset and keeps rejected candidates in `rejection`.

## Assertions

| Status | Grade | Count |
|---|---|---:|
| needs_review | B | 8 |
| needs_review | C | 178 |
| rejected | B | 138 |
| rejected | C | 564 |
| rejected | none | 452 |
| verified | A | 3074 |
| verified | B | 479 |
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
| educated_at | needs_review | 19 |
| educated_at | rejected | 115 |
| educated_at | verified | 618 |
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
| member | needs_review | 19 |
| member | rejected | 286 |
| member | verified | 1177 |
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

Claims from full-document extraction: **1127**.


## Evidence and adjudication

| Rejection stage | Count |
|---|---:|
| source_resolution | 722 |
| llm_adjudication | 702 |
| locator | 452 |
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
| wikipedia | 494 | 4948475 |
| cjeu | 92 | 227327 |
| dg_cv | 82 | 177208 |
| revolving_door | 67 | 48681 |
| declaration | 29 | 307404 |
| entity_md | 12 | 26559 |
| org_site | 7 | 237607 |

## Graph

| Metric | All verified | Network only |
|---|---:|---:|
| Nodes | 2933 | 2147 |
| Edges | 3680 | 2613 |
| Largest component | 2644 | 1914 |
| Degree-1 nodes | 2207 | 1610 |

### Edges by class

| Class | Edges |
|---|---:|
| education | 610 |
| institutional | 94 |
| network | 2613 |
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
