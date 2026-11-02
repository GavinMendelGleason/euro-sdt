# batch_a: unavailable programme-level cohort data

Institutions in this batch: College of Europe (all programmes; Natolin EIS), INSP / former ENA (formation initiale, voie générale and voie Orient).

`batch_a.csv` contains only figures printed explicitly in official institutional publications. Everything below was checked against the institutions' own reports and pages and either is not published at programme level or is published only as a range or a capacity figure that is not an admission count.

## College of Europe

No annual programme-level series of applicants, admissions or graduates for 2019-2025 was found.

- **Applicants**: the Rector's 2020-2025 mandate report states only that submitted applications have been "above the threshold of 2000" since 2021 and that the 2024 admission cycle was "a new record". No annual integer is printed, so no applicant row is written. The application chart (Fig. 2) has no data labels.
- **Admissions**: no annual admitted count is published. The only programme-level admitted table located is `number_of_admitted_students_by_nationality_2018-2019.pdf` (saved as `sources/official/institutions/college-of-europe-admitted-students-2018-2019.txt`), which is for academic year 2018-19 (outside the 2019-2025 window). Its own totals are ECO 16, EEIB 17, IRD 95, LAW 115, POL 88, EIS 137; Bruges 331, Natolin 137, grand total 468. It is not entered because its year is 2018, not 2019.
- **Enrolment**: the mandate report gives only a combined range of 460-476 for 2020-21 to 2024-25, plus the exact 2024-25 total of 496. The range is not converted into annual values. The 2024 College-wide total is recorded; it includes the European General Studies Programme and the first 32 ETI students in Tirana. The Natolin 2009-2019 activity report gives 133 EIS students in 2019/20 and 137 in 2018/19; only the 2019/20 EIS figure is recorded, as one programme rather than the whole College.
- **Graduates**: not published in the mandate report or the Natolin activity report. No annual graduate count was located.
- The College's "General facts and figures" page gives rounded 2024 campus figures (340 Bruges, 120 Natolin, 32 Tirana; 492 in total), which do not match the 496 total in the Rector's report. They are not used.

## INSP / former ENA — formation initiale

### Applicants

The applicant series is complete for 2019-2025, but the 2022 value needs a source caveat.

- 2019: 1,518 (2018 concours, ENA *Rapport d'activité 2019*).
- 2020: 1,731 (2019 concours, ENA *Rapport d'activité 2019*). The 2020 report later printed 1,735 for the same concours; the annual report for the year is used and the discrepancy is noted in the row.
- 2021: 1,775 (2020 concours, ENA *Rapport d'activité 2020*).
- 2022: 1,769 (2021 concours). The only located source is the official ENA *Plan de transformation de l'ENA: bilan 2018-2021*, which is an ENA document reposted by the alumni association, not an annual report. The row flags this.
- 2023: 1,956 (2022 concours, INSP *Les concours en chiffres*).
- 2024: 2,128 (2023 concours, INSP *Les concours en chiffres*).
- 2025: 2,831 voie générale and 367 voie Orient (2025 concours, INSP *Les concours en chiffres*). These are the second 2025 cohort (Missak et Mélinée Manouchian); the page's combined total of 3,198 is the sum of the two voies and is not entered as a single cohort.

### Admissions

- 2019-2021 are the years with an explicit admission count in an annual report: 80 élèves reçus aux concours for the 2019-2020 promotion (2018 concours), 83 admitted for the 2019 concours (2020-2021 promotion), and 83 places pourvues for the 2020 concours (2021-2022 promotion).
- For 2022-2025 the official sources print **places offertes**, not admissions: 89 (2021 concours), 90 (2022), 90 (2023), 60 (2024), 60 voie générale + 8 voie Orient (2025). These are capacity figures and are recorded only in the notes, not in `admitted`.
- No annual "offers made" or "candidates admitted" total was located for 2022-2025. The jury reports for those sessions were not published at the INSP resource paths checked; the 2026 jury report is the earliest one retrievable.

### Enrolment

- 2019: 80 (2019-2020 promotion; the 2020 report later counts 78 concours students in January 2020).
- 2020: 82 (2020-2021 promotion).
- 2021: 84 (2021-2022 promotion, INSP *Rapport d'activité 2022*).
- 2022: 90 (2022-2023 promotion, INSP *Rapport d'activité 2022*).
- 2023: no count printed. The INSP reports describe the entry but do not state the number of new élèves.
- 2024: 89 (2024-2026 promotion, INSP *Rapport d'activité 2024*).
- 2025 A: 61 (2025-2027 A promotion, INSP *Rapport d'activité 2024*). Only the 61 concours students are recorded.
- 2025, second cohort (Missak et Mélinée Manouchian): no count printed for the voie générale or the voie Orient cohort.

### Graduates

Not published in the annual reports. The reports announce the sortie ceremonies (Germaine Tillion in 2022, Guillaume Apollinaire in 2023, Joséphine Baker in 2024, Paul-Émile Victor in 2025) but give no number of graduates. No stated graduate total was found.

## What is usable for production-versus-intake analysis

- College of Europe: 2024 total enrolment (496); 2019 Natolin EIS enrolment (133). No admissions, applicants or graduates.
- INSP/ENA: applicants for every cohort 2019-2025; admissions for 2019-2021; enrolment for 2019-2022, 2024 and 2025 A; no graduate counts.
