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
        start, end = float(item.get("start", 0)), float(item.get("end", 0))
        if not math.isfinite(start) or not math.isfinite(end) or start < 0 or end < start:
            raise ValueError("Invalid transcript timing")
        result.append(dict(item, start=start, end=end))
    return result


def shift_segments(segments: list[dict[str, Any]], offset: float) -> list[dict[str, Any]]:
    return [dict(item, start=item["start"] + offset, end=item["end"] + offset,
                 words=[dict(word, start=word["start"] + offset, end=word["end"] + offset)
                        for word in item.get("words", [])]) for item in segments]
