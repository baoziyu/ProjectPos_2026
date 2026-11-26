"""Flask routes translate form submissions into Register operations."""

import os
import sqlite3
from dataclasses import asdict
from hmac import compare_digest
from pathlib import Path
from secrets import token_hex

from flask import Flask, abort, flash, redirect, render_template, request, session, url_for

from src.application.register import Register
from src.domain.model import PosError, Product, Return, Sale, SalesLineItem, cents, money
from src.infrastructure.sqlite_store import SQLiteStore


def integer(value: str) -> int:
    try:
        return int(value)
    except ValueError as error:
        raise PosError("Enter a whole number.") from error


def create_app(database: Path | None = None) -> Flask:
    app = Flask(__name__)
    app.secret_key = os.environ.get("POS_SECRET") or token_hex(32)
    app.config.update(SESSION_COOKIE_SAMESITE="Strict")
    path = database or Path(os.environ.get("POS_DATABASE", Path(__file__).resolve().parents[2] / "database/pos.sqlite3"))
    store = SQLiteStore(path)
    store.initialize(seed=True)
    register = Register(store)
    app.jinja_env.filters["money"] = money

    @app.context_processor
    def common():
        if "csrf" not in session:
            session["csrf"] = token_hex(24)
        return {"csrf": session["csrf"]}

    @app.before_request
    def verify_form():
        if request.method == "POST":
            supplied = request.form.get("csrf", "")
            if not supplied.isascii() or not compare_digest(supplied, session.get("csrf", "!")):
                abort(400, "This form expired. Reload and try again.")

    def read_sale():
        data = session.get("sale")
        if data is not None:
            lines = {sku: SalesLineItem(**line) for sku, line in data["lines"].items()}
            return Sale(data["id"], lines, data["ended"])
        return None

    def read_return():
        data = session.get("return")
        return Return(**data) if data else None

    def require_draft(draft):
        if draft is None or draft.id != request.form.get("draft"):
            raise PosError("This transaction form is stale. Use the current transaction.")

    def save_draft(key, draft):
        data = asdict(draft)
        signed = app.session_interface.get_signing_serializer(app)
        if len(signed.dumps({**session, key: data})) > 3500:
            raise PosError("This draft reached the browser's storage limit.")
        session[key] = data

    def field(name):
        return request.form.get(name, "").strip()

    def show_retry(error):
        app.logger.warning("Database operation failed: %s", error)
        flash("The local database is unavailable. Retry before moving any cash.", "error")

    @app.route("/", methods=["GET", "POST"])
    def checkout():
        sale = read_sale()
        if request.method == "POST":
            action = field("action")
            try:
                if action == "new":
                    if sale is not None:
                        raise PosError("Cancel the open basket before starting a new sale.")
                    sale = register.make_new_sale()
                else:
                    require_draft(sale)
                    if action == "add":
                        register.enter_item(sale, field("sku"), integer(field("qty")))
                    elif action == "remove":
                        if sale.ended:
                            raise PosError("Reopen the basket to remove items.")
                        sale.lines.pop(field("sku"), None)
                    elif action == "end":
                        register.end_sale(sale)
                    elif action == "reopen":
                        sale.ended = False
                    elif action == "cancel":
                        session.pop("sale", None)
                        return redirect(url_for("checkout"))
                    elif action == "pay":
                        number = register.make_payment(sale, cents(field("tender")))
                        session.pop("sale", None)
                        return redirect(url_for("receipt", kind="sale", number=number))
                    else:
                        abort(400)
                save_draft("sale", sale)
            except PosError as error:
                flash(str(error), "error")
            except sqlite3.Error as error:
                show_retry(error)
            return redirect(url_for("checkout"))
        return render_template("checkout.html", sale=sale)

    @app.route("/returns", methods=["GET", "POST"])
    def returns():
        draft = read_return()
        if request.method == "POST":
            action = field("action")
            try:
                if action == "new":
                    if draft is not None:
                        raise PosError("Cancel the open return before selecting another sale.")
                    sale_id = integer(field("sale_id"))
                    if not 1 <= sale_id <= 2**63 - 1:
                        raise PosError("Enter a valid sale number.")
                    draft = register.make_new_return(sale_id)
                else:
                    require_draft(draft)
                    if action == "add":
                        register.enter_return_item(draft, field("sku"), integer(field("qty")))
                    elif action == "remove":
                        draft.items.pop(field("sku"), None)
                    elif action == "cancel":
                        session.pop("return", None)
                        return redirect(url_for("returns"))
                    elif action == "refund":
                        number = register.refund_cash(draft, integer(field("expected")))
                        session.pop("return", None)
                        return redirect(url_for("receipt", kind="return", number=number))
                    else:
                        abort(400)
                save_draft("return", draft)
            except PosError as error:
                flash(str(error), "error")
            except sqlite3.Error as error:
                show_retry(error)
            return redirect(url_for("returns"))

        source, used, refund_lines, quote_error = {}, {}, [], ""
        if draft:
            try:
                source, used = register.return_context(draft)
                if draft.items:
                    refund_lines = draft.quote(source, used)
            except PosError as error:
                quote_error = str(error)
        return render_template(
            "returns.html", draft=draft, source=source, used=used, refund_lines=refund_lines,
            refund_subtotal=sum(line.subtotal for line in refund_lines),
            refund_tax=sum(line.tax for line in refund_lines), quote_error=quote_error,
        )

    @app.route("/products", methods=["GET", "POST"])
    def products():
        if request.method == "POST":
            try:
                sku = field("sku").upper()
                product = Product(sku, field("name"), cents(field("price")), integer(field("stock")))
                register.save_product(product, create=field("action") == "create")
                flash(f"Saved {sku}.", "success")
            except PosError as error:
                flash(str(error), "error")
            except sqlite3.Error as error:
                show_retry(error)
            return redirect(url_for("products"))
        query = request.args.get("q", "").strip()
        selected_sku = request.args.get("edit")
        entries = register.products(query)
        selected = next((p for p in entries if p.sku == selected_sku), None)
        return render_template("products.html", products=entries, query=query, selected=selected)

    @app.get("/history")
    def history():
        return render_template("history.html", sales=register.recent("sale"), returns=register.recent("return"))

    @app.get("/receipt/<kind>/<int:number>")
    def receipt(kind, number):
        if kind not in ("sale", "return") or not 1 <= number <= 2**63 - 1:
            abort(404)
        try:
            header, lines = register.receipt(kind, number)
        except PosError:
            abort(404, "Receipt was not found.")
        return render_template("receipt.html", kind=kind, header=header, lines=lines)

    @app.errorhandler(sqlite3.Error)
    def database_unavailable(error):
        app.logger.warning("Database read failed: %s", error)
        return render_template("unavailable.html"), 503

    return app
