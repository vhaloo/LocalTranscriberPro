"""Controlled two-voice mixture diagnostic, using private held-out fixtures."""
from __future__ import annotations

import itertools
import json
import socket
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.media import iter_audio_chunks  # noqa: E402
from src.overlap import OverlapSeparator  # noqa: E402


def si_sdr(estimate, reference):
    estimate = estimate - estimate.mean()
    reference = reference - reference.mean()
    target = reference * (np.dot(estimate, reference) / (np.dot(reference, reference) + 1e-9))
    return float(10 * np.log10((np.dot(target, target) + 1e-9) / (np.sum((estimate - target) ** 2) + 1e-9)))


if __name__ == "__main__":
    folder = ROOT / "artifacts/dialect-tests"
    manifest = json.loads((folder / "manifest.json").read_text(encoding="utf-8"))
    report = []
    original_connect = socket.socket.connect
    socket.socket.connect = lambda *_: (_ for _ in ()).throw(RuntimeError("Network prohibited"))
    try:
        separator = OverlapSeparator()
        separator.load(allow_download=False)
        for pair in [("en_us", "fr_fr"), ("Morocco", "fr_fr")]:
            sources = []
            for code in pair:
                clip = next(item for item in manifest if item["config"] == code)
                audio = np.concatenate([part for _, part in iter_audio_chunks(str(folder / clip["file"]))])[:96000]
                audio = np.pad(audio, (0, 96000 - len(audio)))
                sources.append(audio * (0.1 / max(1e-9, np.sqrt(np.mean(audio ** 2)))))
            mixture = sum(sources)
            started = time.monotonic()
            outputs = separator.separate(mixture)
            elapsed = time.monotonic() - started
            assert len(outputs) == 2 and all(len(audio) == 96000 and np.isfinite(audio).all() for audio in outputs)
            assignment = max(itertools.permutations(range(2)), key=lambda order: sum(
                si_sdr(outputs[order[index]], reference) for index, reference in enumerate(sources)))
            baseline = [si_sdr(mixture, reference) for reference in sources]
            scores = [si_sdr(outputs[assignment[index]], reference) for index, reference in enumerate(sources)]
            report.append(dict(languages=pair, samples=96000, processing_seconds=elapsed,
                               mixture_si_sdr_db=baseline, separated_si_sdr_db=scores,
                               average_improvement_db=float(np.mean(np.asarray(scores) - baseline))))
    finally:
        socket.socket.connect = original_connect
    (folder / "overlap-results.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
