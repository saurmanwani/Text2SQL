from app.pipeline.state import PipelineState


def execute_sql(state: PipelineState) -> dict[str, object]:
    try:
        result = state["connector"].execute(state["sql"], state["max_rows"])
        return {
            "columns": result.columns,
            "rows": result.rows,
            "error": None,
        }
    except Exception as exc:
        return {"columns": [], "rows": [], "error": f"execution_error: {exc}"}
