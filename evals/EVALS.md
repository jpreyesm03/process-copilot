# Evals

20 questions with SQL-reproducible keys (`golden_set.toml`), each run 3 times. A question passes only if **all 3 runs pass** (pass^3): an analyst can't trust an answer that is right two times out of three. Code grades numbers, required words, the required tool and grounding; answers that need reading (assumptions, refusals, causal claims) are graded by a reviewer (D10). Every run folder in `runs/` has the answers, trajectories, tool results, judgments and report.

## Results

29 questions (20 dev, 4 held out, 5 guard), 3 runs each. Haiku runs go through the local CLI provider (D12); cost is list price.

| Run | Model | Prompt | Timeline | pass^3 all | dev | held out | guard | Peer benchmarks cited | Gate withheld (wrong) | Cost / question | Median latency |
|---|---|---|---|---|---|---|---|---|---|---|---|
| [baseline](runs/2026-10-18_1657_v1_gpt-oss-120b/report.md) | gpt-oss-120b (Groq) | v1 | v1 | – | **11/20** | – | – | 26% | 0 | $0 (free tier) | 10.2 s |
| [haiku v1](runs/2026-10-18_1834_v1_tlv1_haiku/report.md) | Claude Haiku | v1 | v1 | 22/29 | 16/20 | 2/4 | 4/5 | 8% | 4 (0) | $0.0007 | 7.2 s |
| [haiku +prompt](runs/2026-10-18_1845_v2_tlv1_haiku/report.md) | Claude Haiku | v2 | v1 | 26/29 | 18/20 | 3/4 | 5/5 | 8% | 2 (2) | $0.0008 | 8.3 s |
| [haiku +prompt +tool](runs/2026-10-18_1822_v2_tlv2_haiku/report.md) | Claude Haiku | v2 | v2 | 24/29 | 16/20 | 3/4 | 5/5 | 89% | 4 (3) | $0.0008 | 8.2 s |
| [**haiku v3**](runs/2026-10-18_1859_v3_tlv2_haiku/report.md) | Claude Haiku | **v3** | **v2** | **28/29** | **19/20** | **4/4** | **5/5** | **92%** | 1 (1) | $0.0007 | 7.8 s (max 40 s) |

Reports are re-graded with the current grader and keys, so older rows reflect the fixed cyc_02 key and D9 revised.

**What each change did**
- **Model** (Groq gpt-oss-120b → Haiku, same prompt and tool): dev 11 → 16 of 20. The biggest single gain.
- **Prompt v2** (business readings, D9 ambiguity rule, scope rule, no invented causes): ambiguous 0/3 → 3/3 including the held-out "orders" question it never mentions, so the rule generalises; guard 4/5 → 5/5 (v1 wrote the poem in all 3 runs).
- **Timeline v2** (explicit gaps + peer benchmarks): pass/fail barely moves because benchmarks were only a bonus, but slow-line answers citing peer numbers go 8% → 89-92% and 15/15 answers compare with peers. The 24 vs 26 dip against v1 is within noise: 3 of its 7 failures are the gate blocking "net 30".
- **Prompt v3** (D9 revised: no due-date cutoff, never "overdue"; metrics tables): 28/29, held out 4/4.

**The weakest piece is now the output gate**: it catches real errors (4/4 burger arithmetic in v1, mis-added totals) but also withholds correct answers that mention an example number ("net 30", "such as 90"): precision 1 right / 6 wrong across the Haiku v2/v3 runs.

## Baseline failure taxonomy (17 failed runs)

| # | Failure | Runs | Example | Root cause | Fix candidate |
|---|---|---|---|---|---|
| F1 | **Literal or wrong metric on an ambiguous question, no assumptions stated** | 6 | "Unpaid lines": 68,057 / €260M (all lines without a closed cycle, incl. consignment and lines not yet due) vs 4,302 / €16.3M | v1 prompt has no D9 rule and no business definitions ("unpaid", "time to pay") | Prompt: D9 rule + glossary |
| F2 | **Open cycles counted as payments** | 3 | "Median order → first payment, 2-way match": 21.3 days (all cycle-1 rows) vs 39.7 (closed only) | Prompt defines cycles but not that an open cycle's `days` is not a payment time | Prompt: "payment times use `is_closed`" |
| F3 | **Misreading the timeline** | 4 | Says the payment block lasted 58 days; it was removed after 40, and the 58 days came after. "Other steps under 2 days combined" when they add up to 34 | `wait_days` sits on the row of the later step; the model attributes it to the wrong step | Tool: return each wait as an explicit "from → to" gap |
| F4 | **Invented cause or benchmark** | 2 | "A price dispute"; "far longer than the typical 2–3 weeks" (real median ≈ 77 days) | The tool gives no baseline, so the model supplies one | Tool: add peer benchmarks (JP's labelling method) |
| F5 | **Grounded numbers, invented meaning** | 1 | Used `ts_original` (raw timestamp before date repair) as a "promised date": "100% on time" | Column semantics only implied in the prompt | Prompt: say what `ts_original` is and that no promised date exists |
| – | Missed main delay (auto only) | 1 | case_01 run 3 never mentions the 40-day payment-block wait | Same as F3 | – |

**Key finding:** 0 of 211 numbers were invented, yet 40% of questions fail. Grounding is necessary but not sufficient: the numbers are real, the *meaning* is wrong (F1, F2, F5) or the *story* is wrong (F3, F4).

## Grader notes

- First grading pass flagged 23% of numbers as ungrounded; reading them showed grader bugs, not agent errors: "10 days" dropped as a small count, dates written with U+2011 hyphens and narrow spaces, "50th percentile", numbers quoted from the question. Fixed with a regression test each; `report` re-grades stored answers, so fixes need no new agent runs.
- Grounding matching is deliberately lenient (rounding, thousands/millions/%), so it can pass a wrong number but does not fail a correct one.
