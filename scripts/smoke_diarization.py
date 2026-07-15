"""Exercise the bundled speaker-labeling path on a real audio file."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.diarizer import Diarizer  # noqa: E402
from src.hardware import detect_hardware  # noqa: E402
from src.transcriber import TranscriberEngine, TranscriptionOptions  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("audio", type=Path)
    args = parser.parse_args()

    engine = TranscriberEngine(detect_hardware())
    engine.load_model("large-v3", "auto")
    result = engine.transcribe_file(args.audio, TranscriptionOptions(language="fr"))
    diarizer = Diarizer()
    segments = diarizer.process(str(args.audio), result["segments"])
    print(
        json.dumps(
            {
                "enabled": diarizer.enabled,
                "segments": segments,
                "speakers": sorted({item.get("speaker") for item in segments if item.get("speaker")}),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0 if any(item.get("speaker") for item in segments) else 2


if __name__ == "__main__":
    raise SystemExit(main())
