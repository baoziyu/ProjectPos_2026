import tempfile
import unittest
from pathlib import Path

from src.presentation.web import create_app


class WebTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        app = create_app(Path(directory.name) / "test.sqlite3")
        app.testing = True
        self.client = app.test_client()

    def submit(self, url, action, key=None, **fields):
        with self.client.session_transaction() as state:
            fields["csrf"] = state["csrf"]
            if key:
                fields["draft"] = state[key]["id"]
        return self.client.post(url, data={"action": action, **fields}, follow_redirects=True)

    def test_checkout_to_refund_and_history(self):
        self.assertIn(b"Start a sale", self.client.get("/").data)
        self.submit("/", "new")
        self.submit("/", "add", "sale", sku="1001", qty="2")
        self.submit("/", "add", "sale", sku="1002", qty="1")
        self.submit("/", "end", "sale")
        rejected = self.submit("/", "pay", "sale", tender="10.00")
        self.assertIn(b"must cover the total", rejected.data)
        paid = self.submit("/", "pay", "sale", tender="20.00")
        self.assertIn(b"Sale receipt", paid.data)
        self.assertIn(b"$8.50", paid.data)
        self.submit("/returns", "new", sale_id="1")
        self.submit("/returns", "add", "return", sku="1001", qty="1")
        voucher = self.submit("/returns", "refund", "return", expected="346")
        self.assertIn(b"Original sale #1", voucher.data)
        self.assertIn(b"$3.46", voucher.data)
        history = self.client.get("/history")
        self.assertIn(b"Return #1", history.data)
        self.assertIn(b"Sale #1", history.data)

    def test_product_create_edit_and_search(self):
        self.client.get("/products")
        self.submit("/products", "create", sku="M-1", name="Mango", price="1.59", stock="8")
        self.submit("/products", "update", sku="M-1", name="Mango", price="2.19", stock="7")
        result = self.client.get("/products?q=Mango")
        self.assertIn(b"$2.19", result.data)
        self.assertNotIn(b"Whole Milk", result.data)

    def test_invalid_receipt_and_missing_csrf(self):
        self.assertEqual(self.client.get("/receipt/sale/88").status_code, 404)
        self.assertEqual(self.client.post("/", data={"action": "new"}).status_code, 400)
