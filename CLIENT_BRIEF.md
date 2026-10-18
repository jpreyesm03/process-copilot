# Client brief (hypothetical client, written before building)

**Client:** Dutch multinational in coatings and paints: 4 companies, ~2,000 suppliers, ~76k purchase orders and ~250k order lines a year (the company behind the public BPI Challenge 2019 log). *Hypothetical engagement, real data.*

**User:** the **Procurement Operations Lead** and her 6 analysts. She decides **which process fixes to fund** (e.g. enforce goods receipt before paying, remove a manual payment block, renegotiate with specific suppliers). Today the team answers "why is this late?" by exporting SAP data to Excel; one investigation takes about half a day.

**Questions they ask:**
1. Where does purchase-to-pay get stuck, and how much money sits at each step?
2. Why did *this* order line take 3 months?
3. Why are we paying invoices late and missing early-payment discounts?
4. Which suppliers cause the most rework (price/quantity changes, cancelled invoices)?
5. Are we paying invoices before the goods arrive, when the contract says we shouldn't?

## Constraints (every decision in DECISIONS.md points to one of these)
| # | Constraint | Value | Why it's realistic |
|---|---|---|---|
| C1 | Latency | < 30 s per question | An analyst asks follow-ups in a live meeting; longer and they go back to Excel |
| C2 | Cost | < $0.02 per question | ~50 questions/day across the team must cost less than a coffee |
| C3 | Trust | 0 numbers that can't be traced to a query; every root-cause claim cites event rows | Finance acts on these numbers; one invented figure and the tool is dead |
| C4 | Access | Read-only on the ERP extract; the agent can never write | IT security will not approve anything that can change ERP data |
| C5 | Users | Analysts who know Excel and some SQL | Answers in plain language, with the evidence (rows, query) in an appendix |

## Success =
**80% of the team's questions answered correctly in < 30 s with 0 ungrounded numbers**, and a first value assessment: **3 process findings with € at stake**.

## Out of scope (v1)
Writing back to the ERP · predicting future delays · supplier payment terms (not in the data) · multi-turn memory across questions.
