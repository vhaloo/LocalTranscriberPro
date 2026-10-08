"""Validation and timeline transforms shared by exports, history and recording."""

from __future__ import annotations

import math
from typing import Any


def validate_segments(values: Any) -> list[dict[str, Any]]:
    if not isinstance(values, list):
        raise ValueError("A transcript must contain a segment list")
    result = []
    for item in values:
        if not isinstance(item, dict) or not isinstance(item.get("text", ""), str):
            raise ValueError("Invalid transcript segment")
        for field in ("source_text", "source_language", "target_language", "third_text", "third_language"):
            if field in item and not isinstance(item[field], str):
                raise ValueError(f"Invalid transcript {field}")
        for field, maximum in (("recognition_index", 100), ("translation_index", 100),
                               ("third_translation_index", 100), ("language_probability", 1)):
            if item.get(field) is not None:
                value = item[field]
                if not isinstance(value, (int, float)) or not math.isfinite(value) or not 0 <= value <= maximum:
                    raise ValueError(f"Invalid transcript {field}")
        start, end = float(item.get("start", 0)), float(item.get("end", 0))
        if not math.isfinite(start) or not math.isfinite(end) or start < 0 or end < start:
            raise ValueError("Invalid transcript timing")
        result.append(dict(item, start=start, end=end))
    return result


def shift_segments(segments: list[dict[str, Any]], offset: float) -> list[dict[str, Any]]:
    result = []
    for item in segments:
        shifted = dict(item, start=item["start"] + offset, end=item["end"] + offset)
        for field in ("words", "source_words"):
            if field in item or field == "words":
                shifted[field] = [dict(word, start=word["start"] + offset, end=word["end"] + offset)
                                  for word in item.get(field, [])]
        result.append(shifted)
    return result
