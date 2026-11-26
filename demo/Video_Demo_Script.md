# Market POS Video Demo Script

- **Target runtime** · 5 minutes 45 seconds.
- **Format** · 1080p screen recording, English narration, presentation slides interleaved with the running local register.

## Set up before recording

1. Activate the project environment and launch Flask using a fresh database as shown in the README. Open the printed URL in the browser.
2. Open the PPTX and set the browser zoom so the basket and summary fit side by side. Confirm the Products page lists milk at 40 units and sourdough at 28 units.
3. Keep the automated test result ready. Use the sale number produced on screen. A fresh database normally starts at Sale #1.
4. Use the PPTX for context and design, then switch to the running system. Keep the live checkout and return contiguous so the viewer sees the original sale reference.

| Time | Screen and action | English narration |
|---|---|---|
| 0:00–0:25 | Slides 1–2. Introduce the system. | “This is Market POS, a register for a small supermarket. I will show a cash sale and a cash return against that same purchase. Both operations update the same inventory and leave a traceable receipt or voucher.” |
| 0:25–0:55 | Slides 3–5. Summarize the planned increments and use-case diagram. | “The Scrum plan is divided into three three-day Sprints. The first delivers checkout, the second adds returns, and the third prepares the system for repeatable assessment. The burndown shows simulated remaining effort. The cashier operates both core use cases at one system boundary.” |
| 0:55–1:25 | Slides 6–9. Point to the event sequence and original sale association. | “Process Sale follows the NextGen example. The cashier enters products, ends the sale, and records cash. Handle Returns starts from an original sale and confirms a quote. The domain model connects each returned line to the original item, and the architecture keeps the browser views separate from the business rules.” |
| 1:25–1:55 | Slides 10–12. Point to the controller and commit links. | “Register coordinates the system operations. Sale creates its lines and payment. Return uses the historical sale line and prior return quantities to calculate the refund. The SQLite session commits the transaction record and inventory together.” |
| 1:55–2:33 | Live Checkout. Select **New sale**. Add **1001 × 2** and **1002 × 1**. End the sale. | “I am buying two units of whole milk and one sourdough. As I add each product, its quantity and price update the basket. The subtotal is ten dollars and sixty-five cents, the tax is eighty-five cents, and the final total is eleven dollars and fifty cents.” |
| 2:33–3:14 | Enter **10.00**, record payment, then enter **20.00** and record. Point to receipt, change and recorded sale number. Optionally show milk stock **38** in Products. | “First I enter ten dollars to show the validation message. The register keeps the basket open for payment. I now enter twenty dollars. The receipt shows eight dollars and fifty cents in change. I will use this sale number on the Returns screen.” |
| 3:14–4:23 | Open **Returns**. Find the sale number. Attempt **1001 × 3**. Enter **1001 × 1**, review the quote, and select **Confirm cash refund**. | “The system displays the original purchase and remaining eligible quantities. Three milk units are rejected because only two were purchased. I select one unit. Its original price was three dollars and twenty cents. Its allocated tax is twenty-six cents, so the total cash refund is three dollars and forty-six cents. The voucher identifies the original sale.” |
| 4:23–4:56 | Open **Products**, show milk stock **39**, then **History**, open the original receipt or return voucher. | “The sale reduced milk stock from forty to thirty-eight. Returning one unit brings the quantity to thirty-nine. History keeps both records and I can open either document again.” |
| 4:56–5:45 | Slides 15–16. Briefly display the test terminal or result file. | “Seventeen automated tests passed. They check totals, change, invalid product and quantity inputs, persistence, rollback and concurrent returns. I also exercised the checkout and return workflow in the running browser. The final design keeps both transactions in one register and reconciles a refund to the original purchase.” |

## After recording

Review the recording for legible text and audible explanation. Upload it using the submitting Bilibili account. After publication, open the resulting video URL to confirm the intended audience can access it. Add that verified URL and the verified GitHub URL to the editable technical report and export the final PDF.
