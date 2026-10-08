"""Cooperative cancellation shared by inference, downloads and the interface."""

from __future__ import annotations

import threading


class JobCancelled(Exception):
    """The user cancelled a job; completed outputs remain available."""


def check_cancelled(event: threading.Event | None) -> None:
    if event is not None and event.is_set():
        raise JobCancelled("Transcription cancelled")
