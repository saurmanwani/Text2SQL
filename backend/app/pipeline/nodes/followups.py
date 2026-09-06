import json

from app.llm.prompts.followups import followups_prompt
from app.pipeline.state import PipelineState


async def followups(state: PipelineState) -> dict[str, object]:
    try:
        content = await state["llm"].chat(
            [
                {
                    "role": "user",
                    "content": followups_prompt(state["question"], state["schema_text"]),
                }
            ],
            json_mode=True,
        )
        questions = json.loads(content).get("questions", [])
        return {"followups": [str(question) for question in questions[:3]]}
    except Exception:
        return {"followups": []}
