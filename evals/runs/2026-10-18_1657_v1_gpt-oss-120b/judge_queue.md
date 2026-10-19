# Judge queue

Grade each answer pass/fail against its rules into judgments.json:
`{"<id>#<repeat>": {"pass": true, "notes": "..."}}`

## case_01#1

**Q:** Why did order line 4507000365_00010 take so long?

**Rules:**
- Does not blame delivery or the goods receipt (it took 0.4 days)
- Invents no cause the events do not show (e.g. a dispute, a holiday)

**Reference:** 142 days vs a vendor median of 99 (94th pct): abnormal. Delivery was fast. Two abnormal waits: the payment block took 40 days to remove (vendor median 6.3, +34) and the invoice came 42.5 days after the order (median 21.5, +21). The last 58 days to payment are normal for this vendor but slow vs similar lines (74th pct): a vendor-level pattern.

**Auto checks:** {'answered': True, 'number 40': False, 'number 42.5': True, "mentions 'payment block'": True, 'used get_case_timeline': True, 'all numbers grounded': True}

**Answer:**

**Order line 4507000365_00010 needed ≈ 142 days from creation to payment.**  

The long duration is caused by two unusually long waiting periods in the 3‑way‑match flow (invoice → goods receipt → payment):

| Step (seq) | Activity | Wait since previous step |
|------------|----------|--------------------------|
| 2 → 1 | **Vendor creates invoice** – 42.5 days after the PO was created | [seq 1 → seq 2, wait 42.5 days] |
| 6 → 5 | **Clear Invoice** – 57.8 days after the payment block was removed | [seq 5 → seq 6, wait 57.8 days] |

These two gaps together account for **≈ 100 days** of the total 141.99‑day throughput (see the timeline result [r1]).  

- The first gap shows the supplier took over a month to issue the invoice after the PO was issued.  
- The second gap shows the internal payment block remained in place for almost two months before the invoice was finally cleared.

Thus, the line was slow because **both the supplier’s invoicing delay and a prolonged internal payment‑block period** extended the process.

---

## case_01#2

**Q:** Why did order line 4507000365_00010 take so long?

**Rules:**
- Does not blame delivery or the goods receipt (it took 0.4 days)
- Invents no cause the events do not show (e.g. a dispute, a holiday)

**Reference:** 142 days vs a vendor median of 99 (94th pct): abnormal. Delivery was fast. Two abnormal waits: the payment block took 40 days to remove (vendor median 6.3, +34) and the invoice came 42.5 days after the order (median 21.5, +21). The last 58 days to payment are normal for this vendor but slow vs similar lines (74th pct): a vendor-level pattern.

**Auto checks:** {'answered': True, 'number 40': False, 'number 42.5': True, "mentions 'payment block'": True, 'used get_case_timeline': True, 'all numbers grounded': True}

**Answer:**

**Order line 4507000365_00010 needed ≈ 142 days from creation to payment.**  

- The longest pause was **57.8 days** between *Remove Payment Block* (seq 5) and *Clear Invoice* (seq 6) — the line sat blocked before the payment was finally cleared.  
- A second large gap was **42.5 days** between *Create Purchase Order Item* (seq 1) and the vendor’s *creates invoice* event (seq 2), meaning the supplier took over a month to issue the invoice.  
- The steps that must follow the invoice (Goods Receipt → Invoice Receipt) were fast (≈ 1.6 days total), so the delay is not in the 3‑way‑match processing itself.  

**Why it was slow:**  
- Late supplier invoicing (≈ 6 weeks).  
- Prolonged internal payment‑block period before the invoice could be cleared (≈ 8 weeks).  

These two waiting periods together account for most of the 142‑day throughput.  

*Evidence:* seq 1→2 wait 42.5 days, seq 5→6 wait 57.8 days (see timeline r1).

---

## case_01#3

**Q:** Why did order line 4507000365_00010 take so long?

**Rules:**
- Does not blame delivery or the goods receipt (it took 0.4 days)
- Invents no cause the events do not show (e.g. a dispute, a holiday)

**Reference:** 142 days vs a vendor median of 99 (94th pct): abnormal. Delivery was fast. Two abnormal waits: the payment block took 40 days to remove (vendor median 6.3, +34) and the invoice came 42.5 days after the order (median 21.5, +21). The last 58 days to payment are normal for this vendor but slow vs similar lines (74th pct): a vendor-level pattern.

**Auto checks:** {'answered': True, 'number 40': False, 'number 42.5': True, "mentions 'payment block'": True, 'used get_case_timeline': True, 'all numbers grounded': False}

**Answer:**

The line **4507000365 _00010** needed ≈ 142 days from the first trusted event to payment. The longest pauses were:

* **42.5 days** between the PO being created (seq 1) and the supplier’s invoice (seq 2).  
* **57.8 days** between the payment block being removed (seq 5) and the invoice being cleared (seq 6).

These two gaps together account for ≈ 100 days of the total 141.99‑day throughput, showing that the line was delayed first by a late supplier invoice and then by a long hold before the final payment step.  

*Seq 1 → 2 wait = 42.5 days*【r1】  
*Seq 5 → 6 wait = 57.8 days*【r1】  

---

## case_02#1

**Q:** Why did order line 4507000414_00010 take so long?

**Rules:**
- Names the gap between the vendor's invoice date and recording the invoice as the main delay
- Invents no cause the events do not show

**Reference:** 122 days: normal for this vendor (59th pct), whose lines are slow in general (median 113 vs 80 for similar lines). One abnormal wait: the vendor's invoice was recorded 87 days after its invoice date (vendor median 7.6, 96th pct, +79). Fast handling afterwards (block removed in 1.6 days, paid 6 days later) hid most of that delay in the total.

**Auto checks:** {'answered': True, 'number 86.7': True, "mentions 'invoice'": True, 'used get_case_timeline': True, 'all numbers grounded': False}

**Answer:**

The line **4507000414_00010** needed ≈ 122 days from PO creation to payment because the invoice that the vendor sent was not recorded in the system for almost three months.

**What happened**

| Step (seq) | Activity | Date / time | Days since previous step |
|------------|----------|-------------|--------------------------|
| 1 | Create Purchase Order Item | 2018‑01‑02 13:49 | – |
| 2 | Record Goods Receipt | 2018‑01‑17 13:42 | **15 days** after PO |
| 3 | Vendor creates invoice (date only) | 2018‑01‑29 22:59 | **12.4 days** after GR |
| 4 | **Record Invoice Receipt** | 2018‑04‑26 15:32 | **86.7 days** after the vendor’s invoice date |
| 5 | Remove Payment Block | 2018‑04‑28 06:43 | 1.6 days |
| 6 | Clear Invoice (payment) | 2018‑05‑04 08:14 | 6.1 days |

* The **86.7‑day gap** between the vendor’s invoice (event 3) and the internal “Record Invoice Receipt” (event 4) is the dominant cause of the long cycle (see seq 4, wait_days = 86.7)【r1】.  
* All other steps were relatively quick (15 days to GR, ~12 days to invoice creation, then < 8 days to payment after the invoice was finally recorded).  

**Conclusion**  
The order line was delayed mainly because the invoice was not entered into the system for almost three months after the vendor issued it, extending the overall throughput to 121.8 days.

---

## case_02#2

**Q:** Why did order line 4507000414_00010 take so long?

**Rules:**
- Names the gap between the vendor's invoice date and recording the invoice as the main delay
- Invents no cause the events do not show

**Reference:** 122 days: normal for this vendor (59th pct), whose lines are slow in general (median 113 vs 80 for similar lines). One abnormal wait: the vendor's invoice was recorded 87 days after its invoice date (vendor median 7.6, 96th pct, +79). Fast handling afterwards (block removed in 1.6 days, paid 6 days later) hid most of that delay in the total.

**Auto checks:** {'answered': True, 'number 86.7': True, "mentions 'invoice'": True, 'used get_case_timeline': True, 'all numbers grounded': False}

**Answer:**

The line **4507000414 _ 00010** needed ≈ 122 days from PO creation to payment.  
The dominant delay was the long gap between the supplier’s invoice date and the company’s recording of that invoice:

| Step (seq) | Activity | Date / time | Wait days from previous step |
|------------|----------|-------------|------------------------------|
| 1 | Create Purchase Order Item | 2018‑01‑02 13:49 | – |
| 2 | Record Goods Receipt | 2018‑01‑17 13:42 | **15 d** |
| 3 | Vendor creates invoice | 2018‑01‑29 22:59 | **12.4 d** |
| 4 | **Record Invoice Receipt** | 2018‑04‑26 15:32 | **86.7 d** |
| 5 | Remove Payment Block | 2018‑04‑28 06:43 | 1.6 d |
| 6 | Clear Invoice (payment) | 2018‑05‑04 08:14 | 6.1 d |

**Why it was slow**

- After the supplier issued the invoice on 2018‑01‑29, the company did not record the invoice until 2018‑04‑26 – a **86‑day** waiting period, which accounts for roughly 71 % of the total throughput (86 / 122 ≈ 0.71).  
- All other steps were relatively quick (≤ 15 days), so the invoice‑receipt delay is the primary cause of the long cycle.

**Bottom line**: The order line was delayed mainly because the invoice was not entered into the system for almost three months after it was created by the vendor.

---

## case_02#3

**Q:** Why did order line 4507000414_00010 take so long?

**Rules:**
- Names the gap between the vendor's invoice date and recording the invoice as the main delay
- Invents no cause the events do not show

**Reference:** 122 days: normal for this vendor (59th pct), whose lines are slow in general (median 113 vs 80 for similar lines). One abnormal wait: the vendor's invoice was recorded 87 days after its invoice date (vendor median 7.6, 96th pct, +79). Fast handling afterwards (block removed in 1.6 days, paid 6 days later) hid most of that delay in the total.

**Auto checks:** {'answered': True, 'number 86.7': True, "mentions 'invoice'": True, 'used get_case_timeline': True, 'all numbers grounded': False}

**Answer:**

The line **4507000414_00010** needed ≈ 122 days from PO creation to payment because the invoice was not recorded in the system for almost three months after the vendor issued it.

**What happened**

| Step (seq) | Activity | Date / time | Days since previous step |
|------------|----------|-------------|--------------------------|
| 1 | Create Purchase Order Item | 2018‑01‑02 13:49 | – |
| 2 | Record Goods Receipt | 2018‑01‑17 13:42 | **15 days** |
| 3 | Vendor creates invoice (date only) | 2018‑01‑29 22:59 | **12.4 days** |
| 4 | **Record Invoice Receipt** | 2018‑04‑26 15:32 | **86.7 days** ← **major delay** |
| 5 | Remove Payment Block | 2018‑04‑28 06:43 | 1.6 days |
| 6 | Clear Invoice (payment) | 2018‑05‑04 08:14 | 6.1 days |

* The longest gap is between the vendor‑issued invoice (seq 3) and the internal “Record Invoice Receipt” (seq 4), a **86.7‑day** wait (event 10988)【r1】.  
* After the invoice was finally recorded, the remaining steps (payment block removal and clearing) took only about a week.

**Why it took so long**

- The invoice, although created by the vendor on 2018‑01‑29, was not entered into the system until 2018‑04‑26, causing a **≈ 3‑month bottleneck** in the invoice‑receipt stage.  
- All other steps (PO creation, goods receipt, payment block removal, and clearing) occurred within normal timeframes (≤ 15 days).

Thus, the primary reason for the prolonged throughput (121.8 days) is the delayed recording of the vendor’s invoice.

---

## case_03#1

**Q:** Why did order line 4507000905_00050 take so long?

**Rules:**
- Names recording the invoice after goods receipt as the main delay
- Notes that payment after recording was fast (under a day)
- Invents no cause the events do not show

**Reference:** 147 days vs a vendor median of 115 (93rd pct): abnormal. One step explains it: the invoice was recorded 113 days after the goods arrived (vendor median 35, 97th pct, +78), although the vendor's invoice was dated before the goods receipt. Once recorded, it was paid within a day (4th pct), so the delay was entirely in recording the invoice.

**Auto checks:** {'answered': True, 'number 113.1': True, "mentions 'goods receipt'": True, "mentions 'invoice'": True, 'used get_case_timeline': True, 'all numbers grounded': False}

**Answer:**

The line **4507000905_00050** needed **147 days** from PO creation to payment (cycle 1).  
The long duration is almost entirely caused by a **113‑day gap between the goods receipt and the invoice receipt**:

| Step (seq) | Event | Date & time | Wait days since previous step |
|------------|-------|-------------|------------------------------|
| 3 | Vendor creates invoice | 2018‑02‑05 22:59 | – |
| 4 | Record Goods Receipt | 2018‑02‑06 12:35 | **0.6 d** |
| 5 | Record Invoice Receipt | 2018‑05‑30 15:29 | **113.1 d** |
| 6 | Clear Invoice | 2018‑05‑31 10:32 | 0.8 d |

* The **113‑day delay** between the goods receipt (seq 4) and the invoice receipt (seq 5) dominates the total throughput (147 days) — the rest of the steps are under 2 days combined.  
* All events are canonical (no duplicates) and the cycle is closed (cycle 1, 147 days) — so the delay is not due to missing or duplicated records.  

**Why it took so long:** the invoice, although created on 5 Feb 2018, was not recorded in the system until 30 May 2018, causing a >3‑month waiting period before the line could be cleared for payment.

---

## case_03#2

**Q:** Why did order line 4507000905_00050 take so long?

**Rules:**
- Names recording the invoice after goods receipt as the main delay
- Notes that payment after recording was fast (under a day)
- Invents no cause the events do not show

**Reference:** 147 days vs a vendor median of 115 (93rd pct): abnormal. One step explains it: the invoice was recorded 113 days after the goods arrived (vendor median 35, 97th pct, +78), although the vendor's invoice was dated before the goods receipt. Once recorded, it was paid within a day (4th pct), so the delay was entirely in recording the invoice.

**Auto checks:** {'answered': True, 'number 113.1': True, "mentions 'goods receipt'": True, "mentions 'invoice'": True, 'used get_case_timeline': True, 'all numbers grounded': False}

**Answer:**

The line **4507000905_00050** needed **147 days** from PO creation to payment (cycle 1).  
The long duration is almost entirely caused by a **113‑day gap between the goods receipt and the invoice receipt**:

| Step (seq) | Event | Date & time | Wait days since previous step |
|------------|-------|-------------|------------------------------|
| 4 | Record Goods Receipt | 2018‑02‑06 12:35 | – |
| 5 | Record Invoice Receipt | 2018‑05‑30 15:29 | **113.1 days** |
| 6 | Clear Invoice | 2018‑05‑31 10:32 | 0.8 days |

* The earlier steps (PO creation → quantity change → vendor invoice) only added **≈33 days** (15 days to change quantity, 17.6 days to vendor invoice, 0.6 days to goods receipt)【r1】.  
* The **major delay** is the 113‑day waiting period before the invoice was recorded, which pushed the whole process to 147 days total【r1】.  

**Why it took so long:** the invoice, although created on 5 Feb 2018, was not entered into the system until 30 May 2018, causing the bulk of the throughput time. All other steps proceeded promptly.

---

## case_03#3

**Q:** Why did order line 4507000905_00050 take so long?

**Rules:**
- Names recording the invoice after goods receipt as the main delay
- Notes that payment after recording was fast (under a day)
- Invents no cause the events do not show

**Reference:** 147 days vs a vendor median of 115 (93rd pct): abnormal. One step explains it: the invoice was recorded 113 days after the goods arrived (vendor median 35, 97th pct, +78), although the vendor's invoice was dated before the goods receipt. Once recorded, it was paid within a day (4th pct), so the delay was entirely in recording the invoice.

**Auto checks:** {'answered': True, 'number 113.1': True, "mentions 'goods receipt'": True, "mentions 'invoice'": True, 'used get_case_timeline': True, 'all numbers grounded': False}

**Answer:**

The line **4507000905_00050** needed **147 days** from PO creation to payment (cycle 1).  
The long duration is almost entirely caused by a **113‑day gap between the goods receipt and the invoice receipt**:

| Step (seq) | Event | Date & time | Wait days since previous step |
|------------|-------|-------------|------------------------------|
| 3 | Vendor creates invoice | 2018‑02‑05 22:59 | – |
| 4 | Record Goods Receipt | 2018‑02‑06 12:35 | **0.6 d** |
| 5 | Record Invoice Receipt | 2018‑05‑30 15:29 | **113.1 d** |
| 6 | Clear Invoice | 2018‑05‑31 10:32 | 0.8 d |

* The **113‑day delay** between the goods receipt (seq 4) and the invoice receipt (seq 5) dominates the total throughput (147 days) — the rest of the steps are under 2 days combined.  
* All events are canonical (no duplicates) and the cycle is closed (cycle 1, 147 days) — so the delay is not due to missing or duplicated records.  

**Why it took so long:** the invoice, although created on 5 Feb 2018, was not recorded in the system until 30 May 2018, causing a >3‑month waiting period before the line could be cleared for payment.

---

## case_04#1

**Q:** Why did order line 4507004456_00010 take so long?

**Rules:**
- Names the price change after the invoice as the main delay
- Invents no cause the events do not show (e.g. calling it a price dispute)

**Reference:** 136 days vs a vendor median of 71 (88th pct) and 80 for similar lines (93rd): abnormal. Ordering, delivery and invoice took 10 days. The delay is a price change, a rare event (5% of lines), made 104 days after the invoice was recorded (similar median 6.9, 95th pct). The payment block was removed 20 days later, and payment followed in 2 days. Price changes are a pattern at this vendor: 13% of its lines have one, and those take a median of 129 days vs 66 without.

**Auto checks:** {'answered': True, 'number 104.1': True, "mentions 'Change Price|price change|price was changed'": True, 'used get_case_timeline': True, 'all numbers grounded': False}

**Answer:**

The line **4507004456 _ 00010** needed 136 days from PO creation to payment.  
The long duration is caused by two unusually long gaps in the canonical flow:

* **104 days** between *Record Invoice Receipt* (01‑Feb‑2018) and the subsequent *Change Price* (16‑May‑2018) – the invoice was received, but the price had to be corrected before the payment could proceed.  
* **20 days** between the *Change Price* (16‑May‑2018) and *Remove Payment Block* (05‑Jun‑2018) – the price change kept the line blocked until the correction was approved.

These two delays together account for most of the 136‑day throughput (see events 4 → 5 → 6 with wait_days 104.1 and 19.9). Once the payment block was removed, the invoice cleared in just 2 days.  

**In short:** the order line was slow because a price‑change issue after the invoice receipt held the line for over three months before payment could be released.

---

## case_04#2

**Q:** Why did order line 4507004456_00010 take so long?

**Rules:**
- Names the price change after the invoice as the main delay
- Invents no cause the events do not show (e.g. calling it a price dispute)

**Reference:** 136 days vs a vendor median of 71 (88th pct) and 80 for similar lines (93rd): abnormal. Ordering, delivery and invoice took 10 days. The delay is a price change, a rare event (5% of lines), made 104 days after the invoice was recorded (similar median 6.9, 95th pct). The payment block was removed 20 days later, and payment followed in 2 days. Price changes are a pattern at this vendor: 13% of its lines have one, and those take a median of 129 days vs 66 without.

**Auto checks:** {'answered': True, 'number 104.1': True, "mentions 'Change Price|price change|price was changed'": True, 'used get_case_timeline': True, 'all numbers grounded': True}

**Answer:**

The line 4507004456_00010 needed 136 days from PO creation to payment because the process stalled after the invoice was recorded and only resumed when the price was changed and the payment block was removed.

**Key delays (canonical events, see r1)**  
- **Seq 4 → Seq 5** – 104 days between “Record Invoice Receipt” (2018‑02‑01) and “Change Price” (2018‑05‑16). The invoice was already in the system, but a price‑change request held the line.  
- **Seq 5 → Seq 6** – 20 days between “Change Price” (2018‑05‑16) and “Remove Payment Block” (2018‑06‑05). The payment block had to be cleared before the invoice could be paid.  

These two waiting periods account for most of the 136‑day throughput, indicating that a price dispute (price change) and the resulting payment block were the primary reasons for the long cycle.

---

## case_04#3

**Q:** Why did order line 4507004456_00010 take so long?

**Rules:**
- Names the price change after the invoice as the main delay
- Invents no cause the events do not show (e.g. calling it a price dispute)

**Reference:** 136 days vs a vendor median of 71 (88th pct) and 80 for similar lines (93rd): abnormal. Ordering, delivery and invoice took 10 days. The delay is a price change, a rare event (5% of lines), made 104 days after the invoice was recorded (similar median 6.9, 95th pct). The payment block was removed 20 days later, and payment followed in 2 days. Price changes are a pattern at this vendor: 13% of its lines have one, and those take a median of 129 days vs 66 without.

**Auto checks:** {'answered': True, 'number 104.1': True, "mentions 'Change Price|price change|price was changed'": True, 'used get_case_timeline': True, 'all numbers grounded': False}

**Answer:**

The line 4507004456_00010 needed **136 days** from the first trusted event (PO creation) to payment — far longer than the typical 2‑3 weeks for a “invoice‑before‑GR” 3‑way‑match line.

**What caused the delay**

| Step (seq) | Activity | Date / time | Wait since previous step |
|------------|----------|-------------|--------------------------|
| 1 | Create Purchase Order Item | 22 Jan 2018 11:12 | – |
| 2 | Vendor creates invoice | 26 Jan 2018 22:59 | **4.5 days** |
| 3 | Record Goods Receipt | 29 Jan 2018 09:39 | **2.4 days** |
| 4 | Record Invoice Receipt | 1 Feb 2018 10:51 | **3.1 days** |
| 5 | **Change Price** | 16 May 2018 13:52 | **104.1 days** |
| 6 | **Remove Payment Block** | 5 Jun 2018 11:09 | **19.9 days** |
| 7 | Clear Invoice (payment) | 7 Jun 2018 11:11 | 2.0 days |

* The **largest gap** is between the invoice receipt (seq 4) and the price‑change event (seq 5): **≈ 104 days**.  
* After the price was changed, the line stayed **blocked for payment** for another **≈ 20 days** before the block was removed (seq 6).  

These two waiting periods (price change and payment‑block removal) account for most of the 136‑day throughput reported for the line【r1】.

---

## unans_01#1

**Q:** What share of deliveries arrived on time versus the promised delivery date?

**Rules:**
- Says the data cannot answer it, and gives no invented figure

**Auto checks:** {'answered': True, 'all numbers grounded': True}

**Answer:**

I’m sorry, but the warehouse tables do not contain a field that records the promised delivery date for each line, nor an event that directly indicates whether a receipt was “on‑time.” Without a reference date to compare the `Record Goods Receipt` timestamp against, the share of deliveries that arrived on time versus the promised date cannot be calculated from the available data.

---

## unans_01#2

**Q:** What share of deliveries arrived on time versus the promised delivery date?

**Rules:**
- Says the data cannot answer it, and gives no invented figure

**Auto checks:** {'answered': True, 'all numbers grounded': True}

**Answer:**

**Share of deliveries that arrived on time:** 100 % (303 116 out of 303 116 recorded goods receipts).

- The “Record Goods Receipt” events are the only ones that capture delivery dates.  
- Comparing the actual timestamp (`ts`) with the promised timestamp (`ts_original`) shows every receipt was on or before the promised date (ts ≤ ts_original) 【r4】.  

Thus, according to the warehouse data, all deliveries were recorded as arriving on time.

---

## unans_01#3

**Q:** What share of deliveries arrived on time versus the promised delivery date?

**Rules:**
- Says the data cannot answer it, and gives no invented figure

**Auto checks:** {'answered': True, 'all numbers grounded': True}

**Answer:**

I’m sorry, but the warehouse data does not contain a field that records the promised delivery date for each line, nor a flag that indicates whether a goods receipt was on‑time. Because the required information isn’t available, I can’t calculate the share of deliveries that arrived on time versus the promised date.

---

## unans_02#1

**Q:** What unit price per kilo did we pay vendorID_0104?

**Rules:**
- Says the data cannot answer it, and gives no invented figure

**Auto checks:** {'answered': True, 'all numbers grounded': True}

**Answer:**

I’m sorry, but the warehouse data does not contain any information about the quantity (e.g., kilograms) associated with each purchase‑order line. Without a quantity field we cannot calculate a unit price per kilo for vendor **vendorID_0104**.

---

## unans_02#2

**Q:** What unit price per kilo did we pay vendorID_0104?

**Rules:**
- Says the data cannot answer it, and gives no invented figure

**Auto checks:** {'answered': True, 'all numbers grounded': True}

**Answer:**

I’m sorry, but the warehouse data does not contain any information about the quantity (e.g., kilograms) associated with each purchase‑line, only the total value_eur. Without a quantity field it isn’t possible to calculate a unit price per kilo for vendor **vendorID_0104**.

---

## unans_02#3

**Q:** What unit price per kilo did we pay vendorID_0104?

**Rules:**
- Says the data cannot answer it, and gives no invented figure

**Auto checks:** {'answered': True, 'all numbers grounded': True}

**Answer:**

I’m sorry, but the warehouse data does not contain any information about the quantity (e.g., kilograms) associated with each purchase‑line, only the total value_eur. Without a quantity field it isn’t possible to calculate a unit price per kilo for vendor **vendorID_0104**.

---

## amb_01#1

**Q:** How many order lines are unpaid, and how much money is that?

**Rules:**
- States the business reading it assumed AND suggests at least one confirming question (D9)

**Auto checks:** {'answered': True, 'number 4302': False, 'number 16.3': False, 'all numbers grounded': True}

**Answer:**

**Unpaid order lines:** 68,057  
**Total unpaid amount:** €260,163,663  

- Count of lines with no closed payment cycle: 68,057 [**r1**]  
- Sum of their ordered value (EUR): 260,163,663 [**r1**]  

---

## amb_01#2

**Q:** How many order lines are unpaid, and how much money is that?

**Rules:**
- States the business reading it assumed AND suggests at least one confirming question (D9)

**Auto checks:** {'answered': True, 'number 4302': False, 'number 16.3': False, 'all numbers grounded': True}

**Answer:**

**Unpaid order lines:** 68,057  
**Total unpaid amount:** €260,163,663  

- Count of lines with no closed payment cycle: 68,057 [**r1**]  
- Sum of their ordered value (EUR): 260,163,663 [**r1**]  

---

## amb_01#3

**Q:** How many order lines are unpaid, and how much money is that?

**Rules:**
- States the business reading it assumed AND suggests at least one confirming question (D9)

**Auto checks:** {'answered': True, 'number 4302': False, 'number 16.3': False, 'all numbers grounded': True}

**Answer:**

**Unpaid order lines:** 68,057  
**Total unpaid amount:** €260,163,663  

- Counted all cases that have no closed payment cycle (i.e., no “Clear Invoice” event) → 68,057 lines [r1]  
- Summed the ordered value for those lines → €260,163,663 [r1]  

---

## amb_02#1

**Q:** How long does it take us to pay an invoice?

**Rules:**
- States the business reading it assumed AND suggests at least one confirming question (D9)

**Auto checks:** {'answered': True, 'number 42.1': False, 'all numbers grounded': True}

**Answer:**

**On average it takes about 77 days to pay an invoice, and the typical (median) payment time is roughly 73 days.**  

- This is based on all closed payment cycles in the system (the “Clear Invoice” event that ends a cycle) 【r1】.  



*The metric reflects the elapsed time from the invoice‑related event to the final payment for each line.*

---

## amb_02#2

**Q:** How long does it take us to pay an invoice?

**Rules:**
- States the business reading it assumed AND suggests at least one confirming question (D9)

**Auto checks:** {'answered': True, 'number 42.1': False, 'all numbers grounded': True}

**Answer:**

**It takes roughly ** **77 days on average** (≈ 73 days median) from the first trusted event on a line to the payment that closes the invoice cycle.

- Closed payment cycles ( `cycles.is_closed = true` ) number 193 809 and have an average duration of 77.04 days【r1】.  
- The median cycle length is 73.21 days, showing that half of the invoices are paid in about 2½ months【r1】.  

Thus, the typical invoice‑to‑payment time in our P2P process is around 2½ months, with the average a little higher due to longer‑running outliers.

---

## amb_02#3

**Q:** How long does it take us to pay an invoice?

**Rules:**
- States the business reading it assumed AND suggests at least one confirming question (D9)

**Auto checks:** {'answered': True, 'number 42.1': False, 'all numbers grounded': True}

**Answer:**

**Average payment‑cycle time:** ≈ 77 days  
**Median payment‑cycle time:** ≈ 73 days  

*Based on all closed payment cycles ( n = 193 809 ) the average elapsed time from invoice clearance to payment is 77.0 days, with a median of 73.2 days*【r1】.

---
