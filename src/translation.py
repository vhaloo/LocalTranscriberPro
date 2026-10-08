"""Local MADLAD-400 translation and two-language conversation routing.

Only model preparation can contact the Hub. Inference accepts local files and
never sends speech or text to a network service.
"""
from __future__ import annotations

import gc
import hashlib
import json
import logging
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from platformdirs import user_cache_dir

from src.confidence import model_index
from src.jobs import check_cancelled
from src.translation_languages import LANGUAGE_BY_CODE, normalize_language
from src.utils import atomic_write_text

REPOSITORY = "santhosh/madlad400-3b-ct2"
REVISION = "c32ad0cf118807ea6258d14be137547155842723"
FILES = {
    "model.bin": (2950208251, "f3c87256a2c888100c179d7dcd7f41df17c767469546c59d32c7dde86c740a6b"),
    "sentencepiece.model": (4427844, "ef11ac9a22c7503492f56d48dce53be20e339b63605983e9f27d2cd0e0f3922c"),
    "config.json": (190, "a428c51cd35517554523b3c6b6974a5928bc35e82b130869a543566a34a83b93"),
    "shared_vocabulary.json": (5477099, "c327551ce3ca6efc7b437e11a267f79979893332dda8a1d146e2c950815193f8"),
}


@dataclass
class ConversationRouter:
    preferred: str
    partner: str | None = None
    observed: list[str] = field(default_factory=list)

    @property
    def pair(self) -> tuple[str, ...]:
        return (self.preferred, self.partner) if self.partner else tuple(self.observed[:2])

    def destination(self, source: str | None, probability: float | None, text: str) -> str | None:
        code = normalize_language(source)
        if not self.partner and code in LANGUAGE_BY_CODE and (probability or 0) >= 0.55 and len(text.strip()) >= 3:
            if code not in self.observed and len(self.observed) < 2:
                self.observed.append(code)
        pair = self.pair
        for index, member in enumerate(pair if len(pair) == 2 else ()):
            if code == member or (code and code == member.split("_")[0]):
                return pair[1 - index]
        return self.preferred if code != self.preferred.split("_")[0] else None


class TranslationEngine:
    def __init__(self, cache: Path | None = None):
        self.cache = cache or Path(user_cache_dir("LocalTranscriberPro", "Vhaloo")) / "translation/madlad400-3b"
        self.model: Any = None
        self.tokenizer: Any = None
        self.device = "cpu"
        self.router: ConversationRouter | None = None
        self.last_index = None
        self._lock = threading.RLock()

    def _complete(self) -> bool:
        try:
            return all((self.cache / name).is_file() and (self.cache / name).stat().st_size == size
                       for name, (size, _) in FILES.items())
        except OSError:
            return False

    def prepare(self, allow_download: bool, cancel_event: threading.Event | None = None) -> Path:
        check_cancelled(cancel_event)
        if not self._complete():
            if not allow_download:
                raise RuntimeError("Le moteur de traduction n'est pas préparé. Connectez-vous une fois pour télécharger MADLAD-400, puis utilisez-le hors ligne.")
            from huggingface_hub import hf_hub_download

            self.cache.mkdir(parents=True, exist_ok=True)
            for name in FILES:
                check_cancelled(cancel_event)
                # local_dir produces ordinary files on Windows, avoiding the
                # cached-symlink traversal failure seen in the 3.0 delivery.
                hf_hub_download(REPOSITORY, name, revision=REVISION, local_dir=self.cache)
        if not self._complete():
            raise RuntimeError("Incomplete local translation model")
        receipt_path = self.cache / "verified.json"
        try:
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            receipt = {}
        for name, (_, checksum) in FILES.items():
            check_cancelled(cancel_event)
            path = self.cache / name
            signature = [path.stat().st_size, path.stat().st_mtime_ns, checksum]
            if checksum and receipt.get(name) != signature:
                with path.open("rb") as handle:
                    actual = hashlib.file_digest(handle, "sha256").hexdigest()
                if actual != checksum:
                    raise RuntimeError(f"Translation model checksum mismatch: {name}")
            receipt[name] = signature
        atomic_write_text(receipt_path, json.dumps(receipt))
        return self.cache

    def load(self, hardware, allow_download: bool = True, cancel_event=None) -> None:
        with self._lock:
            if self.model is not None:
                return
            hardware.refresh_resources()
            if hardware.effective_available_ram_gb < 6 or hardware.ram_gb < 12:
                raise RuntimeError("La traduction universelle nécessite 12 Go de RAM et 6 Go actuellement disponibles.")
            if not self._complete() and hardware.disk_free_gb < 4:
                raise RuntimeError("La préparation de la traduction nécessite 4 Go d'espace libre.")
            folder = self.prepare(allow_download, cancel_event)
            import ctranslate2
            import sentencepiece

            self.tokenizer = sentencepiece.SentencePieceProcessor(model_file=str(folder / "sentencepiece.model"))
            # ASR remains resident: its memory cannot be reclaimed to admit MT.
            free_vram = hardware.gpu_vram_free_gb if hardware.gpu_vram_free_gb is not None else hardware.gpu_vram_gb
            self.device = "cuda" if hardware.ctranslate_cuda and free_vram >= 4 else "cpu"
            try:
                self.model = ctranslate2.Translator(str(folder), device=self.device,
                    compute_type="int8_float16" if self.device == "cuda" else "int8",
                    inter_threads=1, intra_threads=max(1, min(hardware.cpu_threads, 12)))
            except (RuntimeError, ValueError, OSError):
                if self.device != "cuda":
                    raise
                logging.exception("Translation GPU initialization failed; using local CPU")
                self.device = "cpu"
                self.model = ctranslate2.Translator(str(folder), device="cpu", compute_type="int8",
                    inter_threads=1, intra_threads=max(1, min(hardware.cpu_threads, 12)))
            logging.info("Loaded translation model=madlad400-3b device=%s compute=int8", self.device)

    def reset_conversation(self, preferred: str, partner: str | None = None) -> None:
        self.router = ConversationRouter(preferred, partner if partner != preferred else None)

    def translate(self, text: str, target: str, cancel_event=None) -> str:
        self.last_index = None
        if target not in LANGUAGE_BY_CODE:
            raise ValueError(f"Unsupported translation destination: {target}")
        if not text.strip():
            return ""
        with self._lock:
            if self.model is None:
                raise RuntimeError("Local translation engine is not loaded")
            tokens = self.tokenizer.encode(text, out_type=str)
            translated = []
            scores = []
            # Bounded segments limit memory and make cancellation effective
            # between decoder operations, including long imported sentences.
            for offset in range(0, len(tokens), 128):
                check_cancelled(cancel_event)
                portion = self.tokenizer.decode(tokens[offset:offset + 128])
                # Encode the language prefix together with the sentence. T5's
                # leading SentencePiece boundary and EOS are both significant.
                batch = [self.tokenizer.encode(f"<2{target}> {portion}", out_type=str) + ["</s>"]]
                results = self.model.translate_batch(batch, beam_size=4, max_decoding_length=512,
                                                     return_scores=True, length_penalty=1)
                score = model_index(getattr(results[0], "scores", [None])[0])
                if score is not None:
                    scores.append(score)
                output = self.tokenizer.decode(results[0].hypotheses[0]).strip()
                if not output:
                    raise RuntimeError("The local translation model returned an empty sentence")
                translated.append(output)
            check_cancelled(cancel_event)
            self.last_index = min(scores) if scores else None
            return " ".join(translated).strip()

    def translate_result(self, result: dict[str, Any], target: str, conversation: bool = False,
                         third: str | None = None, cancel_event=None) -> dict[str, Any]:
        source = normalize_language(result.get("language"))
        original = str(result.get("text", ""))
        probability = result.get("language_probability")
        if conversation and self.router is None:
            self.reset_conversation(target)
        destination = self.router.destination(source, probability, original) if conversation else target
        translated = []
        source_segments = result.get("segments", [])
        if conversation and source_segments:
            # One acoustic turn gets one translation with the full context;
            # sentence-level decoder splits should not fragment the dialogue.
            source_segments = [dict(source_segments[0], text=original,
                                    end=source_segments[-1].get("end", 0),
                                    words=[word for item in source_segments for word in item.get("words", [])])]
        for segment in source_segments:
            check_cancelled(cancel_event)
            text = str(segment.get("text", "")).strip()
            if not text:
                continue
            output = text if destination == source or destination is None else self.translate(text, destination, cancel_event)
            translation_index = self.last_index if destination and destination != source else None
            item = dict(segment, source_text=text, source_language=source or "und", text=output,
                        target_language=destination or "", translation_pending=destination is None,
                        source_words=segment.get("words", []), words=[], translation_model="madlad400-3b")
            item["translation_index"] = translation_index
            source_indices = [s["recognition_index"] for s in result.get("segments", []) if s.get("recognition_index") is not None]
            if conversation and source_indices:
                item["recognition_index"] = min(source_indices)
            if conversation:
                item["conversation_pair"] = list(self.router.pair)
            if third:
                item.update(third_language=third, third_text=text if third == source else (
                    output if third == destination else self.translate(text, third, cancel_event)))
                item["third_translation_index"] = translation_index if third == destination else (
                    self.last_index if third != source else None)
            translated.append(item)
        return dict(result, source_text=original, segments=translated,
                    text=" ".join(item["text"] for item in translated), target_language=destination or "",
                    conversation_pair=list(self.router.pair) if conversation else [], translation_model="madlad400-3b")

    def complete_conversation(self, segments: list[dict[str, Any]], cancel_event=None) -> list[dict[str, Any]]:
        """Resolve earlier lines once both conversation languages are known."""
        if self.router is None or len(self.router.pair) != 2:
            return segments
        completed = []
        for segment in segments:
            if "source_text" not in segment:
                completed.append(segment)
                continue
            item = dict(segment, conversation_pair=list(self.router.pair))
            destination = self.router.destination(item.get("source_language"), None, "")
            if destination and (item.get("translation_pending") or item.get("target_language") != destination):
                item.update(text=self.translate(item["source_text"], destination, cancel_event),
                            target_language=destination, translation_pending=False, translation_index=self.last_index)
            completed.append(item)
        return completed

    def unload(self) -> None:
        with self._lock:
            self.model = self.tokenizer = None
            gc.collect()
