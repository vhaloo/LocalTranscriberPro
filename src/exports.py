"""UI-independent, atomic exports shared by jobs, recovery and the editor."""

from __future__ import annotations

import csv
import io
import json
from pathlib import Path
from typing import Any

from src.transcript_format import TranscriptFormat, format_transcript
from src.utils import atomic_write_text, create_srt_content, create_vtt_content


def write_export(path: Path, segments: list[dict[str, Any]], options: TranscriptFormat | None = None,
                 text_override: str | None = None) -> None:
    suffix = path.suffix.lower()
    encoding = "utf-8"
    if suffix == ".txt":
        content = (text_override if text_override is not None else format_transcript(segments, options)).rstrip() + "\n"
    elif suffix == ".srt":
        content = create_srt_content(segments)
    elif suffix == ".vtt":
        content = create_vtt_content(segments)
    elif suffix == ".json":
        content = json.dumps(segments, ensure_ascii=False, indent=2)
    elif suffix == ".csv":
        buffer = io.StringIO(newline="")
        writer = csv.writer(buffer)
        fields = ("start", "end", "speaker", "source", "text")
        if any("source_text" in item for item in segments):
            fields += ("source_language", "source_text", "target_language", "third_language", "third_text")
        writer.writerow(fields)
        for item in segments:
            # Prevent text from being interpreted as a formula by spreadsheet
            # software; the structured JSON keeps the unmodified original.
            row = [item.get(field, "" if field not in {"start", "end"} else 0) for field in fields]
            writer.writerow(["'" + value if isinstance(value, str) and value.startswith(("=", "+", "-", "@")) else value
                             for value in row])
        content, encoding = buffer.getvalue(), "utf-8-sig"
    else:
        raise ValueError(f"Unsupported transcript export: {suffix}")
    atomic_write_text(path, content, encoding)


def write_bundle(base: Path, segments: list[dict[str, Any]], options: TranscriptFormat | None = None) -> Path | None:
    if not segments:
        return None
    for suffix in (".txt", ".srt", ".vtt", ".json", ".csv"):
        write_export(base.with_suffix(suffix), segments, options)
    return base.with_suffix(".txt")
