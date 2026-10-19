# Data

`bpi2019_events.csv.gz` is the BPI Challenge 2019 event log converted from XES to CSV by `scripts/parse_xes.py`
(one row per event, trace attributes repeated on each event, column names normalised and an event_id added; no rows removed and no values changed). The cleaning rules
(date repair, identical rows, cycles) are applied later by `process_copilot.build_db` and are documented in DECISIONS.md.

**Source:** van Dongen, Boudewijn (2019): BPI Challenge 2019. Version 1. 4TU.ResearchData. dataset.
https://doi.org/10.4121/uuid:d06aff4b-79f0-45e6-8ec8-e19730c248f1

**Licence:** [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). Changes: format conversion (XES → CSV), column renaming and an added event_id.

It is committed so the demo app can build its warehouse on a fresh server; generated data (`data/`) stays out of git.
