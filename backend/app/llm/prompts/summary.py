from typing import Any


def summary_prompt(question: str, columns: list[str], rows: list[list[Any]]) -> str:
    return (
        "Answer the question from these query results in 3-5 concise lines. "
        "Do not invent information.\n"
        f"Question: {question}\nColumns: {columns}\nRows: {rows[:20]}"
    )
