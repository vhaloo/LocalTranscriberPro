"""Meta Omnilingual CTC 1B v2 with local GlotLID v3 language hints.

The recognizer and text language detector have different language coverage.
Unknown or weak language evidence remains visible to the caller.
"""
from __future__ import annotations

import json
from pathlib import Path

from platformdirs import user_cache_dir

from src.local_assets import prepare_assets
from src.media import SAMPLE_RATE

METADATA = json.loads((Path(__file__).parent / "data/omnilingual.json").read_text(encoding="utf-8"))


def cache_root():
    return Path(user_cache_dir("LocalTranscriberPro", "Vhaloo")) / "omnilingual"


def cached_checkpoint():
    folder = cache_root() / "1b-v2"
    try:
        return all((base / name).is_file() and (base / name).stat().st_size == spec["size"]
                   for base, files in ((folder, METADATA["files"]), (cache_root() / "glotlid", METADATA["lid"]["files"]))
                   for name, spec in files.items())
    except OSError:
        return False


class OmnilingualBackend:
    def __init__(self, threads, offline=False, cancel_event=None):
        root = cache_root()
        folder = prepare_assets(root / "1b-v2", METADATA["repository"], METADATA["revision"],
                                METADATA["files"], not offline, cancel_event)
        spec = METADATA["lid"]
        lid_folder = prepare_assets(root / "glotlid", spec["repository"], spec["revision"],
                                    spec["files"], not offline, cancel_event)
        import fasttext
        import sherpa_onnx

        self.lid = fasttext.load_model(str(lid_folder / "model_v3.bin"))
        self.recognizer = sherpa_onnx.OfflineRecognizer.from_omnilingual_asr_ctc(
            model=str(folder / "model.onnx"), tokens=str(folder / "tokens.txt"),
            num_threads=max(1, min(threads, 8)), provider="cpu")
        self.language_probability = None

    def transcribe_chunk(self, audio, options):
        stream = self.recognizer.create_stream()
        stream.accept_waveform(SAMPLE_RATE, audio)
        self.recognizer.decode_stream(stream)
        text = stream.result.text.strip()
        predictions = self.lid.f.predict(text.replace("\n", " "), 1, 0.0, "strict") if text else []
        probability, label = predictions[0] if predictions else (0.0, "__label__und")
        # fastText adds an epsilon to its softmax output; very confident
        # predictions can be 1.00001 and must remain valid transcript metadata.
        probability = max(0.0, min(1.0, float(probability)))
        iso3 = label.removeprefix("__label__").split("_")[0]
        language = options.language or METADATA["lid"]["iso3_to_language"].get(iso3, iso3)
        if language.startswith(("und", "zxx")):
            language, probability = "und", 0.0
        self.language_probability = probability if not options.language else None
        segments = [{"start": 0.0, "end": len(audio) / SAMPLE_RATE, "text": text, "words": [],
                     "language_detection": "text-glotlid-v3", "timing_precision": "chunk"}] if text else []
        return language, segments, "chunk"
