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
from src.transcriber import EngineStatus, TranscriberEngine, TranscriptionOptions  # noqa: E402
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
    parser.add_argument("--resume", action="store_true", help="Continue a partial report for the same model and manifest")
    parser.add_argument("--device", default="auto", choices=("auto", "cpu", "cuda", "metal"))
    parser.add_argument("--compute-type", choices=("int8_float16", "float16", "int8"),
                        help="Explicit diagnostic-only Whisper precision; separate report, without changing app policy")
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
    suffix = f"-{args.device}-{args.compute_type}" if args.compute_type else ""
    report_path = report_folder / ("results-" + args.model + suffix + ".json")
    report = json.loads(report_path.read_text("utf-8")) if args.resume and report_path.is_file() else []
    if len(report) > len(manifest) or any(
        row.get("config") != clip["config"] or row.get("row") != clip["row"]
        or ("sha256" in row and row["sha256"] != clip["sha256"])
        for row, clip in zip(report, manifest, strict=False)
    ):
        raise ValueError("The partial report does not match this input manifest")
    try:
        if args.compute_type:
            if get_model(args.model).family != "whisper" or args.device not in {"cpu", "cuda"} or not args.asr_only:
                raise ValueError("Explicit precision requires Whisper, a concrete device and --asr-only")
            import ctranslate2
            from faster_whisper import WhisperModel
            engine.hardware.refresh_resources()
            if engine.hardware.effective_available_ram_gb < 4:
                raise RuntimeError("Diagnostic needs at least 4 GiB of host commit/RAM headroom")
            if args.device == "cuda" and (not engine.hardware.ctranslate_cuda or
                    engine.hardware.effective_free_vram_gb < max(4.3, get_model(args.model).size_gb * 1.1 + 1)):
                raise RuntimeError("Insufficient real free VRAM for the bounded quantized-GPU diagnostic")
            if args.compute_type not in ctranslate2.get_supported_compute_types(args.device):
                raise RuntimeError("Diagnostic precision is unsupported by this native runtime")
            engine.model = WhisperModel(args.model, device=args.device, compute_type=args.compute_type,
                download_root=str(engine.model_cache), local_files_only=True, cpu_threads=engine.hardware.cpu_threads)
            engine.model_name, engine.device = args.model, args.device
            engine.backend, engine.compute_type = "faster-whisper", args.compute_type
            engine.current_status = status = EngineStatus(args.model, args.device, args.device,
                engine.backend, args.compute_type, args.model)
        else:
            status = engine.load_model(args.model, args.device, options=options)
        if not args.model.startswith("auto-") and status.model_id != args.model:
            raise RuntimeError(f"Benchmark aborted: requested {args.model}, loaded fallback {status.model_id}")
        print("Models loaded:", status, flush=True)
        for clip in manifest[len(report):]:
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
                language_match=normalize_language(result.get("language")) == normalize_language(expected),
                character_edits=distance(reference_chars, hypothesis_chars), reference_characters=len(reference_chars),
                word_edits=distance(reference.split(), hypothesis.split()), reference_words=len(reference.split()),
                processing_seconds=elapsed, translation_device=result.get("translation_device"),
                indices=[{key: segment.get(key) for key in ("recognition_index", "translation_index", "language_probability")}
                         for segment in result["segments"]])
            report.append(value)
            temporary = report_path.with_suffix(".json.tmp")
            temporary.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
            temporary.replace(report_path)
            print(clip["config"], clip["row"], result.get("language"),
                  round(value["character_edits"] / max(1, value["reference_characters"]), 3), round(elapsed, 2), flush=True)
    finally:
        socket.socket.connect = original_connect
    print("Completed", len(report), "clips, with network connections blocked.", flush=True)
