# Process Copilot

**Ask a purchase-to-pay process questions in plain English and get answers with evidence, plus the process metrics a value engineer would present.** Built on the BPI Challenge 2019 SAP event log: 1.6M events, 251,734 purchase-order lines from a multinational coatings company.

**Live demo: [process-copilot.streamlit.app](https://process-copilot.streamlit.app/)**

| Finding | Value |
|---|---|
| Paid before any goods were received (3-way match lines) | **€1.75M** across 655 lines |
| Invoices open longer than 90% of that vendor's paid invoices | **€1.02M** across 828 lines |
| Waiting time spent between invoice receipt and payment | **40%** of all waiting |
| Extra days to payment when an approval change happens (same category and value band) | **+42 days** |

## What it does

- **Answers questions** ("why did order line 4507000365_00010 take so long?", "which vendors have the most payment blocks?") with an agent that can only read the data through two tools: read-only SQL and an order-line timeline that compares every wait with the same vendor and similar lines.
- **Shows its work:** every answer lists the queries behind it, and any number that does not come from a query result is marked `[unverified]`.
- **Stays on topic:** a small classifier screens questions before the main model, the prompt declines anything outside the process data, and usage is capped per visitor and per day.
- **Measures the process:** bottlenecks, process variants, rework cost, conformance and open invoices, precomputed with the warehouse.

## How well it works

29 questions with answer keys computed in SQL, each asked 3 times; a question counts only if all 3 answers are right. Details in [evals/EVALS.md](evals/EVALS.md).

| Configuration | Dev (20) | Held out (4) | Out-of-scope tricks (5) | Cost per question |
|---|---|---|---|---|
| Baseline: gpt-oss-120b, prompt v1 | 11/20 | – | – | free tier |
| Claude Haiku, prompt v1, timeline v1 | 16/20 | 2/4 | 3/5 | $0.0007 |
| **Claude Haiku, prompt v3, timeline v2** | **20/20** | **3/4** | **5/5** | **$0.0007** |
| Claude Sonnet, prompt v3, timeline v2 | 19/20 | 2/4 | 4/5 | – |

On 8 extra questions written independently of the prompt, the final configuration answers 6 of 8 correctly in all 3 runs. Every change (model, prompt, tool) was measured on its own; the misses are listed with their causes.

## How it works

```
 question ──► topic gate (small classifier) ──► agent loop (limits: steps, tokens, repeats)
                                                    │  ▲
                                         tool calls │  │ results (with ids for citation)
                                                    ▼  │
                         run_sql (read-only, 3 safety layers)   get_case_timeline (waits + peer benchmarks)
                                                    │
                                     DuckDB warehouse: events · cases · cycles · waits · m_* metrics
                                                    │
 answer ◄── grounding check (marks numbers no query produced) ◄──┘
```

- **Data preparation** (`build_db.py`): repairs impossible dates, keeps identical rows but marks one canonical copy, splits recurring contracts into payment cycles so a two-year framework order is not ranked as one "slow order".
- **Agent** (`agentkit/`): a hand-written loop over any OpenAI-compatible model, with typed tools, a result store for citations, step and token budgets, tracing to DuckDB, and a grounding check.
- **Evals** (`evaluate.py`, `evals/`): golden set with SQL keys, pass^3, code checks plus reviewer judgments, held-out and independent questions.
- **Interfaces:** a Streamlit app (`app/`) and a FastAPI endpoint (`api.py`, `POST /ask`).

Each design choice and the evidence behind it is in [DECISIONS.md](DECISIONS.md); the hypothetical client and constraints are in [CLIENT_BRIEF.md](CLIENT_BRIEF.md).

## Run it

Requires Python 3.12 and [uv](https://docs.astral.sh/uv/).

```bash
uv sync
uv run python -m process_copilot.build_db --csv data_public/bpi2019_events.csv.gz   # ~10 s
cp .env.example .env                                                                 # add GROQ_API_KEY
uv run streamlit run app/streamlit_app.py                                            # the app
uv run python -m process_copilot.agent "Which vendors have the most payment blocks?"  # one question
uv run uvicorn process_copilot.api:app                                               # the API, docs at /docs
uv run pytest                                                                        # tests
```

## Repository

| Path | What |
|---|---|
| `src/agentkit/` | Reusable agent plumbing: LLM clients, loop, tools, grounding, guards, tracing |
| `src/process_copilot/` | This product: warehouse build, metrics, tools, prompts, evaluation, API |
| `app/` | Streamlit app |
| `evals/` | Golden set, every eval run (answers, judgments, reports), results |
| `notebooks/` | Exploratory analysis and the labelling of slow order lines |
| `data_public/` | The event log (CC BY 4.0, see its README) |
| `tests/` | Unit and integration tests on a six-line fixture with hand-checked answers |

## Data and licence

Data: van Dongen, Boudewijn (2019). *BPI Challenge 2019*. 4TU.ResearchData. https://doi.org/10.4121/uuid:d06aff4b-79f0-45e6-8ec8-e19730c248f1 (CC BY 4.0).
Code: [MIT](LICENSE). Author: JP Reyes.
