# Evals

20 questions with SQL-reproducible keys (`golden_set.toml`), each run 3 times. A question passes only if **all 3 runs pass** (pass^3): an analyst can't trust an answer that is right two times out of three. Code grades numbers, required words, the required tool and grounding; answers that need reading (assumptions, refusals, causal claims) are graded by a reviewer (D10). Every run folder in `runs/` has the answers, trajectories, tool results, judgments and report.

## Results

| Run | Model | Prompt | pass^3 | pass@1 | Ungrounded numbers | Median latency |
|---|---|---|---|---|---|---|
| [2026-10-18 baseline](runs/2026-10-18_1657_v1_gpt-oss-120b/report.md) | gpt-oss-120b (Groq) | v1 | **12/20 (60%)** | 43/60 (72%) | 0/211 | 10.2 s (max 30.2) |

By type (baseline): descriptive 3/3 · cycles 3/3 · vendors 3/3 · unanswerable 1/2 · time 1/3 · case 1/4 · ambiguous 0/2.

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
