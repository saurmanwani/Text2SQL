import re
from typing import Any

EMAIL_PATTERN = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
PHONE_PATTERN = re.compile(r"(?<!\w)(?:\+?\d[\d\s().-]{7,}\d)(?!\w)")
LONG_NUMBER_PATTERN = re.compile(r"\b\d{12,}\b")


def redact_value(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    redacted = EMAIL_PATTERN.sub("[REDACTED_EMAIL]", value)
    redacted = LONG_NUMBER_PATTERN.sub("[REDACTED_NUMBER]", redacted)
    redacted = PHONE_PATTERN.sub("[REDACTED_PHONE]", redacted)
    return redacted


def redact_rows(rows: list[list[Any]]) -> list[list[Any]]:
    return [[redact_value(value) for value in row] for row in rows]
