# UC02 Handle Returns

- **Scope** · Market POS software for a small supermarket.
- **Level** · User goal.
- **Primary actor** · Cashier.
- **Trigger** · A customer presents merchandise to return and identifies the original sale.

## Stakeholders and interests

- Cashier wants to identify the purchase, see quantities still returnable and confirm the right amount before handing over cash.
- Customer wants a refund based on the purchase amounts and a voucher documenting the return.
- Store manager wants traceable refunds, protection against duplicate or excessive returns, and correct stock restoration.

## Preconditions and guarantees

The cashier has access to the local register. Merchandise has been checked by the cashier as suitable for restocking. The customer has a sale number or the cashier can identify it in History.

On success, the POS persists a return linked to the original sale and each original line, records the cash refund, restores selected quantities to stock once, and makes a printable voucher available. A validation or database failure rolls back the refund and its stock movement.

## Main success scenario

1. The customer presents the merchandise and identifies the original purchase.
2. The cashier starts a return by entering the sale number. The POS shows its original lines, purchased quantities, and quantities still returnable.
3. The cashier scans or types a product code and enters the quantity.
4. The POS checks membership in the original sale and the remaining allowance, then presents the selection and the updated refund quote. The cashier repeats steps 3–4 as needed.
5. The cashier verifies the total and confirms a cash refund. The POS revalidates the selections and the quoted amount against committed records, then saves the return and restores stock in one transaction.
6. The POS presents the voucher and cash amount. The cashier hands over the cash and voucher.

## Extensions

| Step | Condition | System and cashier response |
|---|---|---|
| 2a | Sale reference missing or unknown | Try the correct reference or use History to identify a recent sale. The original sale is required to proceed. |
| 3–4a | Code unreadable or missing from the original sale | Try manual code entry or inspect the original receipt. The POS rejects an unmatched code. |
| 4b | Selected quantity exceeds bought quantity minus prior refunds | Show the error and keep the earlier selection. The cashier reduces the quantity or removes the selection. |
| 5a | No selected items, stale quantity, or invalid or changed quote | Block the commit. The cashier reviews the current remaining quantities and refund amount before confirming again. |
| 5b | Cashier cannot issue cash or customer abandons the return before confirmation | Cancel the open return. The POS discards the draft without refunding or changing stock. |
| 5c | Local database unavailable or stock update fails | The POS rolls back the transaction. Fix the issue and retry. Where the outcome is unclear after a lost response, check History before retrying with a new draft. |
| 5d | External refund provider rejects a refund or accounting is unreachable in the textbook scenario | These external integrations are outside this release. A future integrated version must surface the failure and reconcile the transaction outcome before retry. Any cash fallback requires an explicit refund policy and cashier confirmation. |
| 6a | Voucher printing fails or the cashier has trouble handing over cash after commitment | Reopen the voucher for printing. Escalate a cash-handoff discrepancy to the store manager for manual reconciliation before any further cash movement. |

## Special requirements and variations

Original price and recorded line tax drive the refund. Cumulative round-half-up allocation makes full reversal equal the original tax, even after multiple partial returns. The cashier completes physical cash handover after the voucher appears. The register handles receipted, restockable returns only.

- **Frequency** · As customers return eligible purchases.
- **References** · Larman, *Applying UML and Patterns*, 3rd ed., §6.2, §6.8 and chapters 10 and 18. See [system sequence diagram](../diagrams/03-ssd-return.svg) and [design sequence diagram](../diagrams/07-sequence-return.svg).
