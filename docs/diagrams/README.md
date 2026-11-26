# UML diagrams

| Figure | Diagram | SVG | PlantUML source |
|---|---|---|---|
| 2 | Use case boundary | [SVG](01-use-cases.svg) | [PUML](01-use-cases.puml) |
| 3 | Process Sale system sequence | [SVG](02-ssd-sale.svg) | [PUML](02-ssd-sale.puml) |
| 4 | Handle Returns system sequence | [SVG](03-ssd-return.svg) | [PUML](03-ssd-return.puml) |
| 5 | Conceptual domain class model | [SVG](04-domain-model.svg) | [PUML](04-domain-model.puml) |
| 6 | Logical architecture package diagram | [SVG](05-logical-architecture.svg) | [PUML](05-logical-architecture.puml) |
| 7 | Process Sale object sequence | [SVG](06-sequence-sale.svg) | [PUML](06-sequence-sale.puml) |
| 8 | Handle Returns object sequence | [SVG](07-sequence-return.svg) | [PUML](07-sequence-return.puml) |
| 9 | Cash sale communication | [SVG](08-communication-sale.svg) | [PUML](08-communication-sale.puml) |
| 10 | Cash return communication | [SVG](09-communication-return.svg) | [PUML](09-communication-return.puml) |
| 11 | Shared design class model | [SVG](10-design-classes.svg) | [PUML](10-design-classes.puml) |

PNG exports share the same stems. Regenerate with a local PlantUML JAR that includes Smetana. Run inside this directory.

```bash
java -jar /path/to/plantuml.jar -failfast2 -tsvg 0*.puml 10*.puml
java -jar /path/to/plantuml.jar -failfast2 -tpng -Sdpi=190 0*.puml 10*.puml
```

## Relationships to the implementation

| System event | Application method | Collaborators |
|---|---|---|
| makeNewSale | Register.make_new_sale | Constructs Sale |
| enterItem | Register.enter_item | SQLiteSession.get_product, Sale.add_item |
| endSale | Register.end_sale | Sale.end and Sale.total |
| makePayment | Register.make_payment | SQLiteSession.find_sale_token, Sale.accept_cash, SQLiteSession.persist_sale |
| makeNewReturn | Register.make_new_return | SQLiteSession.sale_items and Return constructor |
| enterReturnItem | Register.enter_return_item | Register.return_context, SQLiteSession.sale_items and returned_quantities, Return.add_item |
| refundCash | Register.refund_cash | SQLiteSession.find_return_token, sale_items and returned_quantities, Return.quote, SQLiteSession.persist_return |

The SSDs model observable system events. The named sequences refine these into Python calls. Repository lifelines denote an ephemeral session role. Communication views show the commit interactions and ordered calls. A conceptual Product Description and Stock Record map to one Product record; a receipt or voucher is a view generated from stored transaction data. Cash settlement is stored with the sale header.
