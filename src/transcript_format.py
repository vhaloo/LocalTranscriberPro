"""Human-readable transcript layouts used by the editor and TXT exports."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

from src.utils import format_timestamp


@dataclass(frozen=True)
class TranscriptFormat:
    mode: str = "blocks"
    show_timestamps: bool = True
    show_duration: bool = False


def _duration_label(seconds: float) -> str:
    value = max(0.0, seconds)
    return f"{value:.1f} s" if value < 10 else f"{round(value):d} s"


def _prefix(start: float, end: float, speaker: str, options: TranscriptFormat) -> str:
    details: list[str] = []
    if options.show_timestamps:
        details.append(format_timestamp(start, ".")[:8])
    if options.show_duration:
        details.append(_duration_label(end - start))
    marker = f"[{' • '.join(details)}] " if details else ""
    voice = f"[{speaker}] " if speaker else ""
    return marker + voice


def format_segment(segment: dict[str, Any], options: TranscriptFormat) -> str:
    text = str(segment.get("text", "")).strip()
    if not text:
        return ""
    start = float(segment.get("start", 0.0))
    end = float(segment.get("end", start))
    return f"{_prefix(start, end, str(segment.get('speaker', '')), options)}{text}"


def _blocks(segments: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Join adjacent phrases into readable paragraphs without hiding timing data."""
    blocks: list[dict[str, Any]] = []
    for segment in segments:
        text = str(segment.get("text", "")).strip()
        if not text:
            continue
        speaker = str(segment.get("speaker", ""))
        start = float(segment.get("start", 0.0))
        end = float(segment.get("end", start))
        previous = blocks[-1] if blocks else None
        can_join = bool(
            previous
            and str(previous.get("speaker", "")) == speaker
            and start - float(previous.get("end", 0.0)) <= 2.5
            and end - float(previous.get("start", 0.0)) <= 45.0
            and len(str(previous.get("text", ""))) + len(text) < 700
        )
        if can_join and previous is not None:
            previous["text"] = f"{previous['text']} {text}"
            previous["end"] = end
        else:
            blocks.append({"start": start, "end": end, "speaker": speaker, "text": text})
    return blocks


def format_transcript(
    segments: Iterable[dict[str, Any]],
    options: TranscriptFormat | None = None,
) -> str:
    selected = options or TranscriptFormat()
    values = list(segments)
    if selected.mode == "blocks":
        values = _blocks(values)
        separator = "\n\n"
    else:
        separator = "\n"
    rendered = [format_segment(item, selected) for item in values]
    return separator.join(value for value in rendered if value)
