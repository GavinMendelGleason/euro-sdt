# Missing official biographies — batch_d

No official CJEU biography text exists in the repository for these members:

- **Piotr Polak** (Poland, Judge, Court of Justice)
- **Lela Meano** (Greece, Judge, Court of Justice)
- **Mihail Visoiu** (Romania, Judge, Court of Justice)
- **Thomas Borg** (Malta, Judge, Court of Justice)
- **Dragos-Bogdan Raduletu** (Romania, Judge, Court of Justice)

For each of them, the following were checked:

- `sources/cjeu/` — no matching file (case-insensitive search for `polak`, `meano`, `voiu`, `borg`, `radul`).
- `sources/official/` — no matching `cjeu-*.txt` file.
- `grep -ril` across both directories — only unrelated incidental matches (`sources/cjeu/jesper-svenningsen.txt` contains "Aalborg"; `sources/official/volkswagen.txt` contains "Lamborghini").
- `wiki/people/` — pages exist but contain no official biography text or CJEU source URL, so they were not used.

No rows for these five members are included in `batch_d.csv`. Only official CJEU biographies may be used, so no Wikipedia, Wikidata, or news source was consulted as a substitute. `batch_d.csv` contains fragments for the other two members in the batch, Beatrix Ricziová and Maciej Szpunar.
