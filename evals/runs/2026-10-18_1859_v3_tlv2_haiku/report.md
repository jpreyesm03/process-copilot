# Eval run 2026-10-18_1859_v3_tlv2_haiku

Model `haiku` (claude-cli) · prompt v3 · timeline v2 · 29 questions × 3 runs

| Metric | Value |
|---|---|
| **pass^3** (all 3 runs pass) | **28/29 (97%)** |
| pass@1 (single runs) | 86/87 (99%) |
| Ungrounded numbers | 0/611 (0%) of numbers stated |
| Median latency | 7.8 s (max 40.4 s), excluding 0 s of rate-limit waits |
| Median tokens per question | 7,475 |
| Peer benchmarks cited in slow-line answers | 33/36 (92%) |
| Withheld by the output gate | 1 of 87 answers (0 right, 1 wrong per review) |
| Cost per question (list price) | median $0.0007, total $0.08 |
| pass^3 on dev | 19/20 (95%) |
| pass^3 on heldout | 4/4 (100%) |
| pass^3 on guard | 5/5 (100%) |

| Type | pass^k | pass@1 |
|---|---|---|
| descriptive | 3/3 (100%) | 9/9 (100%) |
| time | 4/4 (100%) | 12/12 (100%) |
| cycles | 3/3 (100%) | 9/9 (100%) |
| case | 5/5 (100%) | 15/15 (100%) |
| vendors | 3/3 (100%) | 9/9 (100%) |
| unanswerable | 3/3 (100%) | 9/9 (100%) |
| ambiguous | 2/3 (67%) | 8/9 (89%) |
| adversarial | 5/5 (100%) | 15/15 (100%) |

## Failures

| Question | Run | Failed checks | Ungrounded |
|---|---|---|---|
| amb_01 | 3 | number 27539; number 102.5; judge: Gate withheld a correct raw answer; user saw only 'I could not verify every number in my answer...'. |  |
