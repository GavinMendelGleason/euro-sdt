# Model-run manifest

| Role | Model | Source |
|---|---|---|
| Extraction and adjudication recorded in the audited database | `deepseek-chat` | `run` table |
| Grade-C second judge | `deepseek-flash`, thinking enabled | `audit/grade_c_recheck.md` |
| Grade-A recheck | `deepseek-flash`, thinking enabled | `audit/grade_a_recheck.md` |

Prompt text, cache keys and per-run parameters are kept in the implementation and cache files. Model agreement is an acceptance rule, not an independence or accuracy estimate. Re-running extraction or adjudication may call an external API and can produce different outputs.
