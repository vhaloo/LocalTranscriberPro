"""Exercise an installed/frozen Windows package with real cached local models.

Run from the repository after placing the official Sherpa sample-fr.wav and
sample-en.wav in artifacts/. No audio or transcript is uploaded by this script.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import time
from pathlib import Path

import numpy as np
import soundfile as sf


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("executable", type=Path)
    parser.add_argument("--prefix", default="package")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    artifacts = root / "artifacts"
    # Include source gaps and stereo resampling in the long-media case.
    voice, rate = sf.read(artifacts / "sample-fr.wav", dtype="float32")
    if voice.ndim > 1:
        voice = voice.mean(axis=1)
    long_audio = np.zeros(75 * rate, dtype=np.float32)
    for seconds in (0, 30, 60):
        start = seconds * rate
        long_audio[start:start + len(voice)] = voice
    sf.write(artifacts / "long-fr-stereo.wav", np.column_stack((long_audio, long_audio)), rate)
    sf.write(artifacts / "silence.wav", np.zeros(32 * 16000), 16000)

    cases = [
        ("qwen-en", "sample-en.wav", "auto-best", "auto", "en", [], "qwen3-asr"),
        ("qwen-long-fr", "long-fr-stereo.wav", "auto-best", "auto", "fr", [], "qwen3-asr"),
        ("parakeet-fr", "sample-fr.wav", "auto-fast", "auto", "fr", [], "parakeet-onnx"),
        ("whisper-translate", "sample-fr.wav", "auto-best", "auto", "fr", ["--task", "translate"], "faster-whisper"),
        ("qwen-silence", "silence.wav", "auto-best", "auto", "fr", ["--expect-silence"], "qwen3-asr"),
    ]
    environment = dict(os.environ, HF_HUB_OFFLINE="1", HF_HUB_DISABLE_TELEMETRY="1")
    summary = []
    for name, source, model, device, language, flags, backend in cases:
        output = artifacts / f"{args.prefix}-{name}.json"
        command = [str(args.executable.resolve()), "--smoke-test", str(artifacts / source),
                   "--model", model, "--device", device, "--language", language,
                   "--diagnostic-output", str(output), *flags]
        started = time.monotonic()
        process = subprocess.run(command, cwd=root, env=environment, timeout=900,
                                 creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
        report = json.loads(output.read_text(encoding="utf-8"))
        success = process.returncode == 0 and report.get("success") and report.get("progress_completed")
        success = success and report.get("status", {}).get("backend") == backend
        if name == "qwen-long-fr":
            starts = [item["start"] for item in report.get("segments", [])]
            success = success and any(value > 58 for value in starts) and len(starts) >= 3
        if name == "whisper-translate":
            success = success and "country" in report.get("text", "").lower()
        summary.append({"case": name, "passed": bool(success), "status": report.get("status"),
                        "elapsed_seconds": round(time.monotonic() - started, 2), "text": report.get("text"),
                        "report": str(output), "error": report.get("error")})
        print(json.dumps(summary[-1], ensure_ascii=False), flush=True)
    (artifacts / f"{args.prefix}-summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    return 0 if all(item["passed"] for item in summary) else 2


if __name__ == "__main__":
    raise SystemExit(main())
