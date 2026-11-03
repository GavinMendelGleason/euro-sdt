# Wider eligible judicial pool for CJEU appointments

Probe of official counts for the population from which CJEU judges and advocates general are
drawn. TFEU Art. 253 and Art. 19(2) TEU require candidates to be "persons whose independence is
beyond doubt and who possess the qualifications required for appointment to the highest judicial
offices in their respective countries or who are jurisconsults of recognised competence".

No EU-wide register of that population exists. This probe measures four observable components per
member state and records coverage rather than forcing a total:

1. **Supreme court judges** — judges sitting in the highest instance, CEPEJ harmonised data.
2. **Constitutional court judges** — statutory composition of the constitutional court or
   equivalent concentrated-review body.
3. **Law professors** — full professors of law at universities, from national statistical offices
   and ministries.
4. **Senior advocates** — lawyers with a formal grade or admission to plead before the highest
   court, where such a grade exists.

All figures, URLs and per-row caveats are in `data/probes/eligible_judicial_pool.csv`
(108 rows: 27 member states × 4 measures). Saved source copies are in
`sources/official/probes/`. Nothing is estimated, and no cross-category total is computed.

## Coverage

`—` means no law-specific official figure was found; the bracketed status is the CSV status.
Values are as published, or documented in the row notes where a rounding or a broader
category applies; see the dimension notes for what each counts.

| MS | Supreme court judges (2024) | Constitutional court seats | Law professors | Senior advocates |
|---|---:|---:|---:|---:|
| AT | 135 | 14 | — [not_public] | — [not_applicable] |
| BE | 68 | 12 | — [blocked] | 17 [partial] |
| BG | 197 | 12 | — [not_public] | — [not_applicable] |
| CY | 16 | 9 | 218 [partial] | — [not_applicable] |
| CZ | 107 | 15 | — [blocked] | — [not_applicable] |
| DE | 462 | 16 | 1,193 | 43 |
| DK | 18 | — [not_applicable] | — [not_public] | — [partial] |
| EE | 19 | — [not_applicable] | — [not_public] | — [not_applicable] |
| ES | 51 | 12 | — [not_public] | — [not_applicable] |
| FI | 41 | — [not_applicable] | — [not_public] | — [not_applicable] |
| FR | 365 | 9 | 1,526 [partial] | 125 |
| GR | 419 | — [not_applicable] | — [not_public] | — [not_applicable] |
| HR | 31 | 13 | — [not_public] | — [not_applicable] |
| HU | 88 | 15 | — [not_public] | — [not_applicable] |
| IE | 9 | — [not_applicable] | — [not_public] | 362 [partial] |
| IT | 535 | 15 | 1,866 | 55,494 [partial, 2013] |
| LT | 29 | 9 | — [not_public] | — [not_applicable] |
| LU | 6 | 9 | 27 [partial] | — [not_applicable] |
| LV | 35 | 7 | — [not_public] | — [not_applicable] |
| MT | — [partial] | 3 | — [not_public] | — [not_applicable] |
| NL | 35 | — [not_applicable] | — [not_public] | — [partial] |
| PL | 210 | 15 [partial] | — [not_public] | — [not_applicable] |
| PT | 91 | 13 | — [not_public] | — [not_applicable] |
| RO | 101 | 9 | — [blocked] | — [not_applicable] |
| SE | 33 | — [not_applicable] | 107 | — [not_applicable] |
| SI | 27 | 9 | — [not_public] | — [not_applicable] |
| SK | 81 | 13 [partial] | 65 | — [not_applicable] |

Status counts: 50 found, 11 partial, 17 not_public, 3 blocked, 27 not_applicable.

## Dimension notes

### 1. Supreme court judges

Source: CEPEJ, *Study on the functioning of judicial systems in the EU Member States — Facts and
figures from the CEPEJ questionnaires 2014 to 2024*, Part 1, CEPEJ(2025)21rev, Strasbourg,
30 January 2026, Table 7.1.3 (Q46) and Table 7.1.4 (Q46-2). Data year 2024; professional judges
sitting in courts, full-time equivalent, posts actually filled.

This is the **supreme-instance column**, not the whole judiciary. For several member states it
covers both judicial orders. Table 7.1.4 shows how many of the supreme-instance judges sit in
administrative supreme courts: AT 68 of 135 (Supreme Court + Supreme Administrative Court),
DE 58 of 462 (of five federal supreme courts), FR 125 of 365 (Cour de cassation + Conseil d'État),
GR 340 of 419 (Council of State dominates), IT 156 of 535 (Consiglio di Stato), PL 114 of 210
(Supreme Court + Supreme Administrative Court since 2020), PT 31 of 91. Belgium is the exception:
CEPEJ counts Council of State judges as first instance, so its 68 is the Cour de cassation alone.
Malta reports NAP.

These are sitting judges in post, not everybody qualified for the office. Former judges, retired
judges and eligible academics/lawyers are outside the count.

### 2. Constitutional court judges

Values are **statutory seats**, fixed by constitution or founding law, not the number currently
sitting and not a measure of the wider pool of people eligible for appointment. Sources are each
court's own site or the official legal portal; the legal basis is in each row's notes.

Seven member states have no separate constitutional court: DK and SE (diffuse review; SE also has
the Lagrådet), FI (Constitutional Law Committee + s.106 review), IE, NL (Art. 120 bars review),
EE (constitutional review chamber inside the 19-justice Riigikohus) and GR (diffuse review; the
Art. 100 Special Highest Court is not a constitutional court). CY is a genuine 2023 change: the
former 13-justice Supreme Court split into a 9-justice Supreme Constitutional Court and a
7-justice Supreme Court.

Vacancies recorded from official pages: PL 10 of 15 seats filled (November 2026), SK 12 of 13
(July 2026). Values remain the statutory figures; the vacancy is in `notes`.

CEPEJ's judiciary totals generally exclude constitutional courts, so these seats are additional
to the supreme-court column and must not be added to it without deciding what "eligible" means.

### 3. Law professors

No EU-wide statistic exists. Eurostat's UOE personnel tables (`educ_uoe_perp01`, `educ_uoe_perp02`)
carry no field-of-education dimension, so they cannot produce law counts. National sources differ
in rank definitions and discipline classification, which is why most rows are blank.

Law-specific counts found:

| MS | Figure | What it counts | Year |
|---|---:|---|---|
| DE | 1,193 | tenured professors (W2/W3/C3/C4, excl. Juniorprofessoren), subject group Rechtswissenschaften, all higher-education institutions; Destatis Hochschulpersonal 2024, table 21341-18 | 2024 |
| IT | 1,866 | professori ordinari, area 12 Scienze giuridiche (all IUS/*); USTAT personnel data | 2024 |
| SK | 65 | professors at the four public law faculties in one CVTI table (UK 38, UPJŠ 9, UMB 9, TTU 9); private/state HEIs in separate tables, excluded | 2025 |
| SE | 107 | professors in research subject group Juridik, 106.93 FTE rounded; UKÄ personal statistics | 2025 |
| FR | 1,526 [partial] | professeurs des universités, CNU group 1 "Droit et science politique" — includes political science (section 04); MESR/DGRH | 2024 |
| LU | 27 [partial] | professorial staff of the University of Luxembourg law department, ranks not split | 2023 |
| CY | 218 [partial] | academic and teaching staff whose highest qualification is law, all ranks | 2023-24 |

Countries where the statistical office publishes only a broader category, so no law value is
recorded (the broader figure is in `notes`): ES (3,577 catedráticos in Ciencias Sociales y
Jurídicas, which also covers economics, business, sociology and political science), PT (4,704
teaching staff in ISCED-F 04 business/administration/law, all ranks), DK (5,741 scientific staff
in social sciences), FI (764.46 professor person-work-years in social sciences), LV (606 professors
in all fields), LT (8,773 lecturers in all fields), MT (2,826 tertiary academic staff in all
fields), GR (19,372 tertiary teaching staff in all fields).

Blocked: BE (no official discipline split; French Community portal bot-blocked), CZ (MŠMT staff
yearbook attachment served only through a client-side app), RO (INS Tempo-Online matrix-only SPA;
publications returned 503). Not public: AT, BG, HR, HU, IE, NL, PL, SI, EE — their statistical
offices publish staff by rank and/or institution, never rank × legal discipline.

### 4. Senior advocates

A formal highest-court advocate grade exists in only a few member states; 20 are `not_applicable`
because the profession is unified and any enrolled lawyer may appear before the supreme court.

| MS | Figure | What it counts | Year |
|---|---:|---|---|
| FR | 125 | avocats aux Conseils (Ordre des avocats au Conseil d'État et à la Cour de cassation); Ministère de la Justice, Références statistiques Justice 2024 | 2024 |
| DE | 43 | at the Bundesgerichtshof, singular admission; chamber's own register (BRAK recorded 37 at 1 Jan 2024) | 2026 |
| BE | 17 [partial] | avocats à la Cour de cassation, last-numbered entry of the official tableau, no published total | 2026 |
| IE | 362 [partial] | senior counsel of 2,097 Law Library members; Bar of Ireland annual report; a second panel on the same page says 364 | 2024 |
| IT | 55,494 [partial] | albo speciale dei cassazionisti; latest machine-readable national total is 2013 | 2013 |
| NL, DK | — [partial] | admission to the supreme-court bar exists, but no official headcount is published | 2026 |

## What failed

- **Belgian, Czech and Romanian law-professor counts.** Each national statistics office either
  cannot split staff by legal discipline or serves the decisive table only through an interactive
  application. Three different routes were tried per country (statistical office table, ministry
  yearbook, open-data API).
- **Austrian, Dutch, Irish, Polish, Slovenian, Hungarian, Bulgarian, Croatian and Estonian law
  professors.** No rank × discipline table is published. All-fields totals exist but are not law
  counts and were deliberately left out of the value column.
- **Spanish, Portuguese, Danish, Finnish, Latvian, Lithuanian, Maltese and Greek law professors.**
  Only broader categories are published (social sciences, or business/administration/law, or all
  fields). Figures are in `notes` as context, not as law counts.
- **Current Italian cassazionisti.** CNF's newer sheet is image-only; the 2013 total is the latest
  machine-readable official figure.
- **Dutch and Danish supreme-court bar headcounts.** Admission rules are documented, counts are not
  published.
- **Several constitutional court current-membership pages** (IT, ES, RO, SI, LV, LT) block automated
  access; statutory seat counts were still confirmed from constitutions or official legal portals.

## Context (not eligible-pool measures)

CEPEJ Table 7.7.1, total practising lawyers, 2024: AT 7,138; BE 19,430; BG 13,641; HR 5,362;
CY 4,232; CZ 13,067; DK 7,671; EE 1,154; FI 4,240; FR 73,998; DE 166,504; GR 46,204; HU 20,447;
IE 14,357; IT 223,819; LV 1,343; LT 2,313; LU 3,532; MT 1,888; NL 18,723; PL 65,038; PT 36,652;
RO 23,357; SK 6,700; SI 1,912; ES 145,013; SE 5,956.

These are entire national bars. They are not a proxy for "jurisconsults of recognised competence"
and are not in the CSV.

## How to use

- The four measures are **not additive**. Supreme-court judges are FTE posts filled; constitutional
  seats are statutory; law professors are headcounts of varying rank definitions; senior advocates
  are roll members, often stale.
- `status=partial` means a published figure exists but its category is broader or its date is old.
  The `notes` column says exactly how.
- For a defensible "highest judicial office" denominator, use supreme + constitutional as separate
  series and state the vacancy treatment (statutory vs sitting).
- For the "jurisconsult" route, only DE, IT, SK, SE, FR, LU and CY supply any law-academic count;
  the rest of the professorial pool is unmeasured in official statistics.
