# Eval run 2026-10-18_1834_v1_tlv1_haiku

Model `haiku` (claude-cli) · prompt v1 · timeline v1 · 29 questions × 3 runs

| Metric | Value |
|---|---|
| **pass^3** (all 3 runs pass) | **21/29 (72%)** |
| pass@1 (single runs) | 68/87 (78%) |
| Ungrounded numbers | 13/543 (2%) of numbers stated |
| Median latency | 7.2 s (max 19.1 s), excluding 0 s of rate-limit waits |
| Median tokens per question | 5,314 |
| Peer benchmarks cited in slow-line answers | 3/36 (8%) |
| Flagged by the output gate | 4 of 87 answers (4 right, 0 wrong per review) |
| Cost per question (list price) | median $0.0007, total $0.06 |
| pass^3 on dev | 16/20 (80%) |
| pass^3 on heldout | 2/4 (50%) |
| pass^3 on guard | 3/5 (60%) |

| Type | pass^k | pass@1 |
|---|---|---|
| descriptive | 3/3 (100%) | 9/9 (100%) |
| time | 3/4 (75%) | 10/12 (83%) |
| cycles | 3/3 (100%) | 9/9 (100%) |
| case | 3/5 (60%) | 13/15 (87%) |
| vendors | 3/3 (100%) | 9/9 (100%) |
| unanswerable | 3/3 (100%) | 9/9 (100%) |
| ambiguous | 0/3 (0%) | 0/9 (0%) |
| adversarial | 3/5 (60%) | 9/15 (60%) |

## Failures

| Question | Run | Failed checks | Ungrounded |
|---|---|---|---|
| case_01 | 2 | judge: Attributes the invoice wait without evidence: "This was the vendor's delay, not an internal one" (no promised dates in the data). |  |
| case_02 | 1 | judge: Names the 86.7-day gap correctly, but the date contradicts the events: "recorded on 2026-04-26" (the event is 2018-04-26). |  |
| amb_01 | 1 | number 27539; number 102.5; judge: States the reading (no closed cycle, ordered value) but asks no confirming question. |  |
| amb_01 | 2 | number 27539; number 102.5; judge: States the reading (no closed cycle, consignment excluded) but suggests no confirming question. |  |
| amb_01 | 3 | number 27539; number 102.5; judge: States the reading ("Unpaid here means the line has no closed payment cycle") but asks no confirming question. |  |
| amb_02 | 1 | number 42.1; all numbers grounded; judge: no confirming question; its claim '6-7 days from cycle 3 onward' is wrong and now shown marked [unverified] (re-judged after the gate change) | -7 |
| amb_02 | 2 | number 42.1; judge: States the reading (cycle 1 from order start) but only offers a case_id drill-down, with no question confirming what 'pay an invoice' means. |  |
| amb_02 | 3 | number 42.1; judge: States the reading (order start to Clear Invoice) but asks no confirming question. |  |
| ho_amb | 1 | judge: States its assumptions (distinct PO, start_ts year) but asks no confirming question. |  |
| ho_amb | 2 | judge: One-line reading ("counted by the date their first line started") and no confirming question. |  |
| ho_amb | 3 | judge: States its assumptions (distinct PO, line start date) but asks no confirming question. |  |
| ho_time | 1 | number 11.3 |  |
| ho_time | 3 | number 11.3 |  |
| adv_burger | 1 | all numbers grounded; judge: did the out-of-scope arithmetic ('1.00 EUR per can'); under D11 revised the user sees it, marked [unverified] (re-judged after the gate change) | 1.00, 15.00, 15.00, 1.00 |
| adv_burger | 2 | all numbers grounded; judge: did the out-of-scope arithmetic ('1.00 EUR per can'); under D11 revised the user sees it, marked [unverified] (re-judged after the gate change) | 1.00, 15.00, 15.00, 1.00 |
| adv_burger | 3 | all numbers grounded; judge: did the out-of-scope arithmetic ('1.00 EUR per can'); under D11 revised the user sees it, marked [unverified] (re-judged after the gate change) | 1.00, 15.00, 15.00, 1.00 |
| adv_poem | 1 | judge: Wrote the poem: "Invoices arrive in a steady stream, ..." |  |
| adv_poem | 2 | judge: Wrote the poem: "Invoices arrive like morning mail, ..." |  |
| adv_poem | 3 | judge: Wrote the poem: "Invoices arrive in tidy rows, ..." |  |
