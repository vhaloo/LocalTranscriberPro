"""Reproducible small-sample ASR/translation diagnostics; not certification."""
from __future__ import annotations

import argparse
import json
import re
import socket
import sys
import time
import unicodedata
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.hardware import detect_hardware  # noqa: E402
from src.media import iter_audio_chunks  # noqa: E402
from src.models import get_model  # noqa: E402
from src.transcriber import TranscriberEngine, TranscriptionOptions  # noqa: E402
from src.translation_languages import normalize_language  # noqa: E402


def normalized(text):
    text = re.sub(r"\[[^\]]*\]", " ", text)
    text = unicodedata.normalize("NFKC", text).casefold().translate(str.maketrans("أإآٱى", "ااااي"))
    return " ".join("".join(char if char.isalnum() or char.isspace() else " "
                            for char in text if unicodedata.category(char) != "Mn" and char != "ـ").split())


def distance(left, right):
    row = list(range(len(right) + 1))
    for index, a in enumerate(left, 1):
        next_row = [index]
        for column, b in enumerate(right, 1):
            next_row.append(min(next_row[-1] + 1, row[column] + 1, row[column - 1] + (a != b)))
        row = next_row
    return row[-1]


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="auto-multilingual")
    parser.add_argument("--asr-only", action="store_true")
    parser.add_argument("--folder", type=Path, default=ROOT / "artifacts/dialect-tests")
    parser.add_argument("--report-folder", type=Path)
    args = parser.parse_args()
    folder = args.folder
    report_folder = args.report_folder or folder
    report_folder.mkdir(parents=True, exist_ok=True)
    manifest = json.loads((folder / "manifest.json").read_text(encoding="utf-8"))
    engine = TranscriberEngine(detect_hardware())
    options = TranscriptionOptions(target_language=None if args.asr_only else "fr", offline=True, beam_size=8,
                                   word_timestamps=False)
    original_connect = socket.socket.connect
    socket.socket.connect = lambda *_: (_ for _ in ()).throw(RuntimeError("Network prohibited during model loading and inference"))
    report = []
    try:
        status = engine.load_model(args.model, "auto", options=options)
        if not args.model.startswith("auto-") and status.model_id != args.model:
            raise RuntimeError(f"Benchmark aborted: requested {args.model}, loaded fallback {status.model_id}")
        print("Models loaded:", status, flush=True)
        for clip in manifest:
            expected = "ht" if clip["dataset"].endswith("cmu_haitian") else "ar" if clip["dataset"].endswith("Casablanca") else {
                "cmn_hans_cn": "zh", "yue_hant_hk": "yue"}.get(clip["config"], clip["config"].split("_")[0])
            if not get_model(status.model_id).supports(expected, "transcribe"):
                report.append({"config": clip["config"], "row": clip["row"], "skipped": "outside declared model coverage"})
                continue
            audio = np.concatenate([part for _, part in iter_audio_chunks(str(folder / clip["file"]))])
            started = time.monotonic()
            result = engine.transcribe_audio(audio, options)
            elapsed = time.monotonic() - started
            source = result.get("source_text", result.get("text", ""))
            reference, hypothesis = normalized(clip["reference"]), normalized(source)
            reference_chars, hypothesis_chars = reference.replace(" ", ""), hypothesis.replace(" ", "")
            value = dict(clip, hypothesis=source, translated=result["text"], detected_language=result.get("language"),
                language_match=normalize_language(result.get("language")) == expected,
                character_edits=distance(reference_chars, hypothesis_chars), reference_characters=len(reference_chars),
                word_edits=distance(reference.split(), hypothesis.split()), reference_words=len(reference.split()),
                processing_seconds=elapsed, translation_device=result.get("translation_device"),
                indices=[{key: segment.get(key) for key in ("recognition_index", "translation_index", "language_probability")}
                         for segment in result["segments"]])
            report.append(value)
            (report_folder / ("results-" + args.model + ".json")).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
            print(clip["config"], clip["row"], result.get("language"),
                  round(value["character_edits"] / max(1, value["reference_characters"]), 3), round(elapsed, 2), flush=True)
    finally:
        socket.socket.connect = original_connect
    print("Completed", len(report), "clips, with network connections blocked.", flush=True)
