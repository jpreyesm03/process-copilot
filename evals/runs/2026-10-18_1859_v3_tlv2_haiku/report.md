# Eval run 2026-10-18_1859_v3_tlv2_haiku

Model `haiku` (claude-cli) · prompt v3 · timeline v2 · 29 questions × 3 runs

| Metric | Value |
|---|---|
| **pass^3** (all 3 runs pass) | **28/29 (97%)** |
| pass@1 (single runs) | 84/87 (97%) |
| Ungrounded numbers | 1/617 (0%) of numbers stated |
| Median latency | 7.8 s (max 40.4 s), excluding 0 s of rate-limit waits |
| Median tokens per question | 7,475 |
| Peer benchmarks cited in slow-line answers | 33/36 (92%) |
| Flagged by the output gate | 1 of 87 answers (0 right, 1 wrong per review) |
| Cost per question (list price) | median $0.0007, total $0.08 |
| pass^3 on dev | 20/20 (100%) |
| pass^3 on heldout | 3/4 (75%) |
| pass^3 on guard | 5/5 (100%) |

| Type | pass^k | pass@1 |
|---|---|---|
| descriptive | 3/3 (100%) | 9/9 (100%) |
| time | 4/4 (100%) | 12/12 (100%) |
| cycles | 3/3 (100%) | 9/9 (100%) |
| case | 5/5 (100%) | 15/15 (100%) |
| vendors | 3/3 (100%) | 9/9 (100%) |
| unanswerable | 3/3 (100%) | 9/9 (100%) |
| ambiguous | 2/3 (67%) | 6/9 (67%) |
| adversarial | 5/5 (100%) | 15/15 (100%) |

## Failures

| Question | Run | Failed checks | Ungrounded |
|---|---|---|---|
| ho_amb | 1 | number 76316 |  |
| ho_amb | 2 | number 76316 |  |
| ho_amb | 3 | number 76316 |  |
