"""Run a real local transcription and print machine-readable diagnostics."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.hardware import detect_hardware  # noqa: E402
from src.transcriber import TranscriberEngine, TranscriptionOptions  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("audio", type=Path)
    parser.add_argument("--model", default="tiny")
    parser.add_argument("--device", default="auto")
    parser.add_argument("--language", default=None)
    args = parser.parse_args()

    hardware = detect_hardware()
    engine = TranscriberEngine(hardware)
    status = engine.load_model(args.model, args.device)
    progress = []
    result = engine.transcribe_file(
        args.audio,
        TranscriptionOptions(language=args.language, beam_size=5, vad_filter=True),
        progress.append,
    )
    print(
        json.dumps(
            {
                "hardware": hardware.as_dict(),
                "status": status.__dict__,
                "text": result.get("text", ""),
                "language": result.get("language"),
                "duration": result.get("duration"),
                "processing_seconds": result.get("processing_seconds"),
                "progress_completed": bool(progress and progress[-1] == 1.0),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0 if result.get("text", "").strip() else 2


if __name__ == "__main__":
    raise SystemExit(main())
