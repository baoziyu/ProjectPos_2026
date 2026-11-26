# POS Testing Report

The automated suite ran on Python 3.12 with Flask 3.1.3 and SQLite on macOS. The run completed **17 tests with zero failures and zero errors**. Exact test names and outcomes are in the [unittest output](test_results.txt). Each automated test starts with a fresh temporary database.

## Coverage and observed outcomes

| Scenario | Test or evidence | Observed outcome |
|---|---|---|
| Normal single-product checkout and change | test_normal_sale_and_change | Two milk units cost $6.91. $10.00 produces $3.09 change and the stock decreases to 38. |
| Multiple products and repeated scans | test_multi_product_sale_and_repeated_scan | Two milk units and one sourdough total $11.50. Repeated milk entries merge into one sale line. |
| Unknown product | test_unknown_product | Error is raised and the basket remains empty. |
| Insufficient cash | test_insufficient_cash_does_not_commit | The sale and stock update are deferred until sufficient tender is recorded. |
| Normal cash refund and restocking | test_normal_refund_restores_stock | One milk unit refunds $3.46, references the original sale, and restores stock to 39. |
| Excess return quantity | test_refund_beyond_remaining_quantity | A second return cannot claim beyond the remaining original quantity. |
| Unknown source sale or return SKU | test_unknown_original_sale_and_return_product | An unknown sale, unknown SKU and unrelated catalog SKU are rejected. |
| Historical price and exact tax | test_historical_price_and_exact_partial_returns | Two refund amounts of $3.46 and $3.45 sum to the original $6.91 despite a later catalog edit. |
| Changed refund quote | test_stale_refund_quote_does_not_commit | A stale amount is rejected, with no extra return or stock movement. |
| SQLite restart and relationship consistency | test_sqlite_persistence_and_integrity | Transactions and stock survive reopening. SQLite reports integrity OK and zero foreign-key violations. |
| Rollback after partial work | test_stale_sale_rolls_back_every_write | A stale stock level causes rollback of the sale header and earlier stock update. |
| Duplicate submissions | test_duplicate_sale_and_refund_requests_are_idempotent | Each draft commits once and retries receive the existing identifier. |
| Concurrent returns | test_concurrent_returns_cannot_both_claim_last_unit | Exactly one request claims the last eligible unit and restores stock. |
| Catalog maintenance and money validation | test_product_validation_and_search and test_product_create_edit_and_search | New and edited records can be found, duplicate code is rejected and invalid money is detected. |
| Flask checkout, return and history | test_checkout_to_refund_and_history | The web flow rejects low tender, issues receipt and voucher, and lists both records. |
| Missing receipt and expired form | test_invalid_receipt_and_missing_csrf | The application returns HTTP 404 and HTTP 400 respectively. |

## Running browser evidence

Chrome exercised the Flask application using a separate seeded database on loopback. The scenario checked that the sale total was $11.50, $10.00 was rejected, $20.00 yielded $8.50 change, three milk units were rejected for return, and the accepted one-unit refund was $3.46. The browser opened the linked voucher and confirmed the restored milk stock of 39. Captures are in [demo/screenshots](../../demo/screenshots/).

The automated evidence covers the local software flow and SQLite persistence. Cash handover, physical scanner hardware, durable printer output and external payment or accounting integrations are outside the verification scope.
