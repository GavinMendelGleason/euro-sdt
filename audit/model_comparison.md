# Model Comparison

Claims: 128. Models: `deepseek-chat`, `deepseek-flash` (thinking disabled), `deepseek-flash` (thinking enabled). Same prompt and evidence for every model.

## Agreement

| Pair | Agreement | Valid | Rate |
|---|---:|---:|---:|
| chat_vs_flash | 126 | 128 | 98.4% |
| chat_vs_flash_reasoning | 97 | 128 | 75.8% |
| flash_vs_flash_reasoning | 95 | 128 | 74.2% |

## By predicate

| Predicate | Claims | Chat/Flash agree | Chat supported | Flash supported |
|---|---:|---:|---:|---:|
| advisory_board | 8 | 8 | 7 | 7 |
| affiliated_with | 8 | 8 | 6 | 6 |
| attendee | 8 | 6 | 5 | 7 |
| board_member | 8 | 8 | 7 | 7 |
| chair | 8 | 8 | 6 | 6 |
| educated_at | 8 | 8 | 6 | 6 |
| employed_by | 8 | 8 | 7 | 7 |
| fellow | 8 | 8 | 7 | 7 |
| founder | 8 | 8 | 6 | 6 |
| from_country | 8 | 8 | 5 | 5 |
| held_portfolio | 8 | 8 | 6 | 6 |
| held_position | 8 | 8 | 7 | 7 |
| member | 8 | 8 | 8 | 8 |
| nominated_by | 8 | 8 | 2 | 2 |
| post_mandate_occupation | 8 | 8 | 0 | 0 |
| served_on_commission | 8 | 8 | 2 | 2 |

## Disagreements (chat vs flash)

- **Sari Essayah — attendee — Christian Democrats' Parliamentary group** (grade A, current verified)
  - chat: UNSUPPORTED — The quote states Essayah was chosen as vice speaker of the Christian Democrats' Parliamentary group, which is a leadership role, not attendance at a meeting or event.
  - flash: SUPPORTED — The quote states Essayah was chosen vice speaker of the Christian Democrats' Parliamentary group, directly entailing she attended/participated in that group's role.
- **Pál Schmitt — attendee — Hungarian Parliament** (grade A, current verified)
  - chat: UNSUPPORTED — The quote states Schmitt was speaker of the Hungarian Parliament, which is a role/position, not that he attended a meeting or event of the organisation.
  - flash: SUPPORTED — The quote states Schmitt was the speaker of the Hungarian Parliament, which directly entails he attended/participated in that body's meetings as speaker.