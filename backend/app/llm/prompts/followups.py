def followups_prompt(question: str, schema_text: str) -> str:
    return (
        "Suggest exactly three useful follow-up questions based only on this visible schema. "
        'Return JSON as {"questions": ["...", "...", "..."]}.\n'
        f"Question: {question}\nSchema:\n{schema_text}"
    )
