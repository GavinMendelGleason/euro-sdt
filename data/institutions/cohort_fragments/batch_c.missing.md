# batch_c: unavailable programme-level cohort data

Institutions in this batch: École Polytechnique (cycle ingénieur), Université catholique de Louvain (Faculté de droit et de criminologie), Vilnius University (Faculty of Law), University of Cologne (Rechtswissenschaftliche Fakultät).

`batch_c.csv` contains only figures printed explicitly in official institutional publications. Everything below was checked against the institutions' own pages and reports and either is not published at programme level or is published only in a form that cannot be converted into an annual integer.

## École Polytechnique — cycle ingénieur

The concours booklets (`sources/official/institutions/ecole-polytechnique-concours-YYYY.txt`) give, by voie, registered candidates, admission lists and entrants. The two voies are kept as separate rows and never summed.

- **2019**: not published on the current statistics page (https://www.polytechnique.edu/admission-cycle-ingenieur/statistiques), which offers the 2020–2026 booklets only. No archived 2019 booklet was retrievable (the site's pre-2025 statistics paths are not in the Internet Archive; 2 Nov 2026). The row is omitted rather than reconstructed from SCEI concours totals, which mix X and ENS.
- **Graduates**: the concours report publishes no graduate count, and no annual official count of engineering diplomas awarded by the cycle ingénieur was located on polytechnique.edu. The Légifrance lists of "ingénieurs diplômés" would give it but were behind a JavaScript challenge at retrieval. The `graduates` column is therefore blank for every Polytechnique row.
- 2026 entrants are published (Livret_Stats_19_10_26) but fall outside the requested 2019–2025 window and are not written.

## Université catholique de Louvain — Faculté de droit et de criminologie

No public programme- or faculty-level series of applicants, admissions, enrolment or graduates was found.

- The University's figures page (https://uclouvain.be/fr/universite/chiffres, saved as `universite-catholique-de-louvain-university-figures-page.txt`) reports only **whole-university** stock: "38 500 étudiant·es", split by campus, plus staff and research totals. It gives no faculty, programme, intake or graduate counts. The whole-university figure is not a law cohort and is not used.
- The faculty's own pages (https://uclouvain.be/fr/facultes/drt/a-propos, `/presentation`, `/rentree-academique`), the annual-report pages (https://uclouvain.be/fr/rapport-annuel, https://www.uclouvain.be/fr/presse/rapport-annuel-de-l-uclouvain) and the 2023-24 student guide (`Guide de l'étudiant·e en droit`) publish no enrolment, intake or graduate numbers.
- The annual report is distributed as a JavaScript flipbook (`fliphtml5.com/cycx/duwx`) whose page data are not machine-readable without executing the viewer; no downloadable PDF was exposed.
- The Wallonia-Brussels Federation statistical yearbook, which does break university enrolment down by establishment and field ("sciences juridiques"), was not reachable: `enseignement.be` and `ares-ac.be` returned bot-protection pages (403 / "Requête non autorisée") on 2 Nov 2026.
- No row is written for UCLouvain.

## Vilnius University — Faculty of Law

Only the 2025 main-admission report is available at programme level; it is recorded in `batch_c.csv`.

- **2019–2024**: no per-programme admission counts were published in the faculty's news or pages. The University's activity reports (`vu.lt/uploads/...veiklos_ataskaita...`) publish admissions, enrolment and graduates only **university-wide** (e.g. 7,584 admitted across all programmes in 2025), which is not a law cohort and is not used.
- **Enrolment and graduates**: the faculty publishes neither the number of contracts signed after the 2025 invitations nor any graduate count. VU reports graduates only university-wide.
- The Ministry of Education's per-programme tables ("Priimtų studentų skaičius ... į VF vietas") give state-funded admissions by programme code, but `smsm.lrv.lt` and `lrv.lt` refused downloads (403) on 2 Nov 2026, and they cover state-funded places only, not total enrolment.
- Law at VU is a five-year integrated programme; the separate part-time "Teisė MAN" stream is not covered by the 2025 figure and is not mixed in.

## University of Cologne — Rechtswissenschaftliche Fakultät

- **Applicants and admitted**: not published. The *Zahlen | Daten | Fakten* reports give no application or admission counts by programme (Cologne's law admission is not a published NC statistic), so both columns are blank.
- **2025**: the 2024 edition (published June 2026) is the most recent; no ZDF 2025 exists yet.
- **Programme boundary**: `batch_c.csv` uses the Staatsexamen track ("1. Prüfung Rechtswissenschaften") for both intake and graduates. The Lehreinheit Rechtswissenschaft also contains Bachelor and Master law degrees (notably for international graduates), whose 1. FS totals are larger (e.g. 1,076 in SJ 2019 vs 837 in the Staatsexamen track). Those faculty-level totals are not substituted for the programme series.
- **2019 graduates** are taken from the 2021 report (PJ 2019 = 484), because the 2024 report's graduate series starts at PJ 2020.

## What is usable for production-versus-intake analysis

- École Polytechnique: registered candidates, admission-list places and entrants for the French and international voies, 2020–2025 (no graduates, no 2019).
- University of Cologne: Staatsexamen intake (1. FS) and first-state-exam graduates, 2019–2024.
- Vilnius University: 2025 first-choice applicants and invitations to study for the integrated Law programme (no enrolment, no graduates).
- UCLouvain: nothing at programme or faculty level.
