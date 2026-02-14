PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS stores (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    website TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS accounts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    provider TEXT NOT NULL,
    account_identifier TEXT NOT NULL,
    display_name TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(provider, account_identifier)
);

CREATE TABLE IF NOT EXISTS sellers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    store_id INTEGER,
    name TEXT NOT NULL,
    inn TEXT,
    legal_entity TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(store_id, name, inn),
    FOREIGN KEY (store_id) REFERENCES stores(id)
);

CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    canonical_key TEXT UNIQUE,
    title_full TEXT,
    title_short TEXT,
    brand TEXT,
    model TEXT,
    sku TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    store_id INTEGER NOT NULL,
    account_id INTEGER,
    seller_id INTEGER,
    external_order_id TEXT,
    dedupe_key TEXT NOT NULL UNIQUE,
    order_datetime TEXT,
    paid_datetime TEXT,
    delivered_datetime TEXT,
    currency TEXT,
    subtotal_amount REAL,
    shipping_amount REAL,
    discount_amount REAL,
    total_amount REAL,
    status TEXT,
    source_url TEXT,
    raw_ref TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(store_id, external_order_id),
    FOREIGN KEY (store_id) REFERENCES stores(id),
    FOREIGN KEY (account_id) REFERENCES accounts(id),
    FOREIGN KEY (seller_id) REFERENCES sellers(id)
);

CREATE TABLE IF NOT EXISTS order_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id INTEGER NOT NULL,
    external_item_id TEXT,
    dedupe_key TEXT NOT NULL,
    product_id INTEGER,
    title_full TEXT,
    title_short TEXT,
    store_category_path TEXT,
    unified_category_path TEXT,
    brand TEXT,
    model TEXT,
    sku TEXT,
    quantity REAL NOT NULL DEFAULT 1,
    unit_price REAL,
    discount_amount REAL,
    shipping_amount REAL,
    total_amount REAL,
    currency TEXT,
    product_url TEXT,
    order_url TEXT,
    receipt_url TEXT,
    comment_user TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(order_id, dedupe_key),
    FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE,
    FOREIGN KEY (product_id) REFERENCES products(id)
);

CREATE TABLE IF NOT EXISTS product_attributes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER,
    item_id INTEGER,
    attr_key TEXT NOT NULL,
    value_type TEXT NOT NULL,
    value_text TEXT,
    value_number REAL,
    value_bool INTEGER,
    value_json_raw TEXT,
    source TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(item_id, attr_key, value_text, value_number, value_bool),
    FOREIGN KEY (product_id) REFERENCES products(id),
    FOREIGN KEY (item_id) REFERENCES order_items(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS media (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    related_item_id INTEGER NOT NULL,
    source_url TEXT,
    local_path_abs TEXT NOT NULL,
    mime TEXT,
    sha256 TEXT NOT NULL,
    size_bytes INTEGER,
    source TEXT,
    downloaded_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    meta_json TEXT,
    UNIQUE(related_item_id, sha256, source_url),
    FOREIGN KEY (related_item_id) REFERENCES order_items(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_media_sha256 ON media(sha256);

CREATE TABLE IF NOT EXISTS reviews (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER,
    item_id INTEGER,
    review_type TEXT NOT NULL CHECK (review_type IN ('public', 'my')),
    source TEXT,
    author TEXT,
    rating REAL,
    review_date TEXT,
    text TEXT,
    url TEXT,
    helpful_count INTEGER,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(product_id, review_type, source, author, review_date, text),
    FOREIGN KEY (product_id) REFERENCES products(id),
    FOREIGN KEY (item_id) REFERENCES order_items(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS raw_messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source TEXT NOT NULL,
    account_id INTEGER,
    external_message_id TEXT NOT NULL,
    thread_id TEXT,
    message_datetime TEXT,
    subject TEXT,
    sender TEXT,
    recipients TEXT,
    raw_text TEXT,
    raw_html TEXT,
    raw_json TEXT,
    raw_eml_path TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(source, external_message_id),
    FOREIGN KEY (account_id) REFERENCES accounts(id)
);

CREATE TABLE IF NOT EXISTS raw_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source TEXT NOT NULL,
    event_type TEXT NOT NULL,
    external_id TEXT,
    payload_json TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS sync_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    correlation_id TEXT NOT NULL UNIQUE,
    source TEXT NOT NULL,
    started_at TEXT NOT NULL,
    finished_at TEXT,
    status TEXT NOT NULL,
    stats_json TEXT,
    error_text TEXT
);

CREATE TABLE IF NOT EXISTS audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    correlation_id TEXT,
    entity_type TEXT NOT NULL,
    entity_id TEXT,
    action TEXT NOT NULL,
    before_json TEXT,
    after_json TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
