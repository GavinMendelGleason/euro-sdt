# Batch E — missing biographies

## Ioannis Gratsias (Greece, Advocate General, AG)

No official CJEU biography text for this person exists in the repository, so no career
fragments were extracted for him.

Evidence:

- `sources/cjeu/` contains no file for this person. A case-insensitive search for
  `gratsias` across `sources/` matches exactly one file, `sources/cjeu/dimitrios-gratsias.txt`,
  which is the biography of **Dimitrios Gratsias** (Judge, born 1957 in Athens, Judge at the
  General Court 25 October 2010 – 6 October 2021, Judge at the Court of Justice since
  7 October 2021).
- `sources/official/` contains no `cjeu-*gratsias*` file, and no other file in `sources/official/`
  mentions the name.
- `audit/education_gaps.csv` and `audit/external_sources_needed.csv` already record
  `ioannis-gratsias` with zero education entries and list "CURIA member biography;
  Wikipedia; national judicial profile" as still-needed sources.
- `wiki/people/ioannis-gratsias.md` holds only the membership-list assertion
  ("held_position: Advocate General") with no biography.

The Dimitrios Gratsias biography was deliberately **not** used: the name differs from the
`data/cjeu/cjeu_members_list.csv` entry, and the recorded role differs (Judge of the Court of
Justice versus Advocate General). Mapping it to `Ioannis Gratsias` would assert an identity
the sources do not state.

To close this gap, the CURIA biography page for Ioannis Gratsias needs to be retrieved and
saved as `sources/cjeu/<slug>.txt`; the extraction can then be re-run.
