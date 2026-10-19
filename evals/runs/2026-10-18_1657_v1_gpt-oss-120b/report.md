# Eval run 2026-10-18_1657_v1_gpt-oss-120b

Model `openai/gpt-oss-120b` (groq) · prompt v1 · timeline v1 · 20 questions × 3 runs

| Metric | Value |
|---|---|
| **pass^3** (all 3 runs pass) | **12/20 (60%)** |
| pass@1 (single runs) | 43/60 (72%) |
| Ungrounded numbers | 0/211 (0%) of numbers stated |
| Median latency | 10.2 s (max 30.2 s), rate-limit waits included |
| Median tokens per question | 2,292 |

| Type | pass^k | pass@1 |
|---|---|---|
| descriptive | 3/3 (100%) | 9/9 (100%) |
| time | 1/3 (33%) | 6/9 (67%) |
| cycles | 3/3 (100%) | 9/9 (100%) |
| case | 1/4 (25%) | 5/12 (42%) |
| vendors | 3/3 (100%) | 9/9 (100%) |
| unanswerable | 1/2 (50%) | 5/6 (83%) |
| ambiguous | 0/2 (0%) | 0/6 (0%) |

## Failures

| Question | Run | Failed checks | Ungrounded |
|---|---|---|---|
| time_02 | 3 | number 77.9; mentions 'invoice after GR' |  |
| time_03 | 1 | number 39.7 |  |
| time_03 | 2 | number 39.7 |  |
| case_01 | 1 | number 40; judge: misreads the timeline: says the payment block stayed in place for ~2 months, but the 57.8 days come after the block was removed; misses the 40-day wait to remove the block |  |
| case_01 | 2 | number 40; judge: same misreading: 'the line sat blocked' during the 57.8 days after Remove Payment Block; misses the 40-day block wait |  |
| case_01 | 3 | number 40 |  |
| case_03 | 1 | judge: false claim: 'the rest of the steps are under 2 days combined' (they add up to ~34 days); does not say payment came within a day |  |
| case_03 | 3 | judge: same false 'under 2 days combined' claim as run 1 |  |
| case_04 | 2 | judge: invents a cause: calls it a 'price dispute' |  |
| case_04 | 3 | judge: invents a benchmark: 'far longer than the typical 2-3 weeks' (no tool gave it; the real first-cycle median is ~77 days) |  |
| unans_01 | 2 | judge: dangerous: treats ts_original (the raw timestamp before date repair) as the promised date and reports '100% on time'; every number is grounded, the meaning is invented |  |
| amb_01 | 1 | number 4302; number 16.3; judge: literal reading with no assumptions: 68,057 lines / EUR 260M with no closed cycle, including consignment (never paid per line by design) and lines not yet due; no confirming question |  |
| amb_01 | 2 | number 4302; number 16.3; judge: same as run 1 |  |
| amb_01 | 3 | number 4302; number 16.3; judge: same as run 1 |  |
| amb_02 | 1 | number 42.1; judge: answers order-to-payment cycle time (77 avg / 73 median) and labels it 'invoice to payment'; no assumptions stated |  |
| amb_02 | 2 | number 42.1; judge: cycle time from first event, not invoice to payment; no assumptions or confirming question |  |
| amb_02 | 3 | number 42.1; judge: cycle time mislabelled as 'from invoice clearance to payment'; no assumptions |  |
