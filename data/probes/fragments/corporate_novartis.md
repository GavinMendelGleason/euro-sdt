# Corporate board succession probe — Novartis AG (Switzerland)

Frame row: `Novartis,Pharma,Switzerland,3+,200,` (`data/corporate/transnational_companies.csv`).
Board = Board of Directors (Swiss one-tier board; shareholders elect each member individually at the
Annual General Meeting for a one-year term). Nomination body = the board committee named in the
governance report of each year: `Governance, Nomination and Corporate Responsibilities Committee`
(GNCRC) through 2021/22, renamed `Governance, Sustainability and Nomination Committee` (GSNC)
effective March 1, 2022.

## Sources saved (`sources/official/probes/`)

| file | document |
|---|---|
| `novartis-agm-notice-2019.pdf` … `-2025.pdf` | Invitation/convening notice to the AGM of that year (English), with the individual director resolutions and the election item |
| `novartis-agm-media-release-2019.pdf` … `-2025.pdf` | Company media release on the AGM results of that year |
| `novartis-agm-voting-results-2024.pdf`, `-2025.pdf` | Published voting results (only these two years are posted on the AGM page) |
| `novartis-annual-report-2019.pdf` … `-2025.pdf` | Annual Report / Integrated Report of that fiscal year, incl. corporate governance report and committee tables |
| `novartis-annual-report-2024-corporate-governance.pdf`, `-2025-…` | Standalone corporate governance section published for 2024 and 2025 |
| `novartis-candidate-cv-2023-background-info-john-young.pdf` | Candidate CV published ahead of the 2023 AGM |
| `novartis-candidate-cv-2025-background-info-giovanni-caforio.pdf`, `…-elizabeth-mcnally.pdf` | Candidate CVs published ahead of the 2025 AGM |

All PDFs have a `pdftotext -layout` `.txt` twin in the same directory.

## Year convention

An event is attributed to the calendar year in which the Annual General Meeting at which it happened
took place (AGMs: 28 Feb 2019, 28 Feb 2020, 2 Mar 2021, 4 Mar 2022, 7 Mar 2023, 5 Mar 2024, 7 Mar 2025).
Novartis elects its whole board every year for a one-year term ending at the next AGM, so a year's
`corporate_board_openings` is the number of individual director resolutions put to that AGM, including
re-elections. No co-option occurred in 2019-2025: every seat change went through the AGM, so no seat is
counted twice. Board-size figures below are the "Number of members" of the Board in the committee table
of that year's Annual Report, i.e. the composition as it stood after that year's AGM and at year-end.

## Board size at each year-end

| year | board size | members after that AGM |
|---|---|---|
| 2019 | 12 | Reinhardt (Chair), Andrews, Buechner, Bula, Datar, Doherty, Fudge, van Houten, von Planta, Sawyers, Vanni, Winters (Azar left, Bula joined) |
| 2020 | 14 | + Heller, Moroney |
| 2021 | 13 | − Datar |
| 2022 | 13 | − Fudge, − Vanni, + de Pro Gonzalo, + Hochstrasser |
| 2023 | 13 | − von Planta, + Young |
| 2024 | 13 | unchanged (all 13 re-elected) |
| 2025 | 12 | − Reinhardt (Chair), − Sawyers, − Winters, + Caforio (Chair), + McNally |

Counts derive from the resolutions enumerated in each convening notice and match the "Number of members"
line of the Board table (AR 2019 p. 181 = 12; AR 2020 p. 146 = 14; AR 2021 p. 142 = 13; AR 2022 p. 144 = 13;
AR 2023 p. 141 = 13; CG 2024 p. 20 = 13; CG 2025 p. 19 = 12).

## Evidence conventions

* The notices enumerate every candidate as a separate numbered resolution (`8.1`…`8.12`, `6.1`…`6.14`,
  `7.1`…`7.13` etc.); the searchable `verbatim evidence sentence` is the board's proposal sentence that
  carries the names, together with the resolution number range cited in the page column.
* No prose sentence states the nomination committee's meeting or member count in any year's report; the
  governance report discloses it only in the committee "Meetings" table. The evidence cell therefore quotes
  that table verbatim, cells in reading order separated by `|`. A trailing `1` on a name in 2019-2021 is the
  source's footnote marker.
* The CEO row is likewise a biography-table line, not prose: "… since 2018" in the Executive Committee
  biography of Vasant (Vas) Narasimhan. He was CEO from February 1, 2018 (AR 2019: "Vasant Narasimhan, CEO
  (in role since February 1, 2018)") and remained CEO throughout 2019-2025, including in the Q4 2025 results
  release; hence `corporate_ceo_changes` = 0 in every year and the Chair/CEO roles are separate persons
  (Caforio is Board Chair from 2025, Narasimhan is CEO).
* `corporate_candidate_list` = 1 in every year: the convening notice names each candidate individually
  before the vote, gives new candidates a CV paragraph in the notice itself (Bula 2019, Heller/Moroney 2020,
  de Pro Gonzalo/Hochstrasser 2022, Young 2023, Caforio/McNally 2025), and cross-references incumbents to
  the Annual Report corporate governance section (published before the AGM). For 2023 and 2025 the company
  additionally published standalone candidate "background information" PDFs, saved above.

## Table

| gap | period | value | verbatim evidence sentence | source_url | document section/page | source_file |
|---|---|---|---|---|---|---|
| corporate_board_openings | 2019 | 12 | The Board of Directors proposes the re-election of Joerg Reinhardt, Ph.D. (also as Chairman of the Board of Directors in a single vote), Nancy C. Andrews, M.D., Ph.D., Ton Buechner, Srikant Datar, Ph.D., Elizabeth Doherty, Ann Fudge, Frans van Houten, Andreas von Planta, Ph.D., Charles L. Sawyers, M.D., Enrico Vanni, Ph.D., and William T. Winters as well as the election of Patrice Bula as members of the Board of Directors, each until the end of the next Annual General Meeting. | https://www.novartis.com/sites/novartis_com/files/2019-novartis-agm-notice.pdf | Invitation to the Annual General Meeting 2019, item on elections of the Board of Directors, p. 4 | novartis-agm-notice-2019.pdf |
| corporate_board_new_members | 2019 | 1 | as well as the election of Patrice Bula as members of the Board of Directors, each until the end of the next Annual General Meeting. | https://www.novartis.com/sites/novartis_com/files/2019-novartis-agm-notice.pdf | Invitation to the Annual General Meeting 2019, item on elections of the Board of Directors, p. 4 | novartis-agm-notice-2019.pdf |
| corporate_board_departures | 2019 | 1 | Dimitri Azar, M.D. has decided not to seek another term of office. | https://www.novartis.com/sites/novartis_com/files/2019-novartis-agm-notice.pdf | Invitation to the Annual General Meeting 2019, item on elections of the Board of Directors, p. 4 | novartis-agm-notice-2019.pdf |
| corporate_candidate_list | 2019 | 1 | The Board of Directors proposes the re-election of Joerg Reinhardt, Ph.D. (also as Chairman of the Board of Directors in a single vote), Nancy C. Andrews, M.D., Ph.D., Ton Buechner, Srikant Datar, Ph.D., Elizabeth Doherty, Ann Fudge, Frans van Houten, Andreas von Planta, Ph.D., Charles L. Sawyers, M.D., Enrico Vanni, Ph.D., and William T. Winters as well as the election of Patrice Bula as members of the Board of Directors, each until the end of the next Annual General Meeting. | https://www.novartis.com/sites/novartis_com/files/2019-novartis-agm-notice.pdf | Invitation to the Annual General Meeting 2019, item on elections of the Board of Directors, p. 4 | novartis-agm-notice-2019.pdf |
| corporate_nomination_committee | 2019 | 5 | Number of meetings held 4 \| Andreas von Planta1 \| Number of members 5 \| Ann Fudge 4 | https://www.novartis.com/sites/novartis_com/files/novartis-annual-report-2019.pdf | p. 184 (committee 'Meetings' table) | novartis-annual-report-2019.pdf |
| corporate_ceo_changes | 2019 | 0 | Chief Executive Officer of Novartis since 2018 \| Nationality: American \| Year of birth: 1976 | https://www.novartis.com/sites/novartis_com/files/novartis-annual-report-2019.pdf | Executive Committee biography of Vasant (Vas) Narasimhan, p. 193 | novartis-annual-report-2019.pdf |
| corporate_board_openings | 2020 | 14 | The Board of Directors proposes the re-election of the current members of the Board of Directors (incl. the Chairman) as well as the election of Bridgette Heller and Simon Moroney as new members of the Board of Directors, each until the end of the next Annual General Meeting. | https://www.novartis.com/sites/novartis_com/files/2020-novartis-agm-notice.pdf | Invitation to the Annual General Meeting 2020, item on elections of the Board of Directors, p. 3 | novartis-agm-notice-2020.pdf |
| corporate_board_new_members | 2020 | 2 | as well as the election of Bridgette Heller and Simon Moroney as new members of the Board of Directors, each until the end of the next Annual General Meeting. | https://www.novartis.com/sites/novartis_com/files/2020-novartis-agm-notice.pdf | Invitation to the Annual General Meeting 2020, item on elections of the Board of Directors, p. 3 | novartis-agm-notice-2020.pdf |
| corporate_board_departures | 2020 | 0 | The Board of Directors proposes the re-election of the current members of the Board of Directors (incl. the Chairman) as well as the election of Bridgette Heller and Simon Moroney as new members of the Board of Directors, each until the end of the next Annual General Meeting. | https://www.novartis.com/sites/novartis_com/files/2020-novartis-agm-notice.pdf | Invitation to the Annual General Meeting 2020, item on elections of the Board of Directors, p. 3 | novartis-agm-notice-2020.pdf |
| corporate_candidate_list | 2020 | 1 | The Board of Directors proposes the re-election of the current members of the Board of Directors (incl. the Chairman) as well as the election of Bridgette Heller and Simon Moroney as new members of the Board of Directors, each until the end of the next Annual General Meeting. | https://www.novartis.com/sites/novartis_com/files/2020-novartis-agm-notice.pdf | Invitation to the Annual General Meeting 2020, item on elections of the Board of Directors, p. 3 | novartis-agm-notice-2020.pdf |
| corporate_nomination_committee | 2020 | 5 | Number of meetings held 4 \| A. von Planta (Chair) 4 \| Number of members 5 \| A. Fudge 4 | https://www.novartis.com/sites/novartis_com/files/novartis-annual-report-2020.pdf | p. 149 (committee 'Meetings' table) | novartis-annual-report-2020.pdf |
| corporate_ceo_changes | 2020 | 0 | Chief Executive Officer of Novartis since 2018 \| Nationality: American \| Year of birth: 1976 | https://www.novartis.com/sites/novartis_com/files/novartis-annual-report-2020.pdf | Executive Committee biography of Vasant (Vas) Narasimhan, p. 155 | novartis-annual-report-2020.pdf |
| corporate_board_openings | 2021 | 13 | The Board of Directors proposes the re-election of the current members of the Board of Directors (incl. the Chairman), with the exception of Srikant Datar, each until the end of the next Annual General Meeting. | https://www.novartis.com/sites/novartis_com/files/2021-novartis-agm-notice.pdf | Invitation to the Annual General Meeting 2021, item on elections of the Board of Directors, p. 4 | novartis-agm-notice-2021.pdf |
| corporate_board_new_members | 2021 | 0 | The Board of Directors proposes the re-election of the current members of the Board of Directors (incl. the Chairman), with the exception of Srikant Datar, each until the end of the next Annual General Meeting. | https://www.novartis.com/sites/novartis_com/files/2021-novartis-agm-notice.pdf | Invitation to the Annual General Meeting 2021, item on elections of the Board of Directors, p. 4 | novartis-agm-notice-2021.pdf |
| corporate_board_departures | 2021 | 1 | Following his appointment as dean of the Harvard Business School as of January 1, 2021, Srikant Datar has decided not to seek another term of office. | https://www.novartis.com/sites/novartis_com/files/2021-novartis-agm-notice.pdf | Invitation to the Annual General Meeting 2021, item on elections of the Board of Directors, p. 4 | novartis-agm-notice-2021.pdf |
| corporate_candidate_list | 2021 | 1 | The Board of Directors proposes the re-election of the current members of the Board of Directors (incl. the Chairman), with the exception of Srikant Datar, each until the end of the next Annual General Meeting. | https://www.novartis.com/sites/novartis_com/files/2021-novartis-agm-notice.pdf | Invitation to the Annual General Meeting 2021, item on elections of the Board of Directors, p. 4 | novartis-agm-notice-2021.pdf |
| corporate_nomination_committee | 2021 | 5 | Number of meetings held 3 \| A. von Planta (Chair)1 \| Number of members 5 \| A. Fudge 3 | https://www.novartis.com/sites/novartis_com/files/novartis-annual-report-2021.pdf | p. 145 (committee 'Meetings' table) | novartis-annual-report-2021.pdf |
| corporate_ceo_changes | 2021 | 0 | Chief Executive Officer of Novartis since 2018 \| Nationality: American \| Year of birth: 1976 | https://www.novartis.com/sites/novartis_com/files/novartis-annual-report-2021.pdf | Executive Committee biography of Vasant (Vas) Narasimhan, p. 151 | novartis-annual-report-2021.pdf |
| corporate_board_openings | 2022 | 13 | The Board of Directors proposes the re-election of the current members of the Board of Directors (incl. the Board Chair), with the exception of Ann Fudge and Enrico Vanni, as well as the election of Ana de Pro Gonzalo and Daniel Hochstrasser as new members of the Board of Directors, each until the end of the next Annual General Meeting. | https://www.novartis.com/sites/novartis_com/files/2022-novartis-agm-notice.pdf | Invitation to the Annual General Meeting 2022, item on elections of the Board of Directors, p. 4 | novartis-agm-notice-2022.pdf |
| corporate_board_new_members | 2022 | 2 | as well as the election of Ana de Pro Gonzalo and Daniel Hochstrasser as new members of the Board of Directors, each until the end of the next Annual General Meeting. | https://www.novartis.com/sites/novartis_com/files/2022-novartis-agm-notice.pdf | Invitation to the Annual General Meeting 2022, item on elections of the Board of Directors, p. 4 | novartis-agm-notice-2022.pdf |
| corporate_board_departures | 2022 | 2 | Ann Fudge and Enrico Vanni have decided to retire from the Board of Directors. | https://www.novartis.com/sites/novartis_com/files/2022-novartis-agm-notice.pdf | Invitation to the Annual General Meeting 2022, item on elections of the Board of Directors, p. 4 | novartis-agm-notice-2022.pdf |
| corporate_candidate_list | 2022 | 1 | The Board of Directors proposes the re-election of the current members of the Board of Directors (incl. the Board Chair), with the exception of Ann Fudge and Enrico Vanni, as well as the election of Ana de Pro Gonzalo and Daniel Hochstrasser as new members of the Board of Directors, each until the end of the next Annual General Meeting. | https://www.novartis.com/sites/novartis_com/files/2022-novartis-agm-notice.pdf | Invitation to the Annual General Meeting 2022, item on elections of the Board of Directors, p. 4 | novartis-agm-notice-2022.pdf |
| corporate_nomination_committee | 2022 | 5 | Number of meetings held 3 \| P. Bula (Chair) 3 \| Number of members 5 \| B. Heller 3 | https://www.novartis.com/sites/novartis_com/files/novartis-annual-report-2022.pdf | p. 147 (committee 'Meetings' table) | novartis-annual-report-2022.pdf |
| corporate_ceo_changes | 2022 | 0 | Chief Executive Officer of Novartis since 2018 \| Nationality: American \| Year of birth: 1976 | https://www.novartis.com/sites/novartis_com/files/novartis-annual-report-2022.pdf | Executive Committee biography of Vasant (Vas) Narasimhan, p. 153 | novartis-annual-report-2022.pdf |
| corporate_board_openings | 2023 | 13 | The Board of Directors proposes the re-election of the current members of the Board of Directors (incl. the Board Chair), with the exception of Andreas von Planta, as well as the election of John D. Young as a new member of the Board of Directors, each until the end of the next Annual General Meeting. | https://www.novartis.com/sites/novartis_com/files/2023-novartis-agm-notice.pdf | Invitation to the Annual General Meeting 2023, item on elections of the Board of Directors, p. 4 | novartis-agm-notice-2023.pdf |
| corporate_board_new_members | 2023 | 1 | as well as the election of John D. Young as a new member of the Board of Directors, each until the end of the next Annual General Meeting. | https://www.novartis.com/sites/novartis_com/files/2023-novartis-agm-notice.pdf | Invitation to the Annual General Meeting 2023, item on elections of the Board of Directors, p. 4 | novartis-agm-notice-2023.pdf |
| corporate_board_departures | 2023 | 1 | Andreas von Planta has decided not to stand for re-election. | https://www.novartis.com/sites/novartis_com/files/2023-novartis-agm-notice.pdf | Invitation to the Annual General Meeting 2023, item on elections of the Board of Directors, p. 4 | novartis-agm-notice-2023.pdf |
| corporate_candidate_list | 2023 | 1 | The Board of Directors proposes the re-election of the current members of the Board of Directors (incl. the Board Chair), with the exception of Andreas von Planta, as well as the election of John D. Young as a new member of the Board of Directors, each until the end of the next Annual General Meeting. | https://www.novartis.com/sites/novartis_com/files/2023-novartis-agm-notice.pdf | Invitation to the Annual General Meeting 2023, item on elections of the Board of Directors, p. 4 | novartis-agm-notice-2023.pdf |
| corporate_nomination_committee | 2023 | 5 | Number of meetings held 4 \| P. Bula (Chair) 4 \| Number of members 5 \| B. Heller 4 | https://www.novartis.com/sites/novartis_com/files/novartis-annual-report-2023.pdf | p. 144 (committee 'Meetings' table) | novartis-annual-report-2023.pdf |
| corporate_ceo_changes | 2023 | 0 | Chief Executive Officer of Novartis since 2018 \| Nationality: American \| Year of birth: 1976 | https://www.novartis.com/sites/novartis_com/files/novartis-annual-report-2023.pdf | Executive Committee biography of Vasant (Vas) Narasimhan, p. 150 | novartis-annual-report-2023.pdf |
| corporate_board_openings | 2024 | 13 | The Board of Directors proposes the re-election of the current members of the Board of Directors (incl. the Board Chair), each until the end of the next Annual General Meeting. | https://www.novartis.com/sites/novartis_com/files/2024-novartis-agm-notice.pdf | Invitation to the Annual General Meeting 2024, item on elections of the Board of Directors, p. 4 | novartis-agm-notice-2024.pdf |
| corporate_board_new_members | 2024 | 0 | The Board of Directors proposes the re-election of the current members of the Board of Directors (incl. the Board Chair), each until the end of the next Annual General Meeting. | https://www.novartis.com/sites/novartis_com/files/2024-novartis-agm-notice.pdf | Invitation to the Annual General Meeting 2024, item on elections of the Board of Directors, p. 4 | novartis-agm-notice-2024.pdf |
| corporate_board_departures | 2024 | 0 | The Board of Directors proposes the re-election of the current members of the Board of Directors (incl. the Board Chair), each until the end of the next Annual General Meeting. | https://www.novartis.com/sites/novartis_com/files/2024-novartis-agm-notice.pdf | Invitation to the Annual General Meeting 2024, item on elections of the Board of Directors, p. 4 | novartis-agm-notice-2024.pdf |
| corporate_candidate_list | 2024 | 1 | The Board of Directors proposes the re-election of the current members of the Board of Directors (incl. the Board Chair), each until the end of the next Annual General Meeting. | https://www.novartis.com/sites/novartis_com/files/2024-novartis-agm-notice.pdf | Invitation to the Annual General Meeting 2024, item on elections of the Board of Directors, p. 4 | novartis-agm-notice-2024.pdf |
| corporate_nomination_committee | 2024 | 5 | Number of meetings held 4 \| P. Bula (Chair) 4 \| Number of members 5 \| B. Heller 4 | https://www.novartis.com/sites/novartis_com/files/novartis-annual-report-2024-corporate-governance.pdf | p. 23 (committee 'Meetings' table) | novartis-annual-report-2024-corporate-governance.pdf |
| corporate_ceo_changes | 2024 | 0 | Chief Executive Officer since 2018 \| Nationality: American \| Year of birth: 1976 | https://www.novartis.com/sites/novartis_com/files/novartis-annual-report-2024.pdf | Executive Committee biography of Vasant (Vas) Narasimhan, p. 128 | novartis-annual-report-2024.pdf |
| corporate_board_openings | 2025 | 12 | The Board of Directors proposes the election of Giovanni Caforio as member of the Board of Directors and Board Chair, the re-election of the current members of the Board of Directors with the exception of Joerg Reinhardt, Charles L. Sawyers, and William T. Winters, and the election of Elizabeth McNally as new member of the Board of Directors, each until the end of the next Annual General Meeting. | https://www.novartis.com/sites/novartis_com/files/2025-novartis-agm-notice.pdf | Invitation to the Annual General Meeting 2025, item on elections of the Board of Directors, p. 4 | novartis-agm-notice-2025.pdf |
| corporate_board_new_members | 2025 | 2 | the election of Elizabeth McNally as new member of the Board of Directors, each until the end of the next Annual General Meeting. | https://www.novartis.com/sites/novartis_com/files/2025-novartis-agm-notice.pdf | Invitation to the Annual General Meeting 2025, item on elections of the Board of Directors, p. 4 | novartis-agm-notice-2025.pdf |
| corporate_board_departures | 2025 | 3 | Joerg Reinhardt, Charles L. Sawyers, and William T. Winters are not standing for re-election. | https://www.novartis.com/sites/novartis_com/files/2025-novartis-agm-notice.pdf | Invitation to the Annual General Meeting 2025, item on elections of the Board of Directors, p. 4 | novartis-agm-notice-2025.pdf |
| corporate_candidate_list | 2025 | 1 | The Board of Directors proposes the election of Giovanni Caforio as member of the Board of Directors and Board Chair, the re-election of the current members of the Board of Directors with the exception of Joerg Reinhardt, Charles L. Sawyers, and William T. Winters, and the election of Elizabeth McNally as new member of the Board of Directors, each until the end of the next Annual General Meeting. | https://www.novartis.com/sites/novartis_com/files/2025-novartis-agm-notice.pdf | Invitation to the Annual General Meeting 2025, item on elections of the Board of Directors, p. 4 | novartis-agm-notice-2025.pdf |
| corporate_nomination_committee | 2025 | 4 | Number of meetings held 3 \| P. Bula (Chair) 3 \| Number of members 4 \| B. Heller 3 | https://www.novartis.com/sites/novartis_com/files/novartis-annual-report-2025-corporate-governance.pdf | p. 22 (committee 'Meetings' table) | novartis-annual-report-2025-corporate-governance.pdf |
| corporate_ceo_changes | 2025 | 0 | Chief Executive Officer since 2018 \| Nationality: American \| Year of birth: 1976 | https://www.novartis.com/sites/novartis_com/files/novartis-annual-report-2025.pdf | Executive Committee biography of Vasant (Vas) Narasimhan, p. 129 | novartis-annual-report-2025.pdf |

## Notes

* Chair transition: Joerg Reinhardt was Board Chair from 2013 and did not stand for re-election at the
  2025 AGM (7 March 2025), where Giovanni Caforio was elected member and Board Chair. The 2023 chair
  transition suggested in the assignment did not happen: Reinhardt was re-elected as Board Chair at the
  2023 AGM and again at the 2024 AGM.
* Committee renaming: the board amended the Board Regulations effective March 1, 2022 and renamed the
  Governance, Nomination and Corporate Responsibilities Committee to the Governance, Sustainability and
  Nomination Committee (AR 2022, p. 127: "the Board … renamed the Governance, Nomination and Corporate
  Responsibilities Committee to the Governance, Sustainability and Nomination Committee (GSNC)"). The
  chair changed from Andreas von Planta to Patrice Bula at the 2022 AGM; the 2025 committee has four
  members (Bula, Heller, Hochstrasser, van Houten) against five in 2022-2024.
* Independent proxy / auditor resolutions and Compensation Committee elections are not board seats and
  are excluded from `corporate_board_openings`.
* 2020 and 2024 had no departures; the notice text states that all current members stood for re-election,
  and the enumerated resolutions cover the full board (12 + 2 in 2020, 13 in 2024), so 0 is a stated
  finding, not a board-size inference.

## Failed URL attempts

* `https://www.novartis.com/investors/financial-data/annual-reports` — HTTP 404 (annual reports are served
  from the reporting archive and under `/sites/novartis_com/files/`).
* `https://www.novartis.com/sites/novartis_com/files/2019..2023-novartis-agm-invitation.pdf` — HTTP 200 but
  the files are the **French** invitation ("Invitation à l'Assemblée générale ordinaire"); the English
  version is published as `…-agm-notice.pdf` and was used instead (both fetched, French versions discarded).
* `…/<year>-novartis-agm-invitation-en.pdf` for 2019-2023 — HTTP 404.
* `https://www.novartis.com/sites/novartis_com/files/novartis-annual-report-<2019..2023>-corporate-governance.pdf`
  — HTTP 404; standalone corporate governance PDFs exist only for 2024 and 2025, so 2019-2023 committee
  data comes from the corporate governance report inside the annual report PDF.
* `https://www.novartis.com/news/media-releases?search=…` — HTTP 404 (no site search endpoint at that path);
  not needed, the AGM microsite lists every document used here.
