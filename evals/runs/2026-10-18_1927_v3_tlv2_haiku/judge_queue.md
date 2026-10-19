# Judge queue

Grade each answer pass/fail against its rules into judgments.json:
`{"<id>#<repeat>": {"pass": true, "notes": "..."}}`

## h2_biggest_vendor#1

**Q:** Who is our biggest vendor?

**Rules:**
- States the business reading it assumed AND suggests at least one confirming question (D9)

**Reference:** Interprets "biggest" as highest ordered value (sum of line value at creation): vendorID_0104 at about EUR 32.1M (3.2% of total), ahead of vendorID_0159 (EUR 30.3M) and vendorID_0106 (EUR 24.7M). States the assumption, notes that by order-line count the answer would be vendorID_0136 (14,471 lines), and asks whether the user meant spend, volume or something else.

**Auto checks:** {'answered': True, 'number 3.21045e+07': True, "mentions 'vendorID_0104'": True, 'all numbers grounded': True}

**Answer:**

Our biggest vendor by ordered value is vendorID_0104, with 32,104,521 EUR across 9,817 order lines, about 3.2% of total ordered spend [r1].

- Next largest: vendorID_0159 (30,251,481 EUR, 968 lines, 3.0%) and vendorID_0106 (24,691,895 EUR, 7,231 lines, 2.5%) [r1].
- vendorID_0104 also has the most order lines of the top five [r1].

Assumptions: "Biggest" means total ordered value (cases.value_eur) across all order lines, not amount paid or invoiced. Lines of every item category are included.

To confirm: Do you want this ranked by amount paid (closed invoices) instead? Should it be limited to a specific company or spend area?

---

## h2_biggest_vendor#2

**Q:** Who is our biggest vendor?

**Rules:**
- States the business reading it assumed AND suggests at least one confirming question (D9)

**Reference:** Interprets "biggest" as highest ordered value (sum of line value at creation): vendorID_0104 at about EUR 32.1M (3.2% of total), ahead of vendorID_0159 (EUR 30.3M) and vendorID_0106 (EUR 24.7M). States the assumption, notes that by order-line count the answer would be vendorID_0136 (14,471 lines), and asks whether the user meant spend, volume or something else.

**Auto checks:** {'answered': True, 'number 3.21045e+07': True, "mentions 'vendorID_0104'": True, 'all numbers grounded': True}

**Answer:**

Vendor vendorID_0104 is the biggest by ordered value: 32,104,521.00 EUR across 9,817 order lines, 3.2% of total ordered value [r1].

- It also has the most order lines of any vendor [r1].
- The next largest are vendorID_0159 (30,251,481.00 EUR, 3.0%) and vendorID_0106 (24,691,895.00 EUR, 2.5%) [r1].

Assumptions: 'biggest' means total value ordered (cases.value_eur), summed over all order lines per vendor. The data has no paid amounts per vendor, so this is not spend actually paid.

To confirm: Do you want the ranking by value paid (closed invoices) instead? Or by number of order lines?

---

## h2_biggest_vendor#3

**Q:** Who is our biggest vendor?

**Rules:**
- States the business reading it assumed AND suggests at least one confirming question (D9)

**Reference:** Interprets "biggest" as highest ordered value (sum of line value at creation): vendorID_0104 at about EUR 32.1M (3.2% of total), ahead of vendorID_0159 (EUR 30.3M) and vendorID_0106 (EUR 24.7M). States the assumption, notes that by order-line count the answer would be vendorID_0136 (14,471 lines), and asks whether the user meant spend, volume or something else.

**Auto checks:** {'answered': True, 'number 3.21045e+07': True, "mentions 'vendorID_0104'": True, 'all numbers grounded': True}

**Answer:**

Vendor vendorID_0104 is your biggest vendor by ordered value: 32,104,521.00 EUR across 9,817 order lines, about 3.2% of total ordered value [r1].

- Next largest: vendorID_0159 at 30,251,481.00 EUR (968 lines, 3.0%) [r1].
- The top 10 vendors together are listed in [r1], ranging from 16,305,609.00 EUR to 32,104,521.00 EUR.
- vendorID_0104 also has the most order lines of the top 10 (9,817) [r1].

Assumptions: 'Biggest' means total ordered value (value_eur on order lines) across all item categories and all orders in the data, which covers orders created in 2018. This is the ordered amount, not the amount paid or invoiced.

To confirm: Do you want the ranking by ordered value (as shown) or by number of order lines? Should it be restricted to a specific period, company, or spend area?

---

## h2_promised_date#1

**Q:** What percentage of our purchase orders were delivered after the delivery date the vendor promised?

**Rules:**
- Says the data cannot answer it, and gives no invented figure

**Auto checks:** {'answered': True, 'all numbers grounded': True}

**Answer:**

The data cannot answer this. The warehouse has no promised or planned delivery dates, so I cannot tell whether any purchase order arrived after the vendor's promised date.

To answer it, the promised delivery date would need to be added to the extract, for example as a field on each order line. Could you check whether that date exists in the source purchase-order system?

I can still show when goods receipts were recorded relative to order creation, if that helps. For example: What is the median number of days from order creation to the first goods receipt, by item category?

---

## h2_promised_date#2

**Q:** What percentage of our purchase orders were delivered after the delivery date the vendor promised?

**Rules:**
- Says the data cannot answer it, and gives no invented figure

**Auto checks:** {'answered': True, 'all numbers grounded': True}

**Answer:**

The data cannot answer this. The warehouse has no promised or planned delivery dates, so I cannot calculate the share of purchase orders delivered late against the vendor's promise.

What the data does contain is the timing of 'Record Goods Receipt' events, which shows when goods were received. I can calculate how long goods receipt takes after ordering, but that is not a comparison against a promised date.

To confirm: Do you have the promised delivery dates in a separate system, such as the purchase order confirmation or the vendor's order acknowledgement? If you can supply them, I can compare them against goods receipt dates.

---

## h2_promised_date#3

**Q:** What percentage of our purchase orders were delivered after the delivery date the vendor promised?

**Rules:**
- Says the data cannot answer it, and gives no invented figure

**Auto checks:** {'answered': True, 'all numbers grounded': True}

**Answer:**

I can't answer this from the data. The warehouse has no promised or planned delivery dates, so there is no baseline to compare actual delivery against, and I won't use another column as a substitute. The events show when goods receipts were recorded, but not when the vendor promised delivery. If you can export the promised delivery dates from the purchasing system and add them to the data, I can calculate the share of late deliveries. In the meantime, I can report the share of order lines that have a goods receipt recorded, if that helps.

---

## h2_why_slow_line#1

**Q:** Why did order line 4508051115_00050 take so long?

**Rules:**
- Names the Remove Payment Block -> Clear Invoice wait (about 115 days, from 17 Sep 2018 to 10 Jan 2019) as the main delay
- Gives the line total as about 139 days and shows the other gaps are small (Create PO -> Goods Receipt about 18 days, the rest under 6 days)
- Compares the long wait with the same gap at vendorID_0136 (median about 100 days, so typical for this vendor, roughly the 87th percentile) and/or across all vendors (median about 25 days, about the 98th percentile)
- Does not claim the payment was due or overdue, and invents no cause (e.g. dispute, cash-flow decision, payment terms) that the events do not show

**Reference:** The line took 139 days in total, and 114.9 of them (about 83%) sit between Remove Payment Block (17 Sep 2018) and Clear Invoice (10 Jan 2019); goods were received after 18 days and the invoice was received and unblocked within about 6 days of that. That wait is typical for vendorID_0136 (median 99.9 days over 5,465 such gaps, about the 87th percentile) but very long against all vendors (median 25.1 days, about the 98th percentile). The data does not show why payment took that long.

**Auto checks:** {'answered': True, 'number 139.1': True, 'number 114.9': True, "mentions 'Remove Payment Block|payment block'": True, "mentions 'Clear Invoice|paid|payment'": True, 'used get_case_timeline': True, 'all numbers grounded': True}

**Answer:**

Most of the time was one wait. The line took 139.14 days from creation (2018-08-24) to payment (2019-01-10) [r1]. The longest wait was 114.9 days between 'Remove Payment Block' (seq 5, event 1117219, 2018-09-17) and 'Clear Invoice' (seq 6, event 1117220, 2019-01-10). The events do not show why that wait happened.

- Remove Payment Block to Clear Invoice: 114.9 days. Similar lines (same category and value band) have a median of 16.7 days, and this wait is at the 99th percentile of their n=5,084 waits. The same vendor's median for this step is 99.9 days, at the 87th percentile [r1].
- Time to first payment: 139.14 days, against a similar-line median of 57.7 days (98th percentile) and a vendor median of 126.1 days (88th percentile) [r1].
- An earlier step was also slow: Create PO Item to Record Goods Receipt (seq 1 to 2, events 1117215 and 1117216) took 18.1 days, against a similar-line median of 6.4 days (90th percentile) [r1].
- Record Invoice Receipt to Remove Payment Block (seq 4 to 5) took 5.2 days, below the similar-line median of 8.5 days [r1].
- The line has one payment cycle, and it is closed [r1].

To confirm: Do you know the reason the payment block was removed about 115 days before payment? The event log does not record it. Should I check whether other lines from this vendor show the same long wait after the block is removed?

---

## h2_why_slow_line#2

**Q:** Why did order line 4508051115_00050 take so long?

**Rules:**
- Names the Remove Payment Block -> Clear Invoice wait (about 115 days, from 17 Sep 2018 to 10 Jan 2019) as the main delay
- Gives the line total as about 139 days and shows the other gaps are small (Create PO -> Goods Receipt about 18 days, the rest under 6 days)
- Compares the long wait with the same gap at vendorID_0136 (median about 100 days, so typical for this vendor, roughly the 87th percentile) and/or across all vendors (median about 25 days, about the 98th percentile)
- Does not claim the payment was due or overdue, and invents no cause (e.g. dispute, cash-flow decision, payment terms) that the events do not show

**Reference:** The line took 139 days in total, and 114.9 of them (about 83%) sit between Remove Payment Block (17 Sep 2018) and Clear Invoice (10 Jan 2019); goods were received after 18 days and the invoice was received and unblocked within about 6 days of that. That wait is typical for vendorID_0136 (median 99.9 days over 5,465 such gaps, about the 87th percentile) but very long against all vendors (median 25.1 days, about the 98th percentile). The data does not show why payment took that long.

**Auto checks:** {'answered': True, 'number 139.1': True, 'number 114.9': True, "mentions 'Remove Payment Block|payment block'": True, "mentions 'Clear Invoice|paid|payment'": True, 'used get_case_timeline': True, 'all numbers grounded': True}

**Answer:**

Line 4508051115_00050 took 139.14 days, from 2018-08-24 to 2019-01-10 [r1]. Most of that is one wait of 114.9 days between Remove Payment Block (seq 5, event 1117219, 2018-09-17) and Clear Invoice (seq 6, event 1117220, 2019-01-10). The events do not show why that gap occurred.

Evidence [r1]:
- Remove Payment Block to Clear Invoice (seq 5 to 6): 114.9 days. Same gap at the same vendor: median 99.9 days (87th percentile). Same gap at similar lines (same item category and value band): median 16.7 days (99th percentile, n=5,084).
- First payment: 139.14 days, against a vendor median of 126.1 days (88th percentile) and a similar-line median of 57.7 days (98th percentile).
- Invoice handling was not the slow part: the vendor invoice (seq 3) was recorded 0.6 days later (seq 4), and the payment block was removed 5.2 days after that (vendor median 5.9 days, similar-line median 8.5 days).
- The goods receipt came 18.1 days after PO creation (seq 1 to 2; vendor median 14.9 days, 80th percentile; similar-line median 6.4 days, 90th percentile). This is a smaller contributor.

Assumptions: throughput is measured from the first to the last trusted event. This line has one payment cycle, which is closed.

To confirm: Should I check whether other lines with a removed payment block also show long waits before Clear Invoice? Do you also want this line's open-invoice status?

---

## h2_why_slow_line#3

**Q:** Why did order line 4508051115_00050 take so long?

**Rules:**
- Names the Remove Payment Block -> Clear Invoice wait (about 115 days, from 17 Sep 2018 to 10 Jan 2019) as the main delay
- Gives the line total as about 139 days and shows the other gaps are small (Create PO -> Goods Receipt about 18 days, the rest under 6 days)
- Compares the long wait with the same gap at vendorID_0136 (median about 100 days, so typical for this vendor, roughly the 87th percentile) and/or across all vendors (median about 25 days, about the 98th percentile)
- Does not claim the payment was due or overdue, and invents no cause (e.g. dispute, cash-flow decision, payment terms) that the events do not show

**Reference:** The line took 139 days in total, and 114.9 of them (about 83%) sit between Remove Payment Block (17 Sep 2018) and Clear Invoice (10 Jan 2019); goods were received after 18 days and the invoice was received and unblocked within about 6 days of that. That wait is typical for vendorID_0136 (median 99.9 days over 5,465 such gaps, about the 87th percentile) but very long against all vendors (median 25.1 days, about the 98th percentile). The data does not show why payment took that long.

**Auto checks:** {'answered': True, 'number 139.1': True, 'number 114.9': True, "mentions 'Remove Payment Block|payment block'": True, "mentions 'Clear Invoice|paid|payment'": True, 'used get_case_timeline': True, 'all numbers grounded': True}

**Answer:**

Order line 4508051115_00050 took 139.14 days from creation to payment (cycle 1, closed), and almost all of that time was one wait: 114.9 days between 'Remove Payment Block' (seq 5, event 1117219, 2018-09-17) and 'Clear Invoice' (seq 6, event 1117220, 2019-01-10). [r1]

Assumptions: 'took so long' means the end-to-end time to payment for this line. The median is used for peer comparisons.

Evidence [r1]:
- The payment-block wait of 114.9 days is at the 99th percentile for similar lines (median 16.7 days, n = 5,084) and at the 87th percentile for this vendor (vendor median 99.9 days, n = 5,465).
- Time to first payment is 139.14 days, against a similar-line median of 57.7 days (98th percentile) and a vendor median of 126.1 days (88th percentile).
- Earlier steps were close to typical. Invoice receipt to block removal took 5.2 days (similar-line median 8.5). The invoice was recorded and the goods receipt happened before it, so the invoice was not waiting on goods.
- The purchase-order-to-goods-receipt wait of 18.1 days (seq 1 to 2) was slower than typical: 90th percentile for similar lines (median 6.4 days). It was not the main delay.

The events show when the payment block was removed and when the invoice cleared, but not what happened in between, so the cause of the 115-day gap is not visible in this data.

To confirm:
- Do you want the explanation for this one line, or a pattern across all lines with long payment blocks?
- Should I check whether the 115-day gap is common for this vendor's other lines?

---
