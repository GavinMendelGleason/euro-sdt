# Euro-SDT v2: Citation-Anchored Assertion Layer

## Why v2 exists

The v1 database is a useful candidate pool and source corpus, but its evidence
layer is not reproducible:

- 30.1% of provenance rows carry no sentence evidence (LLM self-classification,
  generated strings, name-presence checks, missing indices, missing citations).
- Only 17.6% of rows resolve to the recorded sentence under a deterministic
  tokeniser, because v1 used several tokenisers and stored indices from a
  filtered/truncated list.
- No `affiliated_with` edge was ever verified. The one verification run that
  ran marked 57% of the facts it checked as unsupported; 313 of those facts
  remain `confirmed` in v1.
- One predicate (`affiliated_with`) mixed board seats, employment, party
  membership, committee membership, and conference attendance.

The reproducible baseline is in `audit/v1_baseline.md`. Re-run it with:

```bash
.venv/bin/python scripts/audit_v1.py
```

## Data model

```text
source_document ──< sentence ──< evidence >── claim ──< assertion
      │                                         │
      └── sha256, url, revision                 └── subject/object entities
```

- `source_document` is a snapshot: local path, SHA-256, URL, revision, retrieval
  date. A source without a hash cannot enter the corpus.
- `sentence` has exact character offsets. Sentence IDs are the only locator.
- `claim` is a candidate. Claims are unique by subject, predicate, object, role.
- `evidence` is a located quote and its sentence span. It is rejected if the
  quote cannot be found; no index is guessed.
- `assertion` is the decision. Only `verified` assertions enter the graph.
- `adjudication` records the model, verdict, and reason for every LLM decision.
- `organisation_profile` holds classifications and descriptions separately from
  graph edges. The manual seed is marked `manual_seed`; it is never presented as
  sourced.

## Evidence grades

| Grade | Rule |
|---|---|
| A | quote locates; subject, object, and role/nomination wording are in the span |
| B | quote locates; subject and object are in the span; role is implicit (only for membership/affiliation/education) |
| C | quote locates but the span is missing the subject, object, or required role wording; sent to LLM adjudication |
| none | quote does not locate; rejected |

LLM adjudication runs on all `needs_review` and `verified` grade-B claims. The
model is a judge, not an extractor: it receives one exact quote and one claim,
and cannot introduce a new fact. `UNSUPPORTED` becomes rejected; `AMBIGUOUS`
stays in review.

## Role taxonomy

`member`, `board_member`, `advisory_board`, `chair`, `founder`, `fellow`,
`attendee`, `affiliated_with`, `employed_by`, `educated_at`,
`served_on_commission`, `held_portfolio`, `nominated_by`, `from_country`,
`post_mandate_occupation`, `held_position`, `studied_field`, `held_degree`.

The graph exports `edge_class` so occupational, educational, institutional, and
network edges can be analysed separately. Attendance is not membership.

## Commands

```bash
# Rebuild source documents, sentences, claims, evidence, assertions.
.venv/bin/python scripts/run_v2.py

# Extract affiliations from full documents (no truncation).
.venv/bin/python scripts/extract_v2.py --categories commissioner

# Judge non-A evidence. Requires DEEPSEEK_API_KEY.
.venv/bin/python scripts/adjudicate.py --workers 6

# Export graph, wiki, and audit.
.venv/bin/python scripts/render_v2.py

# CI gate. Non-zero exit on an invariant failure.
.venv/bin/python scripts/check_v2.py

# Unit tests.
.venv/bin/python -m unittest tests.test_v2
```

## Invariants enforced by `check_v2.py`

- every verified assertion has at least one located evidence row;
- every located evidence row has sentence IDs and a source document;
- every claim has an object;
- no two active entities share a kind and normalised name;
- every source document has a hash and at least one sentence;
- graph, wiki, and audit artifacts exist.

## Viewing and exporting the graph

```bash
# Static overview (network edges, grades A–B, top nodes by degree)
.venv/bin/python scripts/plot_graph.py
# Stricter view
.venv/bin/python scripts/plot_graph.py --edge-class network --grades A --top 120
```

Open `graph/graph.graphml` in Gephi or Cytoscape. Filter `edge_class = network`
and `grade = A` for the strictest network view; use `role` to separate board
seats from attendance or employment. `graph/edges.csv` carries the best located
quote and the source document for every edge: `doc_id`, `doc_title`, `doc_path`,
`doc_sha256`, and `source_url` where the source is a public web page. Local-only
documents (DG CVs, CJEU, declarations) have a path and hash but no URL. Verified
claims whose endpoint is quarantined are excluded from the graph.

## Results

The generated artifacts are:

- `euro_sdt_v2.db` — assertions and provenance;
- `graph/nodes.csv`, `graph/edges.csv`, `graph/graph.graphml`;
- `graph/metrics.json`, `graph/report.md`;
- `wiki_v2/` — verified-only pages with source links;
- `audit/v2_audit.md`, `audit/v2_audit.json`;
- `audit/llm_adjudication_cache.json`.

The graph is an analysis artifact, not an Obsidian screenshot. Edge attributes
(grade, class, role, quote, document) are in `edges.csv`.
