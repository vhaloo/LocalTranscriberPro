"""Local MADLAD-400 translation and two-language conversation routing.

Only model preparation can contact the Hub. Inference accepts local files and
never sends speech or text to a network service.
"""
from __future__ import annotations

import gc
import hashlib
import json
import logging
import re
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


class TranslationResourceError(RuntimeError):
    """The translation model cannot yet fit alongside the active recognizer."""


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
    def __init__(self, cache: Path | None = None, *, isolated_cpu: bool = True):
        self.cache = Path(cache) if cache else Path(user_cache_dir("LocalTranscriberPro", "Vhaloo")) / "translation/madlad400-3b"
        self.model: Any = None
        self.tokenizer: Any = None
        self.device = "cpu"
        self.router: ConversationRouter | None = None
        self.last_index = None
        self.routing_generation = 0
        self._lock = threading.RLock()
        self.model_id = "madlad400-3b"
        self.context_enabled = False
        self.context = []
        self.glossary = ""
        self.optional_cache = None
        self._isolated_cpu = isolated_cpu
        self._cpu_worker = None
        self._virtual_memory = False

    def configure(self, model_id="madlad400-3b", cache=None, context=False, glossary=""):
        if model_id not in {"madlad400-3b", "madlad400-7b"}:
            raise ValueError("Unknown local translation model")
        with self._lock:
            if model_id != self.model_id or (model_id.endswith("7b") and cache and Path(cache) != self.cache):
                self.unload()
                self.cache = Path(cache) if cache and model_id.endswith("7b") else Path(user_cache_dir("LocalTranscriberPro", "Vhaloo")) / "translation" / model_id
            self.model_id = model_id
            self.context_enabled = bool(context)
            self.glossary = str(glossary)[:6000]

    def assets(self):
        if self.model_id == "madlad400-3b":
            return REPOSITORY, REVISION, FILES
        metadata = json.loads((Path(__file__).parent / "data/translation_7b.json").read_text("utf-8"))
        return metadata["repository"], metadata["revision"], {name: (item["size"], item["hash"]) for name, item in metadata["files"].items()}

    def _complete(self) -> bool:
        try:
            _, _, files = self.assets()
            return all((self.cache / name).is_file() and (self.cache / name).stat().st_size == size
                       for name, (size, _) in files.items())
        except OSError:
            return False

    def prepare(self, allow_download: bool, cancel_event: threading.Event | None = None) -> Path:
        check_cancelled(cancel_event)
        repository, revision, files = self.assets()
        if not self._complete():
            if not allow_download:
                raise RuntimeError("Le moteur de traduction n'est pas préparé. Connectez-vous une fois pour télécharger MADLAD-400, puis utilisez-le hors ligne.")
            from huggingface_hub import hf_hub_download

            self.cache.mkdir(parents=True, exist_ok=True)
            for name in files:
                check_cancelled(cancel_event)
                # local_dir produces ordinary files on Windows, avoiding the
                # cached-symlink traversal failure seen in the 3.0 delivery.
                hf_hub_download(repository, name, revision=revision, local_dir=self.cache)
        if not self._complete():
            raise RuntimeError("Incomplete local translation model")
        receipt_path = self.cache / "verified.json"
        try:
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            receipt = {}
        for name, (_, checksum) in files.items():
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

    def load(self, hardware, allow_download: bool = True, cancel_event=None,
             *, allow_cpu_virtual_memory: bool = False) -> None:
        with self._lock:
            if (self.model is not None and self._virtual_memory == allow_cpu_virtual_memory
                    and (self._cpu_worker is None or self._cpu_worker.alive)):
                return
            self.unload()
            self._virtual_memory = allow_cpu_virtual_memory
            if allow_cpu_virtual_memory and self._isolated_cpu:
                from src.cpu_worker import CPUWorkerClient
                worker = self._cpu_worker = CPUWorkerClient()
                try:
                    result = worker.call("load_translation", {
                        "model": self.model_id, "cache": str(self.cache),
                        "hardware": hardware.as_dict(), "allow_download": allow_download,
                    }, cancel_event=cancel_event)
                    if result != {"device": "cpu", "model": self.model_id}:
                        raise RuntimeError("The CPU translation worker returned a different model/device")
                    self.model, self.device = worker, "cpu"
                    return
                except BaseException:
                    worker.close()
                    self._cpu_worker = self.model = None
                    raise
            hardware.refresh_resources()
            required_ram = 14 if self.model_id.endswith("7b") else 6
            if not allow_cpu_virtual_memory and (hardware.effective_available_ram_gb < required_ram or hardware.ram_gb < required_ram * 2):
                raise TranslationResourceError(f"Traduction {self.model_id}: {required_ram * 2} Go de RAM totale et {required_ram} Go disponibles nécessaires.")
            self.cache.mkdir(parents=True, exist_ok=True)
            import shutil
            required_disk = 10 if self.model_id.endswith("7b") else 4
            if not self._complete() and shutil.disk_usage(self.cache).free < required_disk * 1_000_000_000:
                raise RuntimeError(f"Traduction {self.model_id}: {required_disk} Go libres nécessaires dans {self.cache}.")
            folder = self.prepare(allow_download, cancel_event)
            import ctranslate2
            import sentencepiece

            self.tokenizer = sentencepiece.SentencePieceProcessor(model_file=str(folder / ("spiece.model" if self.model_id.endswith("7b") else "sentencepiece.model")))
            # ASR remains resident: its memory cannot be reclaimed to admit MT.
            free_vram = hardware.gpu_vram_free_gb if hardware.gpu_vram_free_gb is not None else hardware.gpu_vram_gb
            self.device = "cuda" if not allow_cpu_virtual_memory and hardware.ctranslate_cuda and free_vram >= (10 if self.model_id.endswith("7b") else 4) else "cpu"
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
            logging.info("Loaded translation model=%s device=%s compute=int8", self.model_id, self.device)

    def reset_conversation(self, preferred: str, partner: str | None = None) -> None:
        self.routing_generation += 1
        self.router = ConversationRouter(preferred, partner if partner != preferred else None)
        self.context = []

    def translate(self, text: str, target: str, cancel_event=None) -> str:
        self.last_index = None
        if target not in LANGUAGE_BY_CODE:
            raise ValueError(f"Unsupported translation destination: {target}")
        if not text.strip():
            return ""
        with self._lock:
            if self.model is None:
                raise RuntimeError("Local translation engine is not loaded")
            if self._cpu_worker is not None:
                result = self._cpu_worker.call("translate", {
                    "text": text, "target": target, "glossary": self.glossary,
                }, cancel_event=cancel_event)
                self.last_index = result["index"]
                return result["text"]
            original = text
            substitutions = []
            for line in self.glossary.splitlines()[:40]:
                parts = [value.strip() for value in line.split("|")]
                if len(parts) != 3 or parts[1] != target or not parts[0] or not parts[2]:
                    continue
                marker = f"ZXQTERM{len(substitutions)}QXZ"
                if marker in text:
                    continue
                updated = re.sub(r"(?<!\w)" + re.escape(parts[0]) + r"(?!\w)", marker, text)
                if updated != text:
                    text = updated
                    substitutions.append((marker, parts[2]))
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
            output = " ".join(translated).strip()
            if substitutions and not all(marker in output for marker, _ in substitutions):
                glossary, self.glossary = self.glossary, ""
                try:
                    return self.translate(original, target, cancel_event)
                finally:
                    self.glossary = glossary
            for marker, replacement in substitutions:
                output = output.replace(marker, replacement)
            return output

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
            output = text if destination == source or destination is None else self.translate_contextual(text, destination, source, cancel_event)
            translation_index = self.last_index if destination and destination != source else None
            item = dict(segment, source_text=text, source_language=source or "und", text=output,
                        target_language=destination or "", translation_pending=destination is None,
                        source_words=segment.get("words", []), words=[], translation_model=self.model_id)
            item["translation_index"] = translation_index
            source_indices = [s["recognition_index"] for s in result.get("segments", []) if s.get("recognition_index") is not None]
            if conversation and source_indices:
                item["recognition_index"] = min(source_indices)
            if conversation:
                item["routing_generation"] = self.routing_generation
                item["conversation_pair"] = list(self.router.pair)
            if third:
                item.update(third_language=third, third_text=text if third == source else (
                    output if third == destination else self.translate(text, third, cancel_event)))
                item["third_translation_index"] = translation_index if third == destination else (
                    self.last_index if third != source else None)
            translated.append(item)
        return dict(result, source_text=original, segments=translated,
                    text=" ".join(item["text"] for item in translated), target_language=destination or "",
                    conversation_pair=list(self.router.pair) if conversation else [], translation_model=self.model_id)

    def translate_contextual(self, text, target, source, cancel_event=None):
        """Opt-in context; marker failure falls back to the original turn.

        T5 has no chat instructions. Separate turns with a stable marker and
        accept context only when it survives decoding exactly. Never display
        earlier turns again or infer that the result is more reliable.
        """
        if not self.context_enabled:
            return self.translate(text, target, cancel_event)
        previous = next((value for code, value in reversed(self.context) if code == source), None)
        if previous:
            marker = " [987654321] "
            output = self.translate(previous[-500:] + marker + text, target, cancel_event)
            pieces = output.split("[987654321]")
            output = pieces[-1].strip() if len(pieces) == 2 and pieces[-1].strip() else self.translate(text, target, cancel_event)
        else:
            output = self.translate(text, target, cancel_event)
        self.context = [*self.context[-3:], (source, text)]
        return output

    def complete_conversation(self, segments: list[dict[str, Any]], cancel_event=None) -> list[dict[str, Any]]:
        """Resolve earlier lines once both conversation languages are known."""
        if self.router is None or len(self.router.pair) != 2:
            return segments
        completed = []
        for segment in segments:
            if "source_text" not in segment or segment.get("routing_generation", self.routing_generation) != self.routing_generation:
                completed.append(segment)
                continue
            item = dict(segment, conversation_pair=list(self.router.pair))
            destination = self.router.destination(item.get("source_language"), None, "")
            if destination and (item.get("translation_pending") or item.get("target_language") != destination):
                if item.get("edited") or item.get("translation_edited"):
                    completed.append(item)
                    continue
                item.update(text=self.translate(item["source_text"], destination, cancel_event),
                            target_language=destination, translation_pending=False, translation_index=self.last_index)
            completed.append(item)
        return completed

    def unload(self) -> None:
        with self._lock:
            if self._cpu_worker is not None:
                self._cpu_worker.close()
                self._cpu_worker = None
            self.model = self.tokenizer = None
            gc.collect()

    def cancel_cpu_worker(self) -> None:
        # Deliberately no model lock: a native allocation may still be running.
        worker = self._cpu_worker
        if worker is not None:
            worker.close()
