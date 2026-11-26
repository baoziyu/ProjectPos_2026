"""Cash-register concepts and rules for exact, auditable money calculations."""

from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from uuid import uuid4


class PosError(Exception):
    """An operation the cashier can correct or retry."""


MAX_CENTS = 999_999_999
TAX_BPS = 800


def cents(value: str) -> int:
    try:
        amount = Decimal(value.strip())
        if not amount.is_finite() or not 0 <= amount <= Decimal(MAX_CENTS) / 100:
            raise ValueError
        rounded = amount.quantize(Decimal("0.01"))
        if rounded != amount:
            raise ValueError
        return int(rounded * 100)
    except (AttributeError, InvalidOperation, ValueError) as error:
        raise PosError("Enter a nonnegative amount with at most two decimal places.") from error


def money(amount: int) -> str:
    return f"${amount // 100:,}.{amount % 100:02}"


def positive_quantity(value: int) -> int:
    if type(value) is not int or not 1 <= value <= 10000:
        raise PosError("Enter a whole quantity from 1 to 10,000.")
    return value


def rounded_ratio(numerator: int, denominator: int) -> int:
    return (2 * numerator + denominator) // (2 * denominator)


@dataclass(frozen=True)
class Product:
    sku: str
    name: str
    price_cents: int
    stock: int

    def __post_init__(self):
        if not self.sku or len(self.sku) > 24 or not all(
            ch.isascii() and (ch.isalnum() or ch in "-_") for ch in self.sku
        ):
            raise PosError("Use a product code of 1 to 24 letters, digits, hyphens or underscores.")
        if not self.name or len(self.name) > 80:
            raise PosError("Enter a product name of 1 to 80 characters.")
        if type(self.price_cents) is not int or not 0 < self.price_cents <= MAX_CENTS:
            raise PosError("Enter a positive unit price.")
        if type(self.stock) is not int or not 0 <= self.stock <= 10_000_000:
            raise PosError("Enter a whole stock count from 0 to 10,000,000.")


@dataclass(frozen=True)
class SalesLineItem:
    sku: str
    name: str
    price_cents: int
    qty: int
    recorded_tax: int | None = None

    @property
    def subtotal(self) -> int:
        return self.price_cents * self.qty

    @property
    def tax(self) -> int:
        if self.recorded_tax is not None:
            return self.recorded_tax
        return rounded_ratio(self.subtotal * TAX_BPS, 10000)


@dataclass(frozen=True)
class CashPayment:
    tender: int
    total: int

    def __post_init__(self):
        if type(self.tender) is not int or not self.total <= self.tender <= MAX_CENTS:
            raise PosError("Cash tendered must cover the total and be within the register limit.")

    @property
    def change(self) -> int:
        return self.tender - self.total


@dataclass
class Sale:
    id: str = field(default_factory=lambda: uuid4().hex)
    lines: dict[str, SalesLineItem] = field(default_factory=dict)
    ended: bool = False

    def add_item(self, product: Product, qty: int) -> SalesLineItem:
        if self.ended:
            raise PosError("This basket is closed. Reopen it to change items.")
        previous = self.lines.get(product.sku)
        new_qty = positive_quantity(qty) + (previous.qty if previous else 0)
        if new_qty > product.stock or new_qty > 10000:
            raise PosError(f"Quantity exceeds available stock or the line limit for {product.sku}.")
        if previous is None and len(self.lines) >= 24:
            raise PosError("A sale can contain up to 24 distinct products.")
        price = previous.price_cents if previous else product.price_cents
        name = previous.name if previous else product.name
        line = SalesLineItem(product.sku, name, price, new_qty)
        self.lines[product.sku] = line
        return line

    def end(self) -> None:
        if not self.lines:
            raise PosError("Add at least one item before ending the sale.")
        if self.total > MAX_CENTS:
            raise PosError("Sale total exceeds the register limit.")
        self.ended = True

    @property
    def subtotal(self) -> int:
        return sum(line.subtotal for line in self.lines.values())

    @property
    def tax(self) -> int:
        return sum(line.tax for line in self.lines.values())

    @property
    def total(self) -> int:
        return self.subtotal + self.tax

    def accept_cash(self, tender: int) -> CashPayment:
        if not self.ended:
            raise PosError("End the sale before recording cash.")
        return CashPayment(tender, self.total)


@dataclass(frozen=True)
class ReturnLineItem:
    source: SalesLineItem
    qty: int
    previously_returned: int

    def __post_init__(self):
        positive_quantity(self.qty)
        if not 0 <= self.previously_returned <= self.source.qty - self.qty:
            raise PosError(f"Quantity exceeds the number still returnable for {self.source.sku}.")

    @property
    def subtotal(self) -> int:
        return self.source.price_cents * self.qty

    @property
    def tax(self) -> int:
        prior = self.previously_returned
        source_tax = self.source.tax
        bought = self.source.qty
        return rounded_ratio(source_tax * (prior + self.qty), bought) - rounded_ratio(
            source_tax * prior, bought
        )


@dataclass
class Return:
    sale_id: int
    id: str = field(default_factory=lambda: uuid4().hex)
    items: dict[str, int] = field(default_factory=dict)

    def add_item(self, source: SalesLineItem, qty: int, returned: int) -> ReturnLineItem:
        line = ReturnLineItem(source, self.items.get(source.sku, 0) + positive_quantity(qty), returned)
        self.items[source.sku] = line.qty
        return line

    def quote(self, source: dict[str, SalesLineItem], returned: dict[str, int]) -> list[ReturnLineItem]:
        if not self.items:
            raise PosError("Add at least one item before refunding.")
        lines = [
            ReturnLineItem(source[sku], qty, returned.get(sku, 0)) for sku, qty in self.items.items()
        ]
        if not 0 < sum(line.subtotal + line.tax for line in lines) <= MAX_CENTS:
            raise PosError("The refund amount is outside the register limit.")
        return lines
