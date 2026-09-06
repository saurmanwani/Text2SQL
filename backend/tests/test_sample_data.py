import sqlite3
from pathlib import Path

from sample_data.seed import seed_database


def test_seed_creates_complete_retail_dataset(tmp_path: Path) -> None:
    path = seed_database(tmp_path / "sample.db")
    database = sqlite3.connect(path)
    try:
        tables = {
            row[0]
            for row in database.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }
        sales_count = database.execute("SELECT COUNT(*) FROM sales").fetchone()[0]
    finally:
        database.close()

    assert tables == {
        "stores",
        "products",
        "categories",
        "sales",
        "inventory",
        "promotions",
    }
    assert sales_count == 20_000
