"""Shared formatting, logging and safe file helpers."""

from __future__ import annotations

import datetime as dt
import logging
import re
import sys
from collections.abc import Callable, Iterable
from pathlib import Path
from typing import Any

from platformdirs import user_log_dir


def setup_logging() -> Path:
    log_dir = Path(user_log_dir("LocalTranscriberPro", "Vhaloo"))
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / "app.log"
    logging.basicConfig(
        filename=log_path,
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        encoding="utf-8",
    )
    return log_path


class StdErrRedirector:
    """Compatibility progress parser for libraries that only print progress."""

    def __init__(self, callback: Callable[[float], None]):
        self.callback = callback
        self.original_stderr = sys.stderr

    def write(self, buf: str) -> None:
        if self.original_stderr:
            self.original_stderr.write(buf)
        match = re.search(r"(\d+(?:\.\d+)?)%", buf)
        if match:
            try:
                self.callback(min(1.0, float(match.group(1)) / 100.0))
            except (TypeError, ValueError):
                pass

    def flush(self) -> None:
        if self.original_stderr:
            self.original_stderr.flush()

    def start(self) -> None:
        sys.stderr = self

    def stop(self) -> None:
        sys.stderr = self.original_stderr


def format_timestamp(seconds: float, decimal: str = ",") -> str:
    milliseconds = max(0, int(round(float(seconds) * 1000)))
    hours, remainder = divmod(milliseconds, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    secs, millis = divmod(remainder, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}{decimal}{millis:03d}"


def create_srt_content(segments: Iterable[dict[str, Any]]) -> str:
    blocks = []
    for index, segment in enumerate(segments, start=1):
        text = str(segment.get("text", "")).strip()
        if not text:
            continue
        blocks.append(
            f"{index}\n{format_timestamp(segment.get('start', 0))} --> "
            f"{format_timestamp(segment.get('end', 0))}\n{text}"
        )
    return "\n\n".join(blocks) + ("\n" if blocks else "")


def create_vtt_content(segments: Iterable[dict[str, Any]]) -> str:
    blocks = ["WEBVTT"]
    for segment in segments:
        text = str(segment.get("text", "")).strip()
        if not text:
            continue
        blocks.append(
            f"{format_timestamp(segment.get('start', 0), '.')} --> "
            f"{format_timestamp(segment.get('end', 0), '.')}\n{text}"
        )
    return "\n\n".join(blocks) + "\n"


def timestamped_name(prefix: str = "Transcription") -> str:
    return f"{prefix}_{dt.datetime.now():%Y-%m-%d_%H-%M-%S}"


def atomic_write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(content, encoding="utf-8")
    temporary.replace(path)
