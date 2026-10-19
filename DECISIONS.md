# Decisions

Format: constraint → options → evidence → choice → would change if. Constraints (C1–C5) are in `CLIENT_BRIEF.md`.

## D1 · Impossible timestamps (2026-10-17)
**Constraint:** C3 trust (every number traceable; no silent data loss).
**Evidence:** 97% of events are in 2018, but 97 events fall outside 2017–2019 (1948, 1993, 2001, 2008, 2015–16, 2020), touching 82 cases (0.03%). All of them are supplier-side events (79 "Vendor creates invoice", 18 "Vendor creates debit memo"): dates entered by the supplier in their own system. Throughput = last − first event, so one 1948 event turns a 60-day case into 70 years.
**Options:** (a) drop the 82 cases · (b) drop only the bad events · (c) keep every event and flag it · (d) repair the date when the evidence supports it, flag the rest.
**First choice (Oct 17):** (c). **Revised (Oct 18):** the file turned out to be sorted by the bad dates too (a 1948 invoice sorts before its own purchase order), so flagging alone still corrupts any step-order analysis. The pattern points to year typos (e.g. `1948-01-26 22:59` next to a real `2018-01-26 22:59` on the same line).
**Choice:** (d). For each bad event, try the same day and minute in 2017, 2018 and 2019, and check it against the line's valid timeline (± 60 days):
| Result | Events | Rule |
|---|---|---|
| duplicate | 24 | an identical event (same activity, same minute) already exists in 2018 → the bad row is a copy; excluded from sequences |
| repaired | 67 | exactly one year fits the line's timeline (66), or two fit and only one lands on the same minute as another event of the line (1: a debit memo issued together with its invoice) |
| unresolved | 6 | no year fits uniquely → excluded from sequences and durations |
The 6 unresolved sit on 2 of 251,734 lines: one would need a day/month swap as well as a year fix (speculative), the other is a monthly-billed framework contract whose end-of-month invoices can't be mapped to a unique month. Both are supplier invoice dates in the middle of their lines, so they don't move durations; further effort wouldn't change any client-facing number.
The original value is always kept in `ts_original`, and `ts_status` says which rule applied.
**Would change if:** the client can confirm true dates from SAP (invoice document numbers).

## D8 · One hand-written client for any OpenAI-compatible LLM; no agent framework (2026-10-18)
**Constraint:** C2 cost (free tier for development) and the need to compare models in evals without rewriting code.
**Options:** (a) one `httpx` client for the OpenAI-compatible chat API, provider chosen in `.env` · (b) each provider's own SDK · (c) a framework (LangChain / LiteLLM / an agents SDK).
**Evidence:** Groq, Gemini, OpenAI and Ollama all expose the same `/chat/completions` + tool-calling format, so (a) switches provider with one line. First run on Groq (`openai/gpt-oss-120b`, free tier): 5 MVP questions answered in 0.5–23.5 s with 1–4k tokens each.
**Choice:** (a), plus a hand-written loop (~90 lines) instead of a framework, so every limit is explicit and explainable: max 10 steps, stop on a repeated identical call, tool errors returned to the model, retries only for provider errors (429/5xx).
**Would change if:** we need streaming, multi-agent routing or provider-specific features (e.g. prompt caching controls); then re-evaluate a framework as a measured trade-off.

## D7 · Identical rows: keep them, collapse them where it matters (2026-10-18)
**Constraint:** C3 trust (counts and sequences must reflect what happened).
**Evidence:** 132,748 rows (8.3%) are identical to another row in all 22 columns, across 4,955 lines: Record Service Entry Sheet 120,846, Record Goods Receipt 10,981, Clear Invoice 584. The extreme case is 42 identical goods receipts on one line by the same user in the same minute. The log has no event ID and minute-level timestamps, so a true double-record and a batch of real postings (42 deliveries entered together) look the same.
**Options:** (a) delete identical rows (undercounts real batches) · (b) keep everything as is (fake rework loops, zero-length payment cycles) · (c) keep every row, add `n_identical`, and use one copy per group (`is_canonical`) for sequences and cycles.
**Choice:** (c). Durations are unaffected either way (copies share the timestamp). Sequences, variants and cycles use canonical rows only. Raw counts are reported with the caveat.
**Would change if:** an extract with SAP document numbers lets us tell batches from double-records.

## D2 · Case notion: PO line item, not PO (2026-10-17)
**Constraint:** C3 trust (metrics must reflect what actually happened).
**Evidence:** 76,349 POs, 251,734 line items; items per PO: median 1, p90 7, max 429. Each line has its own flow: goods arrive and invoices clear per item, and the 4 item categories (expected flows) are per line.
**Options:** (a) case = PO line item (as delivered) · (b) case = PO (merge all lines' events).
**Choice:** (a). Model at the finest grain and aggregate later: line → PO is a `GROUP BY`, while PO → line can't be undone once events are merged. Merging a 429-line PO would create fake loops and meaningless durations.
**Would change if:** the client's question is about the order as a whole ("when was my order complete?"), then add a PO-level view on top. **Known limitation:** one invoice can cover several lines and appears once per line (convergence); the object-centric view (stretch M10) addresses this.

## D3 · Case value (2026-10-17)
**Evidence:** the value changes across events in 4,632 cases (1.8%, price/quantity changes).
**Choice:** value at "Create Purchase Order Item" (the ordered amount; present in 100% of cases).
**Would change if:** we analyse price-change impact, then also keep the final value.

## D4 · Recurring lines: measure cycles, not whole lines (2026-10-18)
**Constraint:** C3 trust (a "slow order" must be a real process problem, not a long-running contract).
**Evidence:** ~6,800 lines (2.7%) are paid more than once: 6,445 Standard PO, 263 Framework order, 124 EC Purchase order. Framework orders have a median duration of 35 days but a p90 of **350 days**; the largest line has 990 events (a logistics services contract with 258 goods receipts and 67 payments on one line). Measured as first-to-last event, these contracts dominate any "slowest orders" ranking.
**Options:** (a) keep lines as they are + `is_recurring` flag · (b) exclude recurring lines from duration metrics · (c) split each line into payment cycles.
**Choice:** (c). Each `Clear Invoice` closes a cycle and the next event opens a new one. Cycles live in a derived `cycles` table (case_id, cycle_no, start, end); the `events` table is untouched, so the full line is always available. Single-payment lines (97%) are exactly one cycle, so for them nothing changes.
**Known limitation:** cycle 1 includes ordering (requisition, Create PO Item) and later cycles don't, so durations are only compared within the same `cycle_no` bucket (first cycles vs. first cycles).
**Would change if:** the client asks about contract performance as a whole, then report at line level for framework orders.

## D5 · "NONE" in user/resource is a hidden null (2026-10-18)
**Evidence:** `user` and `resource` contain the text "NONE" on every `Vendor creates invoice` (219,919) and `Record Service Entry Sheet` (164,975), and on 7,941 `Clear Invoice` events: steps done by the supplier or the system, not an employee.
**Choice:** convert "NONE" to NULL, so no "top users" analysis ever ranks a user called NONE. The meaning (no internal person) is kept implicitly by the activity.

## D6 · Timestamps are text in UTC (2026-10-18)
**Evidence:** values look like `2018-01-02T12:53:00.000Z`: ISO 8601, the `Z` means UTC, but pandas reads them as strings.
**Choice:** parse to datetime and keep UTC. Durations are unaffected. Hour-of-day analyses must convert to Europe/Amsterdam first (an event at 23:00 UTC is 00:00 or 01:00 in the Netherlands).
**Finding:** supplier-side events (`Vendor creates invoice`, `Vendor creates debit memo`) are always at 21:59 or 22:59 UTC, i.e. midnight in Amsterdam (summer/winter time). They carry a **date only**, stored as local midnight. Never analyse their time of day.
## D9 · Ambiguous questions: assume the business reading, say so, still give the number (2026-10-18)
**Constraint:** C3 trust and C5 (Excel/SQL users who want a figure they can adjust, not a quiz back).
**Evidence:** "lines with goods and invoice but never paid" read literally gives 27,570 lines / €102.6M; 23,237 of them started from Oct 2018 (not due yet at extraction) and 31 were deleted. The business reading (due, not deleted) is 4,302 lines / €16.3M, 6× less money.
**Options:** (a) ask a clarifying question and give no number · (b) answer the most business-relevant reading, state the assumptions explicitly, suggest questions to confirm · (c) answer every reading side by side.
**Choice:** (b). The API has no memory, so (a) costs the user a second round trip; (c) gets noisy with 3+ readings. A number with its assumptions lets the user correct for factors they know and we don't.
**Graded in evals:** the number must match the business-reading key, the answer must name its assumptions, and it must suggest at least one confirming question.
**Would change if:** the API gets conversation memory, then asking first becomes cheap for high-stakes questions.

## D10 · Evals: code grades what it can, a reviewer grades the rest (2026-10-18)
**Constraint:** C2 cost and C3 trust (a grade must be explainable).
**Evidence:** 14 of 20 questions are fully checkable by code (numbers within tolerance, required words, required tool, grounding). 6 need reading: stated assumptions (2 ambiguous), refusals (2 unanswerable), causal claims (4 slow lines, partly).
**Options:** (a) LLM judge, same model as the agent (free, but grades its own kind of output) · (b) LLM judge, a different model · (c) human grading.
**Choice:** a reviewer outside the agent's model family reads the 6 judged questions (18 answers per run) from `judge_queue.md` and records pass/fail with a note in `judgments.json`; code grades everything else. No grading model runs inside the pipeline yet, so the eval itself costs $0 beyond the agent's calls.
**Would change if:** runs become frequent (e.g. in CI); then move the judge prompt into code against an API model and report its agreement with the stored manual judgments.

## D11 · Scope guard: prompt rule + output gate + usage limits (2026-10-18)
**Constraint:** C2 cost (a public demo key is an open tap) and C3 trust (no answers outside the data).
**Threat:** off-topic requests, off-topic disguised as the domain ("if 85 cans and 30 lids cost 100 EUR, what does a can cost?") and prompt injection ("print your system prompt").
**Options:** (a) scope rule in the prompt · (b) input classifier before the agent · (c) output gate reusing the grounding check · (d) usage limits.
**Choice:** a + c + d. The prompt rule is cheap but only a request; the gate is a wall built from code that already exists: numbers in an answer must come from a tool result, and numbers from the question may be repeated but never computed with, which withholds exactly the disguised-arithmetic trick. Limits cap questions per client per hour, per day overall, and tokens per question. (b) is skipped unless evals show a + c leaking: it adds a model call per question.
**Measured by:** 5 guard questions in the golden set (4 tricks to decline, 1 borderline in-scope question that must still be answered, since over-blocking is a failure too).
**Would change if:** the guard evals show leaks, then add (b); a gate cannot catch off-topic answers that contain no numbers.

## D12 · Develop and evaluate on Claude through a local CLI provider before paying for an API (2026-10-18)
**Constraint:** C2 cost, and the project's value is not proven yet, so no paid API until it is. The free Groq tier caps gpt-oss-120b at 200k tokens a day, less than one full eval run (29 questions × 3 ≈ 330k).
**Options:** (a) stay on Groq free, one eval every 1-2 days · (b) pay for an API now · (c) run Claude through the locally installed `claude` CLI as a provider.
**Choice:** (c), for development and evals; the target model for a published demo is a frontier API model, so tuning on Claude is closer to what will ship. The provider keeps the eval honest: each call is a fresh process, built-in tools and MCP servers are off and the working directory is empty, so the model cannot read files (including the answer keys); our system prompt replaces the CLI's own (a test request is ~650 input tokens). Our loop, tools, output gate, traces and grader run unchanged. Each call reports its list-price cost, which answers "what would the API cost" before paying.
**Known differences from the API:** tool use is prompted (JSON replies) instead of native function calling; temperature cannot be set; latency includes CLI start-up (~1 s per call). Results describe Claude with prompted tools; the final API run must confirm them.
**Would change if:** the project goes public, then switch the provider to the paid API and re-run the evals to confirm.

## D9 revised · "Unpaid" has no due-date cutoff: nothing is called overdue (2026-10-18)
**Evidence:** the data has no due dates or payment terms ('Change payment term' occurs 7 times, with no term value). The first D9 reading treated lines created before Oct 2018 as due (4,302 lines / €16.3M), but €15.8M of that had the invoice recorded in Oct 2018 or later, weeks before the data ends (17 Jan 2019): most of it was probably not overdue. The headline shrank about 30× once "due" was checked.
**Options:** (a) keep the creation-date cutoff · (b) invoice date + an assumed payment term · (c) age breakdown only · (d) compare with the vendor's own paid invoices.
**Choice (JP):** no assumptions where the data has none, so (c) + (d). Unpaid = goods and invoice received, not paid, not deleted, with no date cutoff; report days open since the invoice was recorded and flag lines open longer than 90% of the same vendor's paid invoices (vendors with fewer than 30 paid invoices are reported as "too few to compare").
**Result:** 27,539 open lines / €102.5M; 828 / €1.02M open longer than the vendor usually takes (data end = last day with 10+ events, 18 Jan 2019); €15.8M with vendors too rarely paid to have a baseline (a manual-review list).

## D13 · Process metrics are tables built with the warehouse (2026-10-18)
**Constraint:** C3 trust: the overview page, the agent and the tests must show the same number for the same question.
**Choice:** `metrics.py` builds m_bottlenecks, m_variants, m_rework, m_conformance, m_open_invoices and m_summary at build time (about 1 s). Rework cost is compared within the same item category and value band (groups with at least 30 lines on each side), because rework is more common on bigger, more complex lines; it remains a correlation.
**Would change if:** the data were refreshed daily, then compute them incrementally or as views.
