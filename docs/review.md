# Reviewing v2 Assertions

## Commands

```bash
# Full queue: needs_review + verified B/C, plus a sample of grade-A network claims
.venv/bin/python scripts/review.py list --include-a --sample-a 50

# Record a human decision
.venv/bin/python scripts/review.py decide \
  --claim-id c-... --decision rejected \
  --reviewer gavin --reason "quote names the parliamentary group, not the party"
```

Outputs:

- `audit/review_queue.csv` — one row per claim, with quote, source path/URL, evidence
  flags, adjudication verdict, and priority.
- `audit/review_queue.md` — top rows and counts.
- `review` table — every human decision with reviewer, reason, and timestamp.

## Priority

The queue score combines:

- `needs_review` status (+50)
- grade C (+40), grade B (+20), grade A sample (+5)
- subject only present in the document, not the quote (+15)
- recovered sentence-search evidence (+10)
- single-source claim (+5)
- network predicate (+5)
- chat/flash model disagreement (+20)

## What to be skeptical about

1. **Grade A is not entailment.** The deterministic gate checks that the quote
   locates and mentions the subject, object, and role. It cannot tell whether
   the relation is actually asserted. In a 72-claim grade-A sample, `deepseek-chat`
   rejected 10 (about 14%). Examples:
   - vice-president described as `chair`
   - an adjunct professorship described as `educated_at`
   - “independent foundation” described as `founder`
   - speaker of a parliament described as `attendee`
   - deputy director-general described as director-general
2. **Grade C is a single-model decision.** 695 verified edges rest on one
   adjudication. Flash thinking-on agrees with chat only 76% of the time and
   raises many more AMBIGUOUS verdicts; it is a useful second opinion, not a
   replacement.
3. **Most evidence is document-scoped, not sentence-scoped.** 4,891 of 5,918
   located evidence rows have `subject_context='document'`: the person is not
   named in the quote, only in the document. This is defensible for CVs and
   declarations but can misattribute lists.
4. **Recovered evidence is weaker.** 825 verified claims come from deterministic
   sentence search rather than the original extraction. They are graded and
   adjudicated, but they are a second-best path.
5. **Corroboration is thin.** 3,473 of 4,161 verified assertions have one
   source; only 497 have two or more.
6. **Coverage is uneven.** MEPs, corporate elites, DGs/DDGs, and CJEU members
   were not re-extracted with v2; they still use migrated v1 candidates.
   722 claims were rejected because a cited document could not be resolved,
   and 109 citations remain unmapped.
7. **Entity semantics are not fully resolved.** Quarantined entities, parent /
   subsidiary relations, and party vs parliamentary group remain manual
   judgement calls. 25 verified claims are excluded from the graph because an
   endpoint is quarantined.
8. **Flash did not show a quality gain.** Thinking-off is effectively chat;
   thinking-on is more conservative but more ambiguous. Thinking-on extraction
   costs about 15x and violates the exclusion rules.
9. **The paper numbers have not been regenerated.**

## Recommended review order

1. All 51 `needs_review` claims.
2. Network grade-C edges, starting with `board_member`, `chair`, `member`,
   `from_country`, `nominated_by`, and `served_on_commission`.
3. Grade-A claims where a second judge disagrees.
4. Single-source network edges.
5. Under-covered populations: MEP, corporate, DG/DDG, CJEU.
