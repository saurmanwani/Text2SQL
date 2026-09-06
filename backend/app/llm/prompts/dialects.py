DIALECT_RULES = {
    "postgres": (
        "Use PostgreSQL syntax. Use DATE_TRUNC for date grouping, double quotes for identifiers, "
        "and LIMIT for row limits."
    ),
    "mysql": (
        "Use MySQL syntax. Use DATE_FORMAT for date grouping, backticks for identifiers, "
        "and LIMIT for row limits."
    ),
    "sqlite": (
        "Use SQLite syntax. Use strftime for date grouping, double quotes for identifiers, "
        "and LIMIT for row limits."
    ),
}
