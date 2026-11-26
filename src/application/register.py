"""Application controller for Register system operations."""

from src.domain.model import PosError, Product, Return, ReturnLineItem, Sale, SalesLineItem
from src.infrastructure.sqlite_store import SQLiteStore


class Register:
    def __init__(self, store: SQLiteStore):
        self.store = store

    def make_new_sale(self) -> Sale:
        return Sale()

    def enter_item(self, sale: Sale, sku: str, qty: int) -> SalesLineItem:
        with self.store.session() as repo:
            product = repo.get_product(sku.strip().upper())
        return sale.add_item(product, qty)

    def end_sale(self, sale: Sale) -> int:
        sale.end()
        return sale.total

    def make_payment(self, sale: Sale, tender: int) -> int:
        with self.store.session(write=True) as repo:
            existing = repo.find_sale_token(sale.id)
            if existing is not None:
                return existing
            payment = sale.accept_cash(tender)
            return repo.persist_sale(sale, payment)

    def make_new_return(self, sale_id: int) -> Return:
        with self.store.session() as repo:
            repo.sale_items(sale_id)
        return Return(sale_id)

    def return_context(self, draft: Return) -> tuple[dict[str, SalesLineItem], dict[str, int]]:
        with self.store.session() as repo:
            source = repo.sale_items(draft.sale_id)
            returned = repo.returned_quantities(draft.sale_id)
        return source, returned

    def enter_return_item(self, draft: Return, sku: str, qty: int) -> ReturnLineItem:
        source, returned = self.return_context(draft)
        sku = sku.strip().upper()
        if sku not in source:
            raise PosError(f"Product {sku or '(empty code)'} is not on this sale.")
        return draft.add_item(source[sku], qty, returned.get(sku, 0))

    def refund_cash(self, draft: Return, expected: int) -> int:
        with self.store.session(write=True) as repo:
            existing = repo.find_return_token(draft.id)
            if existing is not None:
                return existing
            source = repo.sale_items(draft.sale_id)
            returned = repo.returned_quantities(draft.sale_id)
            lines = draft.quote(source, returned)
            if sum(line.subtotal + line.tax for line in lines) != expected:
                raise PosError("Refund quote changed. Review the new total before confirming.")
            return repo.persist_return(draft, lines)

    def products(self, query: str = "") -> list[Product]:
        with self.store.session() as repo:
            return repo.list_products(query)

    def save_product(self, product: Product, *, create: bool) -> None:
        with self.store.session(write=True) as repo:
            repo.save_product(product, create=create)

    def receipt(self, kind: str, number: int):
        with self.store.session() as repo:
            return repo.receipt(kind, number)

    def recent(self, kind: str):
        with self.store.session() as repo:
            return repo.recent(kind)
