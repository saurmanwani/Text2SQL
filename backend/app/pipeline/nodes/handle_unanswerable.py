from app.pipeline.state import PipelineState


def handle_unanswerable(state: PipelineState) -> dict[str, object]:
    reason = state.get("unanswerable_reason") or "The visible schema cannot answer that question."
    return {
        "unanswerable": True,
        "unanswerable_reason": reason,
        "columns": [],
        "rows": [],
        "summary": None,
    }
