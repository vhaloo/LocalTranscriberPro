"""Bounded audio decoding for modern ASR and long recordings."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import numpy as np

SAMPLE_RATE = 16000


def iter_audio_chunks(source: str | np.ndarray, seconds: float = 25.0) -> Iterator[tuple[float, np.ndarray]]:
    """Decode one window at a time, cutting near silence when possible.

    Offset always describes the original timeline, including silence. PyAV
    handles audio and video without an external executable or full-file RAM.
    """
    import av

    limit = int(seconds * SAMPLE_RATE)
    if limit < SAMPLE_RATE:
        raise ValueError("Audio windows must be at least one second")

    def frames() -> Iterator[np.ndarray]:
        if isinstance(source, np.ndarray):
            data = np.asarray(source, dtype=np.float32)
            if data.ndim > 1:
                data = data.mean(axis=1)
            data = data.reshape(-1)
            for start in range(0, len(data), limit):
                yield data[start : start + limit]
            return
        if not Path(source).is_file():
            raise FileNotFoundError(source)
        with av.open(source) as container:
            stream = next((item for item in container.streams.audio), None)
            if stream is None:
                raise ValueError("The file does not contain an audio track")
            resampler = av.AudioResampler(format="fltp", layout="mono", rate=SAMPLE_RATE)
            for frame in container.decode(stream):
                for converted in resampler.resample(frame):
                    yield converted.to_ndarray().reshape(-1)
            for converted in resampler.resample(None):
                yield converted.to_ndarray().reshape(-1)

    pending = np.empty(0, dtype=np.float32)
    consumed = 0
    for frame in frames():
        pending = np.concatenate((pending, frame))
        while len(pending) >= limit:
            # Prefer a quiet 80 ms boundary in the final five seconds.
            begin = max(SAMPLE_RATE, limit - 5 * SAMPLE_RATE)
            width = 1280
            region = pending[begin:limit]
            bins = len(region) // width
            cut = limit
            if bins:
                energies = np.mean(region[: bins * width].reshape(bins, width) ** 2, axis=1)
                best = int(np.argmin(energies))
                if energies[best] < 0.0001:
                    cut = begin + (best + 1) * width
            yield consumed / SAMPLE_RATE, pending[:cut].copy()
            consumed += cut
            pending = pending[cut:]
    if len(pending):
        yield consumed / SAMPLE_RATE, pending.copy()


class RecordingSpool:
    """Keep microphone audio on disk; memory stays bounded for endless dictation."""

    def __init__(self, path: Path):
        import soundfile as sf

        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        self._file = sf.SoundFile(path, mode="w", samplerate=SAMPLE_RATE, channels=1, subtype="PCM_16")

    def append(self, audio: np.ndarray) -> None:
        import shutil

        if shutil.disk_usage(self.path.parent).free < 250 * 1024**2:
            raise OSError("Recording stopped because less than 250 MB of storage remains. Captured audio was preserved.")
        self._file.write(np.asarray(audio, dtype=np.float32).reshape(-1))
        self._file.flush()

    def close(self) -> None:
        self._file.close()
