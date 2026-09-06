from pydantic import BaseModel, Field
from sqlglot import exp, parse
from sqlglot.errors import ParseError


class ValidationResult(BaseModel):
    ok: bool
    sql: str | None = None
    tables: list[str] = Field(default_factory=list)
    reason: str | None = None
    internal_reason: str | None = None


READ_ONLY_ROOTS = (exp.Select, exp.Union, exp.Intersect, exp.Except)
SIDE_EFFECT_NODES = tuple(
    node
    for name in (
        "Alter",
        "Command",
        "Commit",
        "Copy",
        "Create",
        "Delete",
        "Drop",
        "Grant",
        "Insert",
        "Into",
        "Lock",
        "Merge",
        "Rollback",
        "Set",
        "Transaction",
        "TruncateTable",
        "Update",
        "Use",
    )
    if (node := getattr(exp, name, None)) is not None
)


def _invalid(reason: str, internal_reason: str | None = None) -> ValidationResult:
    return ValidationResult(ok=False, reason=reason, internal_reason=internal_reason or reason)


def _referenced_tables(expression: exp.Expression) -> set[str]:
    cte_names = {cte.alias_or_name.lower() for cte in expression.find_all(exp.CTE)}
    return {
        table.name
        for table in expression.find_all(exp.Table)
        if table.name and table.name.lower() not in cte_names
    }


def _clamp_limit(expression: exp.Expression, max_rows: int) -> exp.Expression:
    limit = expression.args.get("limit")
    if limit is None:
        return expression.limit(max_rows)

    value = limit.expression
    if isinstance(value, exp.Literal) and value.is_int and int(value.this) <= max_rows:
        return expression
    return expression.limit(max_rows, copy=False)


def validate(
    sql: str,
    dialect: str,
    allowed_tables: set[str] | None,
    max_rows: int,
) -> ValidationResult:
    if max_rows < 1:
        raise ValueError("max_rows must be positive")
    try:
        statements = parse(sql, read=dialect)
    except (ParseError, ValueError) as exc:
        return _invalid("parse_error", str(exc))

    if len(statements) != 1:
        return _invalid("multiple_statements")
    expression = statements[0]
    if expression is None:
        return _invalid("parse_error")
    if not isinstance(expression, READ_ONLY_ROOTS):
        return _invalid("not_select", type(expression).__name__)
    if any(expression.find(node) is not None for node in SIDE_EFFECT_NODES):
        return _invalid("side_effect", "side-effecting SQL construct")

    tables = _referenced_tables(expression)
    if allowed_tables is not None:
        allowed = {table.lower() for table in allowed_tables}
        blocked = sorted(table for table in tables if table.lower() not in allowed)
        if blocked:
            return ValidationResult(
                ok=False,
                tables=sorted(tables),
                reason="table_not_allowed",
                internal_reason=f"Blocked tables: {', '.join(blocked)}",
            )

    normalized = _clamp_limit(expression, max_rows).sql(dialect=dialect)
    return ValidationResult(ok=True, sql=normalized, tables=sorted(tables))
