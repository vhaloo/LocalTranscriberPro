"""ETA estimates that learn from completed transcriptions on this computer."""

from __future__ import annotations

import math
from dataclasses import dataclass

from src.models import get_model


@dataclass
class Estimate:
    seconds: float
    source: str


class TimeEstimator:
    def __init__(self, benchmarks: dict[str, float] | None = None):
        self.benchmarks = dict(benchmarks or {})

    @staticmethod
    def key(model_id: str, device: str) -> str:
        return f"{model_id}:{device}"

    def estimate(self, audio_seconds: float, model_id: str, device: str) -> Estimate:
        if audio_seconds <= 0:
            return Estimate(0.0, "unknown")
        learned = self.benchmarks.get(self.key(model_id, device))
        if learned and learned > 0:
            return Estimate(max(2.0, audio_seconds * learned), "learned")

        model_factor = get_model(model_id).speed_factor
        # Conservative real-time factors. Estimates become machine-specific
        # after the first completed file through ``observe``.
        if device == "cuda":
            rtf = 0.055 * model_factor
        elif device == "metal":
            rtf = 0.12 * model_factor
        else:
            rtf = 2.8 * model_factor
        return Estimate(max(3.0, audio_seconds * rtf), "baseline")

    def observe(
        self,
        audio_seconds: float,
        processing_seconds: float,
        model_id: str,
        device: str,
    ) -> None:
        if audio_seconds <= 1 or processing_seconds <= 0:
            return
        measured = processing_seconds / audio_seconds
        key = self.key(model_id, device)
        old = self.benchmarks.get(key)
        self.benchmarks[key] = measured if old is None else (old * 0.65 + measured * 0.35)


def format_duration(seconds: float) -> str:
    if not math.isfinite(seconds) or seconds < 0:
        return "—"
    total = int(round(seconds))
    hours, remainder = divmod(total, 3600)
    minutes, secs = divmod(remainder, 60)
    if hours:
        return f"{hours:d} h {minutes:02d} min"
    if minutes:
        return f"{minutes:d} min {secs:02d} s"
    return f"{secs:d} s"
