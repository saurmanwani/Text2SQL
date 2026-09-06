import sqlite3
from pathlib import Path

from app.connectors.sqlalchemy_connector import SQLAlchemyConnector
from app.core.crypto import decrypt_value, encrypt_value


def create_database(path: str) -> None:
    connection = sqlite3.connect(path)
    connection.executescript(
        """
        PRAGMA foreign_keys = ON;
        CREATE TABLE categories (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL
        );
        CREATE TABLE products (
            id INTEGER PRIMARY KEY,
            category_id INTEGER NOT NULL REFERENCES categories(id),
            name TEXT NOT NULL,
            price REAL
        );
        INSERT INTO categories VALUES (1, 'Tools');
        INSERT INTO products VALUES
            (1, 1, 'Hammer', 12.5),
            (2, 1, 'Saw', 18.0),
            (3, 1, 'Drill', 45.0);
        """
    )
    connection.commit()
    connection.close()


def test_sqlite_schema_execution_and_row_limit(tmp_path: Path) -> None:
    database_path = str(tmp_path / "connector.db")
    create_database(database_path)
    connector = SQLAlchemyConnector(f"sqlite:///{database_path}")

    assert connector.test_connection() is True
    assert connector.dialect == "sqlite"
    assert connector.is_read_only() is None

    schema = connector.get_schema()
    assert [table.name for table in schema.tables] == ["categories", "products"]
    products = next(table for table in schema.tables if table.name == "products")
    category_id = next(column for column in products.columns if column.name == "category_id")
    assert category_id.foreign_key_targets == ["categories.id"]
    assert next(column for column in products.columns if column.name == "id").primary_key

    result = connector.execute("SELECT id, name FROM products ORDER BY id", row_limit=2)
    assert result.columns == ["id", "name"]
    assert result.rows == [[1, "Hammer"], [2, "Saw"]]
    assert result.row_count == 2


def test_connection_value_encryption() -> None:
    encrypted = encrypt_value("sqlite:///private.db", "test-secret")

    assert encrypted != "sqlite:///private.db"
    assert decrypt_value(encrypted, "test-secret") == "sqlite:///private.db"
