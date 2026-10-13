"""Terminal-safe text and display-column wrapping shared by all layouts."""

from __future__ import annotations

import json
import unicodedata
from typing import Any


def display_width(value: str) -> int:
    """Measure ordinary terminal labels, including wide and combining characters."""
    return sum(
        0 if unicodedata.combining(char) or char == "\u200d" else
        2 if unicodedata.east_asian_width(char) in {"W", "F"} else 1
        for char in value
    )


def clean(value: Any) -> str:
    if value is None:
        return ""
    if not isinstance(value, str):
        value = json.dumps(value, ensure_ascii=False, sort_keys=True)
    return "".join(
        char if char in "\n\t" or unicodedata.category(char) != "Cc"
        else "\\x%02x" % ord(char)
        for char in value
    ).expandtabs(2)


def _chunks(word: str, limit: int) -> list[str]:
    parts: list[str] = []
    current = ""
    for char in word:
        if current and display_width(current + char) > limit:
            parts.append(current)
            current = ""
        current += char
    if current:
        parts.append(current)
    return parts or [""]


def wrap_text(value: Any, limit: int) -> list[str]:
    """Wrap while retaining complete words and all non-whitespace source characters."""
    limit = max(2, limit)
    result: list[str] = []
    for paragraph in clean(value).split("\n"):
        if not paragraph.strip():
            result.append("")
            continue
        indentation = paragraph[:len(paragraph) - len(paragraph.lstrip(" "))]
        indentation = indentation[:max(0, limit - 2)]
        current = indentation
        for word in paragraph.lstrip(" ").split():
            parts = _chunks(word, limit)
            for part_number, part in enumerate(parts):
                separator = " " if current.strip() and part_number == 0 else ""
                if current and display_width(current + separator + part) > limit:
                    result.append(current)
                    current = ""
                    separator = ""
                current += separator + part
                if part_number < len(parts) - 1:
                    result.append(current)
                    current = ""
        result.append(current)
    return result or [""]


