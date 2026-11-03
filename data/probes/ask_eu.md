# ask_eu — CJEU / Commission candidate pools in FOI and access-to-documents archives

Probe run 2026-11-03. Scope: AskTheEU.org, the Council's public register / document server,
the Commission's document register, and the documents those archives point to.
Only explicitly published counts are recorded as values; refusals and absences are recorded as
`not_public` / `blocked` with the evidence that establishes them.

## 1. CJEU — what is published

The only systematic, authoritative count of people entering the CJEU judicial selection funnel is
the **Article 255 TFEU panel's own activity reports**. One opinion is issued per candidate, so
"number of opinions" is the number of candidates assessed.

Per calendar year (7th activity report, table "breakdown of the panel's activities per full
calendar year"):

| Year | Candidates assessed |
|---|---|
| 2010 | 18 |
| 2011 | 3 |
| 2012 | 22 |
| 2013 | 24 |
| 2014 | 3 |
| 2015 | 24 |
| 2016 | 37 |
| 2017 | 9 |
| 2018 | 23 |
| 2019 | 27 |
| 2020 | 11 |
| 2021 | 32 |
| 2022 (Jan–Feb) | 10 |
| **Total** | **243** |

Cross-checks: the 243 total is stated in the 7th report's conclusions and equals the sum of the
annual rows. Breakdown of the 243: 97 Court of Justice (Judge or Advocate-General), 146 General
Court; 113 renewals (52 CJ, 61 GC), 130 first-term (45 CJ, 85 GC). The 2018 figure is 23 because
the year spans two panels: 7 candidates assessed by the second panel before 1 March 2018 (5th
report) and 16 by the third panel from 1 March (6th report).

Seat counts (denominator): 92 posts at 1 March 2022 — 54 General Court Judges, 27 Court of Justice
Judges, 11 Advocates-General (7th report); 95 posts in 2018–2019 — 56 + 28 + 11 (6th report);
65 posts when the panel was created in 2010.

Post-2022: the fourth panel (1 March 2022 – 28 February 2026) delivered **70 opinions**, but only as
an aggregate on the panel's work page. There is no per-year breakdown and the Eighth activity report
is marked "(In progress)". Per-year figures for 2023–2025 therefore do not exist publicly; that
series is carried in the `c255_post2022` batch, not here.

Openings, from Council IGC notes served by `data.consilium.europa.eu`:

- **2024 partial renewal, Court of Justice: 18 seats** — terms of 13 Judges and 5 Advocates-General
  ended 6 October 2024 (doc 13358/24, §I.1).
- **2025 partial renewal, General Court: 26 seats** — terms of 26 Judges ended 31 August 2025
  (doc 13680/24, §8).

## 2. CJEU — what is refused

No shortlist, ranking or individual opinion has ever been released in full.

- **Council doc 12964/26 (10 September 2026), confirmatory application 48/c/01/26.** Request of
  23 July 2026 for "the list of votes and opinions of this panel for all candidates' suitability"
  over 1 March 2022 – 28 February 2026. The General Secretariat refused full access (Art. 4(1)(b),
  4(2) indent 2, 4(2) indent 1, 4(3) Reg. 1049/2001) and granted partial access to a **sample of
  seven redacted opinions**. It stated the request "covers a very large number of documents" but
  gave no figure.
- **Council ref. 25/0444, decision 31 March 2025, confirmatory reply 5 June 2025** (Alemanno,
  AskTheEU request `selection_of_candidates_for_the`). Refused the panel's opinions on the two
  Portuguese candidates nominated in 2023–2025. The "two candidates" is the requester's own
  description and is not recorded as a value.
- **AskTheEU request `opinions_of_the_255_committee_on`** (Alemanno, response 9 January 2025):
  refused.
- **AskTheEU request `article_255_panel_opinions_on_ju`** (2017): the Council released ten opinions
  in PDF, but they are candidate-level assessments containing no aggregate counts.

The applicant in 12964/26 asserts that no activity report or aggregate statistics exist for
2022–2026. That assertion is not used as evidence here; the independent check is that
`comite255.europa.eu/en/work` lists reports 1–7 only (the 7th dated 14/07/2022) and marks the
Eighth "(In progress)".

## 3. Commission — no published candidate pool

The College of Commissioners has no application process to count: under Article 17(4) TEU each
Member State nominates its candidate, and the President-designate allocates portfolios. There is
therefore no application count, shortlist or ranking for the Commission register to hold.

Searches run against the Commission document register (`POST
https://ec.europa.eu/transparency/documents-register/api/groupSearch`, `EXACT_PHRASE` mode):

| Phrase | Hits | Relevant |
|---|---|---|
| `candidates for appointment as members of the Commission` | 0 | — |
| `shortlist of candidates` | 26 | none is a Commission appointment shortlist |
| `applications were received` | 87 | none reports applicants for a Commission post |
| `applied for the post` | 2 (2005, 2016) | no applicant counts |

Commission senior-management selection (Directors, Directors-General, OLAF Director-General) is
documented only through refusals: AskTheEU requests `selection_process_for_the_post_o`,
`selection_process_for_the_next_d` and `request_for_access_to_documents_16` ask for the shortlist,
rankings and panel recommendations for the OLAF Director-General post; the Commission refused or
closed them, and no applicant or shortlist count appears in the correspondence.

## 4. Access notes (for reproducibility)

- `www.consilium.europa.eu` returns **HTTP 403** to non-browser clients, including the public
  register and its search. Individual documents are still retrievable from
  `https://data.consilium.europa.eu/doc/document/ST-<num>-<year>-<INIT|REV1>/en/pdf`.
- Council documents are also mirrored by the Austrian parliament, e.g.
  `https://www.parlament.gv.at/dokument/XXVIII/EU/<doc>/imfname_<id>.pdf` — this is how 12964/26 was
  obtained.
- AskTheEU search: `https://www.asktheeu.org/search/<query>/all?sortby=newest`. Relevance ranking is
  weak; exact-title queries work better than keyword phrases.
- The Commission register API requires the SPA's query object (fields `keywords`,
  `keywordsSearchType`, `target`, `types`, `departments`, `language`, `sortBy`, `isRegular`,
  `reference`, `page`) posted to `/api/groupSearch?size=&page=`. `/api/search` returns 503 for the
  same payload.

## 5. Files saved

- `sources/official/probes/c255_report_1er_EN.pdf` … `c255_report_7_EN.pdf` — activity reports 1–7.
- `sources/official/probes/c255_report_7_EN.txt`, `c255_report_6_EN.txt` — extracted text used for
  the tables above.
- `sources/official/probes/comite255_work_page.txt` — work page snapshot (313 / 70 / 150 / 163).
- `sources/official/probes/ST-13358-2024-INIT.pdf`, `ST-13680-2024-INIT.pdf` — Council IGC notes.
- `sources/official/probes/council_12964_26_2026_255_refusal.pdf` — 2026 refusal (Austrian mirror).
