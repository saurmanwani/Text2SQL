from app.llm.prompts.summary import summary_prompt
from app.pipeline.state import PipelineState
from app.safety.redact import redact_rows


async def summarize(state: PipelineState) -> dict[str, object]:
    if state.get("error"):
        return {"summary": None, "summary_reason": "query_error"}
    if not state["summaries_enabled"]:
        return {"summary": None, "summary_reason": "cloud_summaries_disabled"}

    rows = state.get("rows", [])
    if state.get("redact_before_summary", False):
        rows = redact_rows(rows)
    try:
        summary = await state["llm"].chat(
            [
                {
                    "role": "user",
                    "content": summary_prompt(state["question"], state.get("columns", []), rows),
                }
            ],
        )
        return {"summary": summary, "summary_reason": None}
    except Exception:
        return {"summary": None, "summary_reason": "summary_error"}
