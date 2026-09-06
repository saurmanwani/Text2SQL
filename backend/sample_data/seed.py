import random
import sqlite3
from datetime import date, timedelta
from pathlib import Path

SAMPLE_DATABASE = Path(__file__).with_name("sample.db")


def seed_database(path: Path = SAMPLE_DATABASE) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        return path

    randomizer = random.Random(42)
    connection = sqlite3.connect(path)
    connection.executescript(
        """
        PRAGMA foreign_keys = ON;
        CREATE TABLE stores (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            region TEXT NOT NULL
        );
        CREATE TABLE categories (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL
        );
        CREATE TABLE products (
            id INTEGER PRIMARY KEY,
            category_id INTEGER NOT NULL REFERENCES categories(id),
            name TEXT NOT NULL,
            price REAL NOT NULL
        );
        CREATE TABLE sales (
            id INTEGER PRIMARY KEY,
            store_id INTEGER NOT NULL REFERENCES stores(id),
            product_id INTEGER NOT NULL REFERENCES products(id),
            sold_at DATE NOT NULL,
            quantity INTEGER NOT NULL,
            revenue REAL NOT NULL
        );
        CREATE TABLE inventory (
            store_id INTEGER NOT NULL REFERENCES stores(id),
            product_id INTEGER NOT NULL REFERENCES products(id),
            quantity INTEGER NOT NULL,
            PRIMARY KEY (store_id, product_id)
        );
        CREATE TABLE promotions (
            id INTEGER PRIMARY KEY,
            product_id INTEGER NOT NULL REFERENCES products(id),
            name TEXT NOT NULL,
            starts_at DATE NOT NULL,
            ends_at DATE NOT NULL,
            discount_percent INTEGER NOT NULL
        );
        """
    )

    stores = [
        (1, "Downtown", "North"),
        (2, "Riverside", "South"),
        (3, "Market Square", "East"),
        (4, "Hilltop", "West"),
        (5, "Central", "North"),
    ]
    categories = [(1, "Electronics"), (2, "Home"), (3, "Outdoors"), (4, "Office")]
    products = [
        (product_id, ((product_id - 1) % 4) + 1, f"Product {product_id}", 5.0 + product_id * 2.5)
        for product_id in range(1, 41)
    ]
    connection.executemany("INSERT INTO stores VALUES (?, ?, ?)", stores)
    connection.executemany("INSERT INTO categories VALUES (?, ?)", categories)
    connection.executemany("INSERT INTO products VALUES (?, ?, ?, ?)", products)

    start = date(2024, 1, 1)
    sales = []
    for sale_id in range(1, 20_001):
        store_id = randomizer.randint(1, len(stores))
        product_id = randomizer.randint(1, len(products))
        quantity = randomizer.randint(1, 8)
        sold_at = start + timedelta(days=randomizer.randint(0, 730))
        revenue = round(products[product_id - 1][3] * quantity, 2)
        sales.append((sale_id, store_id, product_id, sold_at.isoformat(), quantity, revenue))
    connection.executemany("INSERT INTO sales VALUES (?, ?, ?, ?, ?, ?)", sales)

    inventory = [
        (store_id, product_id, randomizer.randint(0, 150))
        for store_id in range(1, len(stores) + 1)
        for product_id in range(1, len(products) + 1)
    ]
    connection.executemany("INSERT INTO inventory VALUES (?, ?, ?)", inventory)
    connection.executemany(
        "INSERT INTO promotions VALUES (?, ?, ?, ?, ?, ?)",
        [
            (1, 3, "Spring Sale", "2025-03-01", "2025-03-31", 15),
            (2, 12, "Summer Special", "2025-06-01", "2025-06-30", 20),
            (3, 25, "Holiday Deal", "2025-12-01", "2025-12-31", 25),
        ],
    )
    connection.commit()
    connection.close()
    return path


if __name__ == "__main__":
    print(seed_database())
