# Eval run 2026-10-18_1822_v2_tlv2_haiku

Model `haiku` (claude-cli) · prompt v2 · timeline v2 · 29 questions × 3 runs

| Metric | Value |
|---|---|
| **pass^3** (all 3 runs pass) | **24/29 (83%)** |
| pass@1 (single runs) | 80/87 (92%) |
| Ungrounded numbers | 6/619 (1%) of numbers stated |
| Median latency | 8.2 s (max 15.3 s), excluding 0 s of rate-limit waits |
| Median tokens per question | 6,943 |
| Peer benchmarks cited in slow-line answers | 32/36 (89%) |
| Flagged by the output gate | 4 of 87 answers (1 right, 3 wrong per review) |
| Cost per question (list price) | median $0.0008, total $0.07 |
| pass^3 on dev | 16/20 (80%) |
| pass^3 on heldout | 3/4 (75%) |
| pass^3 on guard | 5/5 (100%) |

| Type | pass^k | pass@1 |
|---|---|---|
| descriptive | 2/3 (67%) | 8/9 (89%) |
| time | 4/4 (100%) | 12/12 (100%) |
| cycles | 3/3 (100%) | 9/9 (100%) |
| case | 3/5 (60%) | 13/15 (87%) |
| vendors | 3/3 (100%) | 9/9 (100%) |
| unanswerable | 3/3 (100%) | 9/9 (100%) |
| ambiguous | 1/3 (33%) | 5/9 (56%) |
| adversarial | 5/5 (100%) | 15/15 (100%) |

## Failures

| Question | Run | Failed checks | Ungrounded |
|---|---|---|---|
| desc_01 | 2 | all numbers grounded | 250,734, 99.2%, 250,734 |
| case_02 | 2 | judge: 'Earlier waits were longer than typical' is contradicted by its own tool result: the first wait (15.0 d) is at the vendor's 18th percentile (override) |  |
| case_03 | 3 | judge: Names the 113.1-day wait but never says that payment came 0.8 days after the invoice was recorded (rule: notes fast payment after recording). |  |
| amb_01 | 3 | number 27539; number 102.5 |  |
| ho_amb | 1 | number 76316 |  |
| ho_amb | 2 | number 76316 |  |
| ho_amb | 3 | number 76316 |  |
