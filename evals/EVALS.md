# Evals

20 questions with SQL-reproducible keys (`golden_set.toml`), each run 3 times. A question passes only if **all 3 runs pass** (pass^3): an analyst can't trust an answer that is right two times out of three. Code grades numbers, required words, the required tool and grounding; answers that need reading (assumptions, refusals, causal claims) are graded by a reviewer (D10). Every run folder in `runs/` has the answers, trajectories, tool results, judgments and report.

## Results

29 questions (20 dev, 4 held out, 5 guard), 3 runs each. Haiku runs go through the local CLI provider (D12); cost is list price.

| Run | Model | Prompt | Timeline | pass^3 all | dev | held out | guard | Peer benchmarks cited | Gate flags (wrong) | Cost / question | Median latency |
|---|---|---|---|---|---|---|---|---|---|---|---|
| [baseline](runs/2026-10-18_1657_v1_gpt-oss-120b/report.md) | gpt-oss-120b (Groq) | v1 | v1 | – | **11/20** | – | – | 26% | – | $0 (free tier) | 10.2 s |
| [haiku v1](runs/2026-10-18_1834_v1_tlv1_haiku/report.md) | Claude Haiku | v1 | v1 | 21/29 | 16/20 | 2/4 | 3/5 | 8% | 4 (0) | $0.0007 | 7.2 s |
| [haiku +prompt](runs/2026-10-18_1845_v2_tlv1_haiku/report.md) | Claude Haiku | v2 | v1 | 26/29 | 18/20 | 3/4 | 5/5 | 8% | 2 (2) | $0.0008 | 8.3 s |
| [haiku +prompt +tool](runs/2026-10-18_1822_v2_tlv2_haiku/report.md) | Claude Haiku | v2 | v2 | 25/29 | 16/20 | 4/4 | 5/5 | 89% | 4 (3) | $0.0008 | 8.2 s |
| [**haiku v3**](runs/2026-10-18_1859_v3_tlv2_haiku/report.md) | Claude Haiku | **v3** | **v2** | **29/29** | **20/20** | **4/4** | **5/5** | **92%** | 1 (1) | $0.0007 | 7.8 s (max 40 s) |

Reports are re-graded with the current grader and keys, so older rows reflect the fixed cyc_02 key and D9 revised.

**What each change did**
- **Model** (Groq gpt-oss-120b → Haiku, same prompt and tool): dev 11 → 16 of 20. The biggest single gain.
- **Prompt v2** (business readings, D9 ambiguity rule, scope rule, no invented causes): ambiguous 0/3 → 3/3 including the held-out "orders" question it never mentions, so the rule generalises; guard 4/5 → 5/5 (v1 wrote the poem in all 3 runs).
- **Timeline v2** (explicit gaps + peer benchmarks): pass/fail barely moves because benchmarks were only a bonus, but slow-line answers citing peer numbers go 8% → 89-92% and 15/15 answers compare with peers. The 24 vs 26 dip against v1 is within noise: 3 of its 7 failures are the gate blocking "net 30".
- **Prompt v3** (D9 revised: no due-date cutoff, never "overdue"; metrics tables): 28/29, held out 4/4.

**Output gate (D11 revised):** withholding answers hid correct ones that mentioned an example number ("net 30", "such as 90"): 1 right / 6 wrong across the Haiku v2/v3 runs. It now marks unverified numbers `[unverified]` with a warning instead. The guard therefore rests on the prompt's scope rule: v1 does the burger arithmetic in all 3 runs (guard 3/5), v2 and v3 decline (5/5).

**How much to trust 29/29:** it is one run of 3 repetitions on 29 questions, 6 of them graded by reviewers from the same model family as the agent; the business readings were written from failures on the dev set (the 4 held-out questions guard against that, but 4 is few); tool calls are prompted, not native (D12); it is the configuration we iterated on. Next confirmations: re-run v3 on another day, add held-out questions, and run v3 on the paid API before publishing.

## Overfitting check (2026-10-18, after choosing v3)

Pass criterion set before running: at least 7 of 8 new questions in all 3 runs, and a second model in the same range.

| Check | What it tests | Result |
|---|---|---|
| [8 new questions](runs/2026-10-18_1927_v3_tlv2_haiku/report.md), written from the data only by an independent author who never saw the prompt or the golden set; graded by a different reviewer model | overfitting to the questions | **6/8** with exact counts (7/8 with the old 1% count tolerance) |
| [Sonnet as the agent](runs/2026-10-18_1924_v3_tlv2_sonnet/report.md), same prompt v3 + timeline v2, all 29 questions | overfitting to the model | **25/29** (dev 19/20), vs Haiku 28/29 |

**Grader fix found by this check:** counts were accepted within 1%, so 76,349 passed for a key of 76,316. Integer keys are now exact unless a question sets its own tolerance; all runs were re-graded (Haiku v3 held-out 4/4 → 3/4).

**What the misses are**
- **One systematic definition slip (both models, 6 of the misses):** "orders placed in 2018" filtered on each line's first event (`start_ts`, which can be a requisition from late 2017) instead of the PO creation event: 76,280 POs vs 76,316 (0.05%). Not fixed in the prompt: fixing it now would tune on held-out questions.
- **Precision:** whole calendar days instead of exact durations (11.0 vs 10.0), 1 run in 3.
- **Question wording, not the agent:** ho_time ("lines where the invoice is recorded after the goods arrive") reads naturally as the category "3-way match, invoice after GR"; Sonnet took that reading in all 3 runs and stated it.
- **Arithmetic in the model's head:** Sonnet mis-added the top-5 vendor total (120,444,110 for 132,444,110); the gate flagged it [unverified] (right).
- **Not covered by any check:** a wrong statement in words ("it also has the most order lines") passes, because the gate only checks numbers.

**Verdict:** scores on unseen questions (6-7/8) and with another model (25/29) are close to the dev score, and the misses are specific and explainable rather than broad, so the setup is not overfitted to the dev questions or to Haiku. The dev 20/20 is optimistic; the honest headline is "about 85-95% of questions right in all 3 runs, on questions it has never seen".

## Baseline failure taxonomy (17 failed runs)

| # | Failure | Runs | Example | Root cause | Fix candidate |
|---|---|---|---|---|---|
| F1 | **Literal or wrong metric on an ambiguous question, no assumptions stated** | 6 | "Unpaid lines": 68,057 / €260M (all lines without a closed cycle, incl. consignment and lines not yet due) vs 4,302 / €16.3M | v1 prompt has no D9 rule and no business definitions ("unpaid", "time to pay") | Prompt: D9 rule + glossary |
| F2 | **Open cycles counted as payments** | 3 | "Median order → first payment, 2-way match": 21.3 days (all cycle-1 rows) vs 39.7 (closed only) | Prompt defines cycles but not that an open cycle's `days` is not a payment time | Prompt: "payment times use `is_closed`" |
| F3 | **Misreading the timeline** | 4 | Says the payment block lasted 58 days; it was removed after 40, and the 58 days came after. "Other steps under 2 days combined" when they add up to 34 | `wait_days` sits on the row of the later step; the model attributes it to the wrong step | Tool: return each wait as an explicit "from → to" gap |
| F4 | **Invented cause or benchmark** | 2 | "A price dispute"; "far longer than the typical 2–3 weeks" (real median ≈ 77 days) | The tool gives no baseline, so the model supplies one | Tool: add peer benchmarks (the method used to label the slow lines) |
| F5 | **Grounded numbers, invented meaning** | 1 | Used `ts_original` (raw timestamp before date repair) as a "promised date": "100% on time" | Column semantics only implied in the prompt | Prompt: say what `ts_original` is and that no promised date exists |
| – | Missed main delay (auto only) | 1 | case_01 run 3 never mentions the 40-day payment-block wait | Same as F3 | – |

**Key finding:** 0 of 211 numbers were invented, yet 40% of questions fail. Grounding is necessary but not sufficient: the numbers are real, the *meaning* is wrong (F1, F2, F5) or the *story* is wrong (F3, F4).

## Grader notes

- First grading pass flagged 23% of numbers as ungrounded; reading them showed grader bugs, not agent errors: "10 days" dropped as a small count, dates written with U+2011 hyphens and narrow spaces, "50th percentile", numbers quoted from the question. Fixed with a regression test each; `report` re-grades stored answers, so fixes need no new agent runs.
- Grounding matching is deliberately lenient (rounding, thousands/millions/%), so it can pass a wrong number but does not fail a correct one.
