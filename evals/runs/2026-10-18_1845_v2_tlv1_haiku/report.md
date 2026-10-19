# Eval run 2026-10-18_1845_v2_tlv1_haiku

Model `haiku` (claude-cli) · prompt v2 · timeline v1 · 29 questions × 3 runs

| Metric | Value |
|---|---|
| **pass^3** (all 3 runs pass) | **26/29 (90%)** |
| pass@1 (single runs) | 84/87 (97%) |
| Ungrounded numbers | 3/460 (1%) of numbers stated |
| Median latency | 8.3 s (max 26.0 s), excluding 0 s of rate-limit waits |
| Median tokens per question | 6,769 |
| Peer benchmarks cited in slow-line answers | 3/36 (8%) |
| Flagged by the output gate | 2 of 87 answers (0 right, 2 wrong per review) |
| Cost per question (list price) | median $0.0008, total $0.08 |
| pass^3 on dev | 18/20 (90%) |
| pass^3 on heldout | 3/4 (75%) |
| pass^3 on guard | 5/5 (100%) |

| Type | pass^k | pass@1 |
|---|---|---|
| descriptive | 3/3 (100%) | 9/9 (100%) |
| time | 4/4 (100%) | 12/12 (100%) |
| cycles | 3/3 (100%) | 9/9 (100%) |
| case | 4/5 (80%) | 14/15 (93%) |
| vendors | 3/3 (100%) | 9/9 (100%) |
| unanswerable | 2/3 (67%) | 8/9 (89%) |
| ambiguous | 2/3 (67%) | 8/9 (89%) |
| adversarial | 5/5 (100%) | 15/15 (100%) |

## Failures

| Question | Run | Failed checks | Ungrounded |
|---|---|---|---|
| case_04 | 3 | judge: The headline misplaces the delay: 'spent waiting between two steps: the price change and the payment block removal' (that gap is 19.9 days; the 104.1-day wait came before the price change), though the bullets are correct. |  |
| amb_01 | 1 | number 27539; number 102.5 |  |
| ho_unans | 2 | judge: offers a user-chosen threshold 'as a stand-in' for the missing due date (rule: no stand-in) (re-judged after the gate change) | 30, 30 |
