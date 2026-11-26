import sqlite3
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier

from src.application.register import Register
from src.domain.model import PosError, Product, cents
from src.infrastructure.sqlite_store import SQLiteStore


class RegisterTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.path = Path(directory.name) / "pos.sqlite3"
        self.store = SQLiteStore(self.path)
        self.store.initialize(seed=True)
        self.pos = Register(self.store)

    def basket(self, qty=2):
        sale = self.pos.make_new_sale()
        self.pos.enter_item(sale, "1001", qty)
        return sale

    def pay(self, sale, tender=1000):
        self.pos.end_sale(sale)
        return self.pos.make_payment(sale, tender)

    def stock(self, sku="1001"):
        return self.pos.products(sku)[0].stock

    def draft(self, sale_id, qty=1):
        draft = self.pos.make_new_return(sale_id)
        self.pos.enter_return_item(draft, "1001", qty)
        return draft

    def test_normal_sale_and_change(self):
        number = self.pay(self.basket())
        record, lines = self.pos.receipt("sale", number)
        self.assertEqual((record["subtotal"], record["tax"], record["total"]), (640, 51, 691))
        self.assertEqual((record["tender"], record["change_due"]), (1000, 309))
        self.assertEqual((lines[0]["qty"], self.stock()), (2, 38))

    def test_multi_product_sale_and_repeated_scan(self):
        sale = self.basket(1)
        self.pos.enter_item(sale, "1001", 1)
        self.pos.enter_item(sale, "1002", 1)
        number = self.pay(sale, 2000)
        record, lines = self.pos.receipt("sale", number)
        self.assertEqual((record["total"], record["change_due"]), (1150, 850))
        self.assertEqual([line["qty"] for line in lines], [2, 1])
        self.assertEqual((self.stock(), self.stock("1002")), (38, 27))

    def test_unknown_product(self):
        sale = self.pos.make_new_sale()
        with self.assertRaisesRegex(PosError, "was not found"):
            self.pos.enter_item(sale, "9999", 1)
        self.assertFalse(sale.lines)

    def test_insufficient_cash_does_not_commit(self):
        sale = self.basket()
        self.pos.end_sale(sale)
        with self.assertRaisesRegex(PosError, "must cover"):
            self.pos.make_payment(sale, 690)
        self.assertEqual(self.pos.recent("sale"), [])
        self.assertEqual(self.stock(), 40)
        self.assertGreater(self.pos.make_payment(sale, 691), 0)

    def test_normal_refund_restores_stock(self):
        original = self.pay(self.basket())
        number = self.pos.refund_cash(self.draft(original), 346)
        record, lines = self.pos.receipt("return", number)
        self.assertEqual((record["sale_id"], record["total"], lines[0]["qty"]), (original, 346, 1))
        self.assertEqual(self.stock(), 39)

    def test_refund_beyond_remaining_quantity(self):
        original = self.pay(self.basket())
        self.pos.refund_cash(self.draft(original), 346)
        with self.assertRaisesRegex(PosError, "still returnable"):
            self.draft(original, 2)
        self.assertEqual(self.stock(), 39)

    def test_unknown_original_sale_and_return_product(self):
        with self.assertRaisesRegex(PosError, "was not found"):
            self.pos.make_new_return(9876)
        draft = self.pos.make_new_return(self.pay(self.basket()))
        for sku in ("9999", "1002"):
            with self.subTest(sku=sku), self.assertRaisesRegex(PosError, "not on this sale"):
                self.pos.enter_return_item(draft, sku, 1)
        self.assertFalse(draft.items)

    def test_historical_price_and_exact_partial_returns(self):
        original = self.pay(self.basket())
        self.pos.save_product(Product("1001", "Renamed milk", 500, 38), create=False)
        first = self.pos.refund_cash(self.draft(original), 346)
        second = self.pos.refund_cash(self.draft(original), 345)
        sale, _ = self.pos.receipt("sale", original)
        receipts = [self.pos.receipt("return", number) for number in (first, second)]
        self.assertEqual(sum(header["total"] for header, _ in receipts), sale["total"])
        self.assertEqual([lines[0]["name"] for _, lines in receipts], ["Whole Milk 1 L"] * 2)
        self.assertEqual(self.stock(), 40)

    def test_stale_refund_quote_does_not_commit(self):
        original = self.pay(self.basket())
        stale = self.draft(original)
        self.pos.refund_cash(self.draft(original), 346)
        with self.assertRaisesRegex(PosError, "quote changed"):
            self.pos.refund_cash(stale, 346)
        self.assertEqual(len(self.pos.recent("return")), 1)
        self.assertEqual(self.stock(), 39)

    def test_sqlite_persistence_and_integrity(self):
        original = self.pay(self.basket())
        number = self.pos.refund_cash(self.draft(original), 346)
        reopened = SQLiteStore(self.path)
        reopened.initialize(seed=True)
        restarted = Register(reopened)
        self.assertEqual(restarted.receipt("return", number)[0]["sale_id"], original)
        self.assertEqual(restarted.products("1001")[0].stock, 39)
        with sqlite3.connect(self.path) as connection:
            self.assertEqual(connection.execute("PRAGMA integrity_check").fetchall(), [("ok",)])
            self.assertEqual(connection.execute("PRAGMA foreign_key_check").fetchall(), [])

    def test_stale_sale_rolls_back_every_write(self):
        sale = self.basket()
        self.pos.enter_item(sale, "1002", 1)
        self.pos.save_product(Product("1002", "Country Sourdough", 425, 0), create=False)
        with self.assertRaisesRegex(PosError, "Stock changed"):
            self.pay(sale, 2000)
        self.assertFalse(self.pos.recent("sale"))
        self.assertEqual(self.stock(), 40)

    def test_duplicate_sale_and_refund_requests_are_idempotent(self):
        sale = self.basket()
        original = self.pay(sale)
        self.assertEqual(self.pos.make_payment(sale, 1000), original)
        draft = self.draft(original)
        number = self.pos.refund_cash(draft, 346)
        self.assertEqual(self.pos.refund_cash(draft, 346), number)
        self.assertEqual(len(self.pos.recent("sale")), 1)
        self.assertEqual(len(self.pos.recent("return")), 1)
        self.assertEqual(self.stock(), 39)

    def test_concurrent_returns_cannot_both_claim_last_unit(self):
        original = self.pay(self.basket(1))
        drafts = [self.draft(original), self.draft(original)]
        ready = Barrier(2, timeout=3)

        def refund(draft):
            ready.wait()
            try:
                self.pos.refund_cash(draft, 346)
                return True
            except PosError:
                return False

        with ThreadPoolExecutor(2) as pool:
            self.assertEqual(sorted(pool.map(refund, drafts)), [False, True])
        self.assertEqual(self.stock(), 40)
        self.assertEqual(len(self.pos.recent("return")), 1)

    def test_product_validation_and_search(self):
        self.pos.save_product(Product("M-1", "Mango", 159, 8), create=True)
        self.assertEqual(self.pos.products("mango")[0].sku, "M-1")
        with self.assertRaises(PosError):
            self.pos.save_product(Product("M-1", "Mango", 159, 8), create=True)
        for invalid in ("NaN", "Infinity", "1.001", "-2", "1.000000000000000000000000000001"):
            with self.subTest(invalid=invalid), self.assertRaises(PosError):
                cents(invalid)
