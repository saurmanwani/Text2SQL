from app.pipeline.state import PipelineState
from app.safety.validator import validate


def validate_sql(state: PipelineState) -> dict[str, object]:
    result = validate(
        state.get("sql", ""),
        state["dialect"],
        set(state["schema_tables"]),
        state["max_rows"],
    )
    return {
        "validation": result,
        "sql": result.sql or state.get("sql", ""),
        "error": None if result.ok else result.reason,
    }
