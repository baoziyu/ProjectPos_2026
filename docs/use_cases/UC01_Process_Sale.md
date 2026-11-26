# UC01 Process Sale

- **Scope** · Market POS software for a small supermarket.
- **Level** · User goal.
- **Primary actor** · Cashier.
- **Trigger** · A customer arrives with items to purchase.

## Stakeholders and interests

- Cashier wants fast item entry, visible totals, and the correct change.
- Customer wants accurate prices and a receipt as proof of purchase.
- Store manager wants an auditable cash transaction and accurate stock levels.

## Preconditions and guarantees

The cashier has access to a running register with an available local database. Products intended for sale have catalog records. The demo treats access to the local register as authorization.

A successful sale records original item names and prices, quantities, tax, cash tender, and change. Stock is reduced once, the completed sale is assigned a receipt number, and a printable receipt is available. An unsuccessful commit leaves the stored sale, payment and stock unchanged.

## Main success scenario

1. The customer brings products to the checkout.
2. The cashier starts a new sale. The POS opens an empty basket.
3. The cashier scans or types a product code and enters the quantity.
4. The POS presents the matched line and updates the subtotal and running total. The cashier repeats steps 3–4 for the remaining products.
5. The cashier ends the sale. The POS presents the final tax-inclusive amount.
6. The cashier requests and receives cash from the customer, then enters the amount received.
7. The POS validates tender, calculates change, records the sale and payment, and reduces stock in one database transaction.
8. The POS shows the receipt and change due. The cashier gives the change and receipt to the customer.

## Extensions

| Step | Condition | System and cashier response |
|---|---|---|
| 3–4a | Scan unreadable, product unknown, quantity invalid or stock insufficient | The POS explains the problem and preserves the other lines. The cashier retries with a valid code or quantity. |
| 4b | An entered line is incorrect | The cashier removes the line and re-enters it if needed. |
| 5a | Basket empty or amount exceeds register limit | The POS keeps the basket open. The cashier corrects the basket before trying again. |
| 5b | Cashier finds an error after ending the sale | The cashier reopens the basket and resumes at step 3. |
| 6–7a | Invalid or insufficient tender | The POS requests corrected tender. No sale or stock adjustment is recorded. |
| 7b | Stock changed or local persistence failed | The POS reports the condition and rolls back every write. The cashier adjusts the basket or retries after recovery. If the outcome is unclear following a lost response, the cashier checks History before starting a duplicate sale. |
| 8a | Printing is unavailable | The completed sale remains committed. The cashier can reopen its receipt from History and print it later. |
| 2–7c | Cashier cancels the draft before commitment | The POS discards it without changing stock or history. |

## Special requirements and variations

The interface accepts manual entry or a keyboard-wedge scanner that submits the code like keyboard input. Money is stored in integer cents and the fixed 8% demonstration tax is rounded half up per sale line. The browser prints receipts. Duplicated commit requests with the same draft identifier resolve to the original commit. The course implementation uses local stock and cash. The external accounting, inventory and payment services in Larman’s full NextGen scenario fall outside this release.

- **Frequency** · Many times per business day.
- **References** · Larman, *Applying UML and Patterns*, 3rd ed., §6.8 and chapters 10 and 18. See [system sequence diagram](../diagrams/02-ssd-sale.svg) and [design sequence diagram](../diagrams/06-sequence-sale.svg).
