"""Shared formatting, logging and safe file helpers."""

from __future__ import annotations

import datetime as dt
import logging
import os
import re
import sys
import tempfile
import threading
import time
from collections.abc import Callable, Iterable
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any

from platformdirs import user_log_dir

_ATOMIC_REPLACE_LOCK = threading.Lock()


def setup_logging() -> Path:
    log_dir = Path(user_log_dir("LocalTranscriberPro", "Vhaloo"))
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / "app.log"
    logging.basicConfig(
        handlers=[RotatingFileHandler(log_path, maxBytes=5 * 1024**2, backupCount=3, encoding="utf-8")],
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
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
    for segment in segments:
        text = subtitle_text(segment)
        if not text:
            continue
        blocks.append(
            f"{len(blocks) + 1}\n{format_timestamp(segment.get('start', 0))} --> "
            f"{format_timestamp(segment.get('end', 0))}\n{text}"
        )
    return "\n\n".join(blocks) + ("\n" if blocks else "")


def create_vtt_content(segments: Iterable[dict[str, Any]]) -> str:
    blocks = ["WEBVTT"]
    for segment in segments:
        text = subtitle_text(segment)
        if not text:
            continue
        blocks.append(
            f"{format_timestamp(segment.get('start', 0), '.')} --> "
            f"{format_timestamp(segment.get('end', 0), '.')}\n{text}"
        )
    return "\n\n".join(blocks) + "\n"


def subtitle_text(segment: dict[str, Any]) -> str:
    if "source_text" in segment:
        # Import lazily: transcript_format also uses format_timestamp here.
        from src.transcript_format import TranscriptFormat, format_segment

        return format_segment(segment, TranscriptFormat(show_timestamps=False, show_duration=False))
    return str(segment.get("text", "")).strip()


def timestamped_name(prefix: str = "Transcription") -> str:
    return f"{prefix}_{dt.datetime.now():%Y-%m-%d_%H-%M-%S}"


def atomic_write_text(path: Path, content: str, encoding: str = "utf-8") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding=encoding, dir=path.parent,
                                         prefix=f".{path.name}.", suffix=".tmp", delete=False) as handle:
            temporary = Path(handle.name)
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        # Windows can reject concurrent replaces of the same destination, or a
        # brief antivirus/indexer handle. Keep replacement atomic and retry only
        # transient sharing/access errors; other failures remain visible.
        with _ATOMIC_REPLACE_LOCK:
            for attempt in range(5):
                try:
                    temporary.replace(path)
                    break
                except PermissionError as error:
                    if getattr(error, "winerror", None) not in {5, 32, 33} or attempt == 4:
                        raise
                    time.sleep(0.02 * 2**attempt)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
