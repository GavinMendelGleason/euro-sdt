# Missing official biographies

No official CJEU biography text was found under `sources/official/` or `sources/cjeu/` for:

- Lyudmila Grigorova
- Ingunn Ikdahl

`audit/external_sources_needed.csv` records both with 0 available sources. No career rows for these people appear in `batch_c.csv`, and no dates or posts have been inferred.

## Name discrepancy

`data/cjeu/cjeu_members_list.csv` lists **Jiří Passer**, while `sources/official/cjeu-jiri-passer.txt` is the biography of **Jan Passer**. The rows in `batch_c.csv` use the member-list name `Jiří Passer` so that they join to the roster; role and date evidence is quoted from that file.

## Source composition

`sources/official/cjeu-marko-ilesic.txt` and `sources/official/cjeu-jiri-passer.txt` append the opening of the next member's biography. Every quote was taken from the target member's own section.
