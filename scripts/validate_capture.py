"""Short native input-stream check. Never saves or transcribes captured audio."""
from __future__ import annotations

import argparse
import json
import threading
from pathlib import Path

import sounddevice as sd


def validate(seconds=2):
    done = threading.Event()
    report = {"frames": 0, "overflows": 0, "sample_rate": 16000, "audio_saved": False}
    def callback(data, frames, when, status):
        report["frames"] += frames
        report["overflows"] += int(bool(status))
        if report["frames"] >= seconds * 16000:
            done.set()
    with sd.InputStream(channels=1, samplerate=16000, blocksize=1024, callback=callback):
        report["success"] = done.wait(seconds + 5)
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = validate()
    except Exception as error:
        result = {"success": False, "error": type(error).__name__, "audio_saved": False}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2), "utf-8")
    print(json.dumps(result))
    raise SystemExit(0 if result["success"] else 1)
