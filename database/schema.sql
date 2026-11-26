PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS products (
    sku TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    price_cents INTEGER NOT NULL CHECK (price_cents > 0),
    stock INTEGER NOT NULL CHECK (stock >= 0)
);

CREATE TABLE IF NOT EXISTS sales (
    id INTEGER PRIMARY KEY,
    token TEXT NOT NULL UNIQUE,
    created TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    subtotal INTEGER NOT NULL CHECK (subtotal > 0),
    tax INTEGER NOT NULL CHECK (tax >= 0),
    total INTEGER NOT NULL CHECK (total = subtotal + tax),
    tender INTEGER NOT NULL CHECK (tender >= total),
    change_due INTEGER NOT NULL CHECK (change_due = tender - total)
);

CREATE TABLE IF NOT EXISTS sale_lines (
    sale_id INTEGER NOT NULL REFERENCES sales(id),
    sku TEXT NOT NULL REFERENCES products(sku),
    name TEXT NOT NULL,
    price_cents INTEGER NOT NULL CHECK (price_cents > 0),
    qty INTEGER NOT NULL CHECK (qty > 0),
    subtotal INTEGER NOT NULL CHECK (subtotal = price_cents * qty),
    tax INTEGER NOT NULL CHECK (tax >= 0),
    PRIMARY KEY (sale_id, sku)
);

CREATE TABLE IF NOT EXISTS returns (
    id INTEGER PRIMARY KEY,
    sale_id INTEGER NOT NULL REFERENCES sales(id),
    token TEXT NOT NULL UNIQUE,
    created TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    subtotal INTEGER NOT NULL CHECK (subtotal > 0),
    tax INTEGER NOT NULL CHECK (tax >= 0),
    total INTEGER NOT NULL CHECK (total = subtotal + tax),
    UNIQUE (id, sale_id)
);

CREATE TABLE IF NOT EXISTS return_lines (
    return_id INTEGER NOT NULL,
    sale_id INTEGER NOT NULL,
    sku TEXT NOT NULL,
    qty INTEGER NOT NULL CHECK (qty > 0),
    subtotal INTEGER NOT NULL CHECK (subtotal > 0),
    tax INTEGER NOT NULL CHECK (tax >= 0),
    PRIMARY KEY (return_id, sku),
    FOREIGN KEY (return_id, sale_id) REFERENCES returns(id, sale_id),
    FOREIGN KEY (sale_id, sku) REFERENCES sale_lines(sale_id, sku)
);

CREATE INDEX IF NOT EXISTS return_line_source ON return_lines(sale_id, sku);
