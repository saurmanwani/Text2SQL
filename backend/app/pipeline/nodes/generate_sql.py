import json

from app.llm.prompts.generate import generation_prompt
from app.pipeline.state import PipelineState


async def generate_sql(state: PipelineState) -> dict[str, object]:
    prompt = generation_prompt(
        question=state["question"],
        dialect=state["dialect"],
        schema_text=state["schema_text"],
        history=state.get("history", []),
        previous_error=state.get("error"),
    )
    attempt = state.get("attempt", 0) + 1
    try:
        content = await state["llm"].chat(
            [{"role": "user", "content": prompt}],
            json_mode=True,
        )
        payload = json.loads(content)
        return {
            "sql": str(payload.get("sql", "")),
            "unanswerable": bool(payload.get("unanswerable", False)),
            "unanswerable_reason": payload.get("reason"),
            "attempt": attempt,
            "error": None,
        }
    except (json.JSONDecodeError, TypeError, ValueError) as exc:
        return {
            "sql": "",
            "unanswerable": False,
            "attempt": attempt,
            "error": f"invalid_model_response: {exc}",
        }
