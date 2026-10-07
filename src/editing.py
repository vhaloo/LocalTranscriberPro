"""Apply editor text corrections to timed segments without changing timing."""

from __future__ import annotations

from difflib import SequenceMatcher
from typing import Any


def apply_text_edits(segments: list[dict[str, Any]], rendered: str, edited: str) -> list[dict[str, Any]]:
    if rendered == edited:
        return list(segments)
    if not segments:
        return [{"start": 0.0, "end": 0.0, "text": edited.strip(), "words": []}] if edited.strip() else []
    if not edited.strip():
        return []
    matcher = SequenceMatcher(None, rendered, edited, autojunk=False)
    if matcher.ratio() < 0.45:
        # A complete rewrite has no trustworthy per-segment text anchors. Keep
        # its entire content and original session range rather than truncating
        # new words to old formatting offsets or inventing word timestamps.
        return [{"start": segments[0].get("start", 0.0), "end": segments[-1].get("end", 0.0),
                 "text": edited.strip(), "words": [], "edited": True}]
    opcodes = matcher.get_opcodes()

    def map_position(position: int, end: bool = False) -> int:
        if end and position == len(rendered):
            return len(edited)
        for tag, old_start, old_end, new_start, new_end in opcodes:
            if old_start <= position <= old_end:
                if tag == "equal":
                    return new_start + position - old_start
                if tag == "insert":
                    return new_end if end else new_start
                if old_end == old_start:
                    return new_end
                fraction = (position - old_start) / (old_end - old_start)
                return round(new_start + fraction * (new_end - new_start))
        return len(edited)

    result = []
    cursor = 0
    for item in segments:
        original = str(item.get("text", "")).strip()
        start = rendered.find(original, cursor) if original else -1
        if start < 0:
            result.append(dict(item))
            continue
        finish = start + len(original)
        text = edited[map_position(start) : map_position(finish, end=True)].strip()
        updated = dict(item, text=text)
        if text != original:
            # Word timings no longer describe the edited words. Keep segment
            # timing and explicitly mark the correction rather than invent it.
            updated["words"] = []
            updated["edited"] = True
        result.append(updated)
        cursor = finish
    return result
