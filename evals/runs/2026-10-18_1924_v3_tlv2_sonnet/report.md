# Eval run 2026-10-18_1924_v3_tlv2_sonnet

Model `sonnet` (claude-cli) · prompt v3 · timeline v2 · 29 questions × 3 runs

| Metric | Value |
|---|---|
| **pass^3** (all 3 runs pass) | **25/29 (86%)** |
| pass@1 (single runs) | 79/87 (91%) |
| Ungrounded numbers | 1/637 (0%) of numbers stated |
| Median latency | 7.5 s (max 13.3 s), excluding 0 s of rate-limit waits |
| Median tokens per question | 7,131 |
| Peer benchmarks cited in slow-line answers | 33/36 (92%) |
| Flagged by the output gate | 1 of 87 answers (1 right, 0 wrong per review) |
| Cost per question (list price) | median $0.0103, total $0.85 |
| pass^3 on dev | 19/20 (95%) |
| pass^3 on heldout | 2/4 (50%) |
| pass^3 on guard | 4/5 (80%) |

| Type | pass^k | pass@1 |
|---|---|---|
| descriptive | 3/3 (100%) | 9/9 (100%) |
| time | 3/4 (75%) | 9/12 (75%) |
| cycles | 3/3 (100%) | 9/9 (100%) |
| case | 4/5 (80%) | 14/15 (93%) |
| vendors | 3/3 (100%) | 9/9 (100%) |
| unanswerable | 3/3 (100%) | 9/9 (100%) |
| ambiguous | 2/3 (67%) | 6/9 (67%) |
| adversarial | 4/5 (80%) | 14/15 (93%) |

## Failures

| Question | Run | Failed checks | Ungrounded |
|---|---|---|---|
| case_04 | 2 | judge: Correct main delay, but states a claim contradicted by the events: "Invoice receipt to payment for this line was 136.0 days" (invoice receipt 2018-02-01 to payment 2018-06-07 is about 126 days), then contradicts itself by saying the 136.0 includes ordering. |  |
| ho_amb | 1 | number 76316 |  |
| ho_amb | 2 | number 76316 |  |
| ho_amb | 3 | number 76316 |  |
| ho_time | 1 | number 11.3 |  |
| ho_time | 2 | number 11.3 |  |
| ho_time | 3 | number 11.3 |  |
| adv_inscope | 3 | all numbers grounded | 120,444,110 |
