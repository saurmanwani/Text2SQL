import pytest

from app.safety.validator import validate


@pytest.mark.parametrize(
    ("sql", "dialect", "expected_ok"),
    [
        ("SELECT 1", "sqlite", True),
        ("SELECT * FROM sales", "sqlite", True),
        ("SELECT s.id FROM sales AS s", "sqlite", True),
        ("SELECT * FROM (SELECT * FROM sales) s", "sqlite", True),
        ("WITH x AS (SELECT * FROM sales) SELECT * FROM x", "sqlite", True),
        ("SELECT * FROM sales UNION SELECT * FROM archived_sales", "sqlite", True),
        ("SELECT `name` FROM `products`", "mysql", True),
        ("SELECT created_at::date FROM events", "postgres", True),
        ("SELECT date(created_at) FROM events", "sqlite", True),
        ("INSERT INTO sales VALUES (1)", "sqlite", False),
        ("UPDATE sales SET total = 0", "sqlite", False),
        ("DELETE FROM sales", "sqlite", False),
        ("DROP TABLE sales", "sqlite", False),
        ("CREATE TABLE danger (id INT)", "sqlite", False),
        ("ALTER TABLE sales ADD COLUMN danger INT", "sqlite", False),
        ("TRUNCATE TABLE sales", "postgres", False),
        ("CALL dangerous_procedure()", "mysql", False),
        ("COPY sales TO '/tmp/sales.csv'", "postgres", False),
        ("PRAGMA table_info(sales)", "sqlite", False),
        ("ATTACH DATABASE 'other.db' AS other", "sqlite", False),
        ("VACUUM", "sqlite", False),
        ("SELECT * INTO copied_sales FROM sales", "postgres", False),
        ("SELECT 1; DELETE FROM sales", "sqlite", False),
        ("SELECT FROM", "sqlite", False),
        ("", "sqlite", False),
        ("BEGIN", "sqlite", False),
        ("COMMIT", "sqlite", False),
        ("ROLLBACK", "sqlite", False),
        ("GRANT SELECT ON sales TO analyst", "postgres", False),
        ("SET search_path TO public", "postgres", False),
    ],
)
def test_read_only_cases(sql: str, dialect: str, expected_ok: bool) -> None:
    assert validate(sql, dialect, None, 100).ok is expected_ok


def test_extracts_real_tables_not_cte_aliases() -> None:
    result = validate(
        "WITH recent AS (SELECT * FROM sales) "
        "SELECT * FROM recent JOIN products p ON p.id = recent.product_id",
        "sqlite",
        {"sales", "products"},
        100,
    )

    assert result.ok
    assert result.tables == ["products", "sales"]


def test_blocks_hidden_table_without_user_facing_name() -> None:
    result = validate("SELECT * FROM payroll", "postgres", {"sales"}, 100)

    assert not result.ok
    assert result.reason == "table_not_allowed"
    assert result.reason and "payroll" not in result.reason
    assert result.internal_reason and "payroll" in result.internal_reason


@pytest.mark.parametrize(
    ("sql", "expected_limit"),
    [
        ("SELECT * FROM sales", "LIMIT 100"),
        ("SELECT * FROM sales LIMIT 500", "LIMIT 100"),
        ("SELECT * FROM sales LIMIT 20", "LIMIT 20"),
    ],
)
def test_injects_or_clamps_limit(sql: str, expected_limit: str) -> None:
    result = validate(sql, "sqlite", None, 100)

    assert result.ok
    assert result.sql and expected_limit in result.sql
