from app.llm.prompts.dialects import DIALECT_RULES
from app.pipeline.state import HistoryTurn


def generation_prompt(
    question: str,
    dialect: str,
    schema_text: str,
    history: list[HistoryTurn],
    examples: list[dict[str, object]],
    previous_error: str | None,
) -> str:
    history_text = "\n".join(
        f"Question: {turn['question']}\nSQL: {turn['sql']}" for turn in history[-3:]
    )
    retry_text = f"\nPrevious SQL was rejected because: {previous_error}" if previous_error else ""
    examples_text = "\n".join(
        f"Verified question: {example.get('question')}\nVerified SQL: {example.get('sql')}"
        for example in examples
    )
    return f"""
Generate one read-only SQL query that answers the question.
{DIALECT_RULES[dialect]}
Use only tables and columns shown in the schema.
Return JSON exactly as {{"sql": "...", "unanswerable": false, "reason": ""}}.
If the schema cannot answer it, set unanswerable to true and explain why.

Schema:
{schema_text}

Previous questions and their SQL:
{history_text or "None"}

Similar verified examples:
{examples_text or "None"}

Question: {question}{retry_text}
""".strip()
