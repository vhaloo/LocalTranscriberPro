"""Streaming speech boundaries with local Silero VAD, outside the audio callback."""
from __future__ import annotations

from collections.abc import Callable

import numpy as np

SAMPLE_RATE = 16000
FRAME = 512


class StreamingVoiceDetector:
    def __init__(self):
        from faster_whisper.vad import get_vad_model

        self.session = get_vad_model().session
        self.h = np.zeros((1, 1, 128), dtype=np.float32)
        self.c = np.zeros((1, 1, 128), dtype=np.float32)
        self.context = np.zeros(64, dtype=np.float32)

    def __call__(self, audio: np.ndarray) -> float:
        values = np.asarray(audio, dtype=np.float32).reshape(-1)
        if values.size != FRAME:
            raise ValueError("Streaming VAD requires 512 samples")
        inputs = np.concatenate((self.context, values)).reshape(1, -1)
        probability, self.h, self.c = self.session.run(None, {"input": inputs, "h": self.h, "c": self.c})
        self.context = values[-64:].copy()
        return float(np.asarray(probability).reshape(-1)[0])


class SpeechSegmenter:
    """Keep every sample; emit after speech + silence or a bounded long turn.

    A silence is a useful turn boundary, not proof that a different person is
    speaking. The default 700 ms hold avoids cutting most short hesitations.
    """
    def __init__(self, detector: Callable[[np.ndarray], float], maximum_seconds: float = 12,
                 silence_seconds: float = 0.7):
        self.detector = detector
        self.maximum = max(FRAME, int(maximum_seconds * SAMPLE_RATE))
        self.silence_limit = int(silence_seconds * SAMPLE_RATE)
        self.pending = np.empty(0, dtype=np.float32)
        self.parts: list[np.ndarray] = []
        self.samples = 0
        self.silent_samples = 0
        self.voiced_samples = 0
        self.state = "listening"
        self.last_boundary = ""
        self.detector_error = ""

    def feed(self, audio: np.ndarray) -> list[np.ndarray]:
        values = np.concatenate((self.pending, np.asarray(audio, dtype=np.float32).reshape(-1)))
        consumed = values.size // FRAME * FRAME
        self.pending = values[consumed:].copy()
        chunks = []
        for offset in range(0, consumed, FRAME):
            frame = values[offset:offset + FRAME].copy()
            try:
                probability = self.detector(frame)
            except Exception as error:
                self.detector_error = str(error)
                # Retain all audio even when the auxiliary detector fails.
                # The recorder stops after this block and flushes its tail.
                probability = 0.0
            self.parts.append(frame)
            self.samples += FRAME
            if probability >= 0.5:
                self.voiced_samples += FRAME
                self.silent_samples = 0
                self.state = "speech"
            else:
                self.silent_samples += FRAME
                self.state = "end_of_turn" if self.voiced_samples else "listening"
            if (self.voiced_samples >= SAMPLE_RATE * 0.25 and self.silent_samples >= self.silence_limit
                    and self.samples >= SAMPLE_RATE * 0.9):
                self.last_boundary = "silence"
                chunks.append(self._emit())
            elif self.samples >= self.maximum:
                self.last_boundary = "context_limit"
                chunks.append(self._emit())
        return chunks

    def _emit(self) -> np.ndarray:
        result = np.concatenate(self.parts)
        self.parts = []
        self.samples = self.silent_samples = self.voiced_samples = 0
        self.state = "listening"
        return result

    def finish(self) -> np.ndarray:
        parts = [*self.parts, self.pending]
        result = np.concatenate(parts) if parts else np.empty(0, dtype=np.float32)
        self.parts = []
        self.pending = np.empty(0, dtype=np.float32)
        self.samples = self.silent_samples = self.voiced_samples = 0
        self.state = "listening"
        return result

    def snapshot(self) -> dict:
        return {"state": self.state, "seconds": (self.samples + self.pending.size) / SAMPLE_RATE,
                "silence": min(1.0, self.silent_samples / self.silence_limit),
                "maximum_seconds": self.maximum / SAMPLE_RATE, "boundary": self.last_boundary}
