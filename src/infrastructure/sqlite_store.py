"""SQLite adapter with a bounded write transaction for each business commit."""

import sqlite3
from contextlib import contextmanager
from pathlib import Path

from src.domain.model import CashPayment, PosError, Product, Return, ReturnLineItem, Sale, SalesLineItem


class SQLiteStore:
    def __init__(self, path: Path):
        self.path = path

    @contextmanager
    def session(self, *, write=False):
        db = sqlite3.connect(self.path, timeout=5)
        db.row_factory = sqlite3.Row
        try:
            db.execute("PRAGMA foreign_keys = ON")
            db.execute("BEGIN IMMEDIATE" if write else "BEGIN")
            yield SQLiteSession(db)
            db.commit()
        except BaseException:
            db.rollback()
            raise
        finally:
            db.close()

    def initialize(self, seed: bool = False) -> None:
        files = Path(__file__).resolve().parents[2] / "database"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.session() as repo:
            repo.db.executescript((files / "schema.sql").read_text())
            if seed:
                repo.db.executescript((files / "seed.sql").read_text())


class SQLiteSession:
    def __init__(self, db: sqlite3.Connection):
        self.db = db

    def list_products(self, query: str = "") -> list[Product]:
        pattern = f"%{query}%"
        rows = self.db.execute(
            "SELECT * FROM products WHERE sku LIKE ? OR name LIKE ? ORDER BY sku", (pattern, pattern)
        )
        return [Product(**row) for row in rows]

    def get_product(self, sku: str) -> Product:
        row = self.db.execute("SELECT * FROM products WHERE sku = ?", (sku,)).fetchone()
        if row is None:
            raise PosError(f"Product {sku or '(empty code)'} was not found.")
        return Product(**row)

    def save_product(self, product: Product, *, create: bool) -> None:
        if create:
            try:
                self.db.execute(
                    "INSERT INTO products VALUES (?, ?, ?, ?)",
                    (product.sku, product.name, product.price_cents, product.stock),
                )
            except sqlite3.IntegrityError as error:
                raise PosError("That product code already exists.") from error
        else:
            cursor = self.db.execute(
                "UPDATE products SET name = ?, price_cents = ?, stock = ? WHERE sku = ?",
                (product.name, product.price_cents, product.stock, product.sku),
            )
            if not cursor.rowcount:
                raise PosError("Choose an existing product to update.")

    def find_sale_token(self, token: str) -> int | None:
        row = self.db.execute("SELECT id FROM sales WHERE token = ?", (token,)).fetchone()
        return row["id"] if row else None

    def find_return_token(self, token: str) -> int | None:
        row = self.db.execute("SELECT id FROM returns WHERE token = ?", (token,)).fetchone()
        return row["id"] if row else None

    def persist_sale(self, sale: Sale, payment: CashPayment) -> int:
        cursor = self.db.execute(
            "INSERT INTO sales (token, subtotal, tax, total, tender, change_due) VALUES (?, ?, ?, ?, ?, ?)",
            (sale.id, sale.subtotal, sale.tax, sale.total, payment.tender, payment.change),
        )
        sale_id = cursor.lastrowid
        for line in sale.lines.values():
            stock = self.db.execute(
                "UPDATE products SET stock = stock - ? WHERE sku = ? AND stock >= ?",
                (line.qty, line.sku, line.qty),
            )
            if not stock.rowcount:
                raise PosError(f"Stock changed for {line.sku}. Reopen the basket and adjust it.")
            self.db.execute(
                "INSERT INTO sale_lines VALUES (?, ?, ?, ?, ?, ?, ?)",
                (sale_id, line.sku, line.name, line.price_cents, line.qty, line.subtotal, line.tax),
            )
        return sale_id

    def sale_items(self, sale_id: int) -> dict[str, SalesLineItem]:
        rows = self.db.execute(
            "SELECT sku, name, price_cents, qty, tax AS recorded_tax FROM sale_lines WHERE sale_id = ? ORDER BY sku", (sale_id,)
        )
        lines = {row["sku"]: SalesLineItem(**row) for row in rows}
        if not lines:
            raise PosError(f"Sale #{sale_id} was not found.")
        return lines

    def returned_quantities(self, sale_id: int) -> dict[str, int]:
        rows = self.db.execute(
            "SELECT sku, SUM(qty) AS qty FROM return_lines WHERE sale_id = ? GROUP BY sku", (sale_id,)
        )
        return {row["sku"]: row["qty"] for row in rows}

    def persist_return(self, draft: Return, lines: list[ReturnLineItem]) -> int:
        subtotal = sum(line.subtotal for line in lines)
        tax = sum(line.tax for line in lines)
        cursor = self.db.execute(
            "INSERT INTO returns (sale_id, token, subtotal, tax, total) VALUES (?, ?, ?, ?, ?)",
            (draft.sale_id, draft.id, subtotal, tax, subtotal + tax),
        )
        return_id = cursor.lastrowid
        for line in lines:
            sku = line.source.sku
            self.db.execute(
                "INSERT INTO return_lines VALUES (?, ?, ?, ?, ?, ?)",
                (return_id, draft.sale_id, sku, line.qty, line.subtotal, line.tax),
            )
            stock = self.db.execute(
                "UPDATE products SET stock = stock + ? WHERE sku = ? AND stock + ? <= 10000000",
                (line.qty, sku, line.qty),
            )
            if not stock.rowcount:
                raise PosError(f"Stock for {sku} would exceed the register limit.")
        return return_id

    def receipt(self, kind: str, number: int) -> tuple[dict, list[dict]]:
        if kind == "sale":
            header = self.db.execute("SELECT * FROM sales WHERE id = ?", (number,)).fetchone()
            lines = self.db.execute("SELECT * FROM sale_lines WHERE sale_id = ? ORDER BY sku", (number,))
        else:
            header = self.db.execute("SELECT * FROM returns WHERE id = ?", (number,)).fetchone()
            lines = self.db.execute(
                """SELECT r.*, s.name, s.price_cents FROM return_lines r
                   JOIN sale_lines s USING (sale_id, sku) WHERE return_id = ? ORDER BY r.sku""",
                (number,),
            )
        if header is None:
            raise PosError("Receipt was not found.")
        return dict(header), [dict(row) for row in lines]

    def recent(self, kind: str) -> list[dict]:
        sql = ("SELECT id, created, total FROM sales ORDER BY id DESC LIMIT 25" if kind == "sale" else
               "SELECT id, sale_id, created, total FROM returns ORDER BY id DESC LIMIT 25")
        return [dict(row) for row in self.db.execute(sql)]
