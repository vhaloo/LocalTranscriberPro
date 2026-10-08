"""Optional CPU speech synthesis with pinned local Piper/Sherpa voices."""
from __future__ import annotations

import json
import sys
import threading
from pathlib import Path

from platformdirs import user_cache_dir

from src.jobs import check_cancelled
from src.local_assets import prepare_assets
from src.translation_languages import normalize_language

CATALOG = json.loads((Path(__file__).parent / "data/voices.json").read_text(encoding="utf-8"))
CATALOG["voices"].update(json.loads((Path(__file__).parent / "data/mms_voices.json").read_text(encoding="utf-8")))


class LocalSpeechOutput:
    def __init__(self, cache=None):
        self.cache = Path(cache) if cache else Path(user_cache_dir("LocalTranscriberPro", "Vhaloo")) / "voices"
        self.model = None
        self.language = None
        self.lock = threading.RLock()
        self.bundled = Path(getattr(sys, "_MEIPASS", Path(__file__).parents[1])) / "default-voices"

    @staticmethod
    def supports(language):
        return normalize_language(language).split("_")[0] in CATALOG["voices"] if language else False

    def prepare(self, language, allow_download=True, cancel_event=None):
        language = normalize_language(language).split("_")[0]
        if language not in CATALOG["voices"]:
            raise ValueError("No local voice for " + language)
        voice = CATALOG["voices"][language]
        if voice.get("backend") == "mms":
            folder = prepare_assets(self.cache / ("mms-" + language), voice["repository"], voice["revision"],
                                    voice["files"], allow_download, cancel_event)
            return voice, folder, None
        common = CATALOG["common"]
        data_folder = self._folder("phonemizer")
        voice_folder = self._folder(language)
        data = prepare_assets(data_folder, common["repository"], common["revision"],
                              common["files"], allow_download, cancel_event, self.cache / "receipts/phonemizer")
        folder = prepare_assets(voice_folder, voice["repository"], voice["revision"],
                                voice["files"], allow_download, cancel_event, self.cache / "receipts" / language)
        return voice, folder, data

    def _folder(self, language):
        bundled = self.bundled / language
        return bundled if bundled.is_dir() else self.cache / language

    def ready(self, language):
        if not self.supports(language):
            return False
        language = normalize_language(language).split("_")[0]
        voice = CATALOG["voices"][language]
        try:
            if voice.get("backend") == "mms":
                return all((self.cache / ("mms-" + language) / name).is_file()
                           and (self.cache / ("mms-" + language) / name).stat().st_size == spec["size"]
                           for name, spec in voice["files"].items())
            return all((folder / name).is_file() and (folder / name).stat().st_size == spec["size"]
                       for folder, files in ((self._folder(language), CATALOG["voices"][language]["files"]),
                                             (self._folder("phonemizer"), CATALOG["common"]["files"]))
                       for name, spec in files.items())
        except OSError:
            return False

    def synthesize(self, text, language, slow=False, allow_download=True, cancel_event=None):
        with self.lock:
            voice, folder, data = self.prepare(language, allow_download, cancel_event)
            if voice.get("backend") == "mms":
                import torch
                from transformers import VitsModel, VitsTokenizer

                if self.language != language or self.model is None:
                    self.model = VitsModel.from_pretrained(str(folder), local_files_only=True).eval()
                    self.tokenizer = VitsTokenizer.from_pretrained(str(folder), local_files_only=True)
                    self.language = language
                self.model.speaking_rate = 0.8 if slow else 1.0
                portions = []
                # Bound each inference, preserving every selected character up
                # to the same per-line reading limit as Piper.
                for offset in range(0, min(len(text), 2500), 180):
                    check_cancelled(cancel_event)
                    tokens = self.tokenizer(text[offset:offset + 180], return_tensors="pt")
                    with torch.inference_mode():
                        portions.append(self.model(**tokens).waveform.squeeze(0).numpy())
                import numpy as np
                check_cancelled(cancel_event)
                return np.concatenate(portions), self.model.config.sampling_rate
            if self.language != language or self.model is None:
                import sherpa_onnx

                config = sherpa_onnx.OfflineTtsConfig(model=sherpa_onnx.OfflineTtsModelConfig(
                    vits=sherpa_onnx.OfflineTtsVitsModelConfig(model=str(folder / voice["model"]),
                         tokens=str(folder / "tokens.txt"), data_dir=str(data / "espeak-ng-data")),
                    provider="cpu", num_threads=2), max_num_sentences=2)
                if not config.validate():
                    raise RuntimeError("Invalid local speech voice")
                self.model = sherpa_onnx.OfflineTts(config)
                self.language = language
            check_cancelled(cancel_event)
            # Bound the optional reading operation, not the saved transcript.
            audio = self.model.generate(text[:2500], sid=0, speed=0.8 if slow else 1.0,
                                       callback=lambda *_: 0 if cancel_event and cancel_event.is_set() else 1)
            check_cancelled(cancel_event)
            return audio.samples, audio.sample_rate
