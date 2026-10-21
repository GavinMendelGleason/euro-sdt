# Model Comparison: deepseek-chat vs deepseek-flash

Date: 2026-10-21. Sample: 128 claims across 16 predicates, same evidence and
prompt for every model. No database rows were changed.

## Adjudication

| Pair | Agreement | Valid | Rate |
|---|---:|---:|---:|
| chat vs flash (thinking disabled) | 126 | 128 | 98.4% |
| chat vs flash (thinking enabled) | 97 | 128 | 75.8% |
| flash disabled vs flash reasoning | 95 | 128 | 74.2% |

Verdict distribution:

| Model | Supported | Unsupported | Ambiguous |
|---|---:|---:|---:|
| chat | 87 | 41 | 0 |
| flash (disabled) | 89 | 39 | 0 |
| flash (reasoning) | 74 | 31 | 23 |

The two chat/flash disagreements were both `attendee` claims where flash
treated a role ("vice speaker", "speaker") as attendance. That is the wrong
direction.

Flash reasoning was more conservative and caught several chat false positives:

- `founder`: "contributed to the creation" treated as founding.
- `affiliated_with`: a donation announced to an institution treated as affiliation.
- `held_position`: a truncated or renamed directorate treated as an exact match.
- `from_country`: birth or a role in a country treated as nationality.

It also produced false negatives and ambiguity:

- `chair`: "President of Nokia Mobile Phones" was rejected.
- `fellow`: "studied on a Henry Fellowship" was treated as unsupported.
- `served_on_commission`: a term was not identified even when the quote placed
  the person on the Commission.

## Extraction

Four biographies, eight chunks, same prompt and source text:

| Model | Behaviour |
|---|---|
| chat | 68 rows across 8 chunks |
| flash disabled | Similar; +4 rows on one Mogherini chunk (including duplicate Chamber of Deputies and NATO delegation surface forms), 0 rows on a Faury chunk where chat found 3 |
| flash reasoning | Empty responses on 6 of 8 chunks with the current 4,000-token extraction budget |

The extraction script now has a working `--thinking` path that uses
`reasoning_effort: "low"`, an 8,000-token budget, plain-text JSON parsing, and
8-sentence chunks. It is a targeted option, not a default.

On one 8-sentence chunk, thinking-off returned 3 rows in 179 completion
tokens. Thinking-on returned 5–6 rows in about 2,800 completion tokens, of which
about 2,465 were reasoning tokens (roughly 15x the cost). The extra rows included
entities the prompt explicitly excludes (European Commission, German federal
government) and duplicate surface forms (`Commission` and `European Commission`,
`EPP` and `European People's Party`). Thinking-on is therefore **not suitable
for a full extraction run** without additional post-filtering and a taxonomy
change. It is only a targeted option for a small, high-value set.

## Conclusion

There is no evidence yet that flash improves quality over `deepseek-chat` for
this pipeline.

- **Flash with thinking disabled** is effectively a drop-in alternative, not an
  upgrade. It agrees 98.4% with chat and has at least one recall failure.
- **Flash with thinking enabled** is a useful second adjudicator: it catches
  real false positives, but it increases ambiguity and has its own false
  negatives. It is not suitable as the sole judge.
- **Flash reasoning for extraction** is not operational with the current
  `response_format` and token budget; it returned empty content on most chunks.

To try extraction with thinking on:

```bash
.venv/bin/python scripts/extract_v2.py --categories commissioner \
  --model deepseek-flash --thinking --limit 1
```

This writes claims to `euro_sdt_v2.db`, so use a disposable copy or a small
`--limit`. Expect roughly 15x the completion tokens of thinking-off.

A full second-judge pass over 738 grade-C claims kept 569 and moved 169 to
`needs_review`; no claim was promoted on the second judge alone.

Recommended use: run flash reasoning as a second adjudicator, send
disagreements to `needs_review`, and keep `deepseek-chat` as the primary
extractor until a human-labelled gold set shows a precision or recall gain.
If cost or latency is the goal, flash disabled is viable, but add an empty-
response retry and validate it on the gold set first.
