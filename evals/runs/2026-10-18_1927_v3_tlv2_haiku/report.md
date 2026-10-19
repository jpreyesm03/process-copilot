# Eval run 2026-10-18_1927_v3_tlv2_haiku

Model `haiku` (claude-cli) · prompt v3 · timeline v2 · 8 questions × 3 runs

| Metric | Value |
|---|---|
| **pass^3** (all 3 runs pass) | **7/8 (88%)** |
| pass@1 (single runs) | 23/24 (96%) |
| Ungrounded numbers | 0/161 (0%) of numbers stated |
| Median latency | 9.2 s (max 14.3 s), excluding 0 s of rate-limit waits |
| Median tokens per question | 7,819 |
| Flagged by the output gate | 0 of 24 answers |
| Cost per question (list price) | median $0.0009, total $0.02 |

| Type | pass^k | pass@1 |
|---|---|---|
| descriptive | 2/2 (100%) | 6/6 (100%) |
| time | 1/2 (50%) | 5/6 (83%) |
| vendors | 1/1 (100%) | 3/3 (100%) |
| ambiguous | 1/1 (100%) | 3/3 (100%) |
| unanswerable | 1/1 (100%) | 3/3 (100%) |
| case | 1/1 (100%) | 3/3 (100%) |

## Failures

| Question | Run | Failed checks | Ungrounded |
|---|---|---|---|
| h2_po_to_gr | 3 | number 10 |  |
