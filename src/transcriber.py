"""Adaptive local transcription engine.

The preferred backend is faster-whisper/CTranslate2 on NVIDIA GPUs and CPUs.
Apple Silicon uses MLX when installed. OpenAI Whisper through PyTorch is kept as
a compatibility fallback, so GPU acceleration does not disappear when a
CTranslate2 runtime is incomplete.
"""

from __future__ import annotations

import logging
import os
import re
import shutil
import time
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
from platformdirs import user_cache_dir

from src.hardware import HardwareProfile, detect_hardware
from src.models import AUTO_MODEL_ID, MODEL_CATALOG, get_model, mlx_repository

ProgressCallback = Callable[[float], None]


@dataclass
class TranscriptionOptions:
    task: str = "transcribe"
    language: str | None = None
    beam_size: int = 5
    vad_filter: bool = True
    word_timestamps: bool = True
    initial_prompt: str | None = None


@dataclass
class EngineStatus:
    model_id: str
    requested_device: str
    device: str
    backend: str
    compute_type: str


class TranscriberEngine:
    def __init__(self, hardware: HardwareProfile | None = None):
        self.hardware = hardware or detect_hardware()
        self.model: Any = None
        self.model_name: str | None = None
        self.device = "cpu"
        self.backend = "none"
        self.compute_type = "int8"
        self.model_cache = Path(user_cache_dir("LocalTranscriberPro", "Vhaloo")) / "models"
        self.model_cache.mkdir(parents=True, exist_ok=True)

        # Compatibility attributes used by the v1 interface and external users.
        self.has_nvidia_gpu = self.hardware.nvidia_detected
        self.torch_cuda_available = self.hardware.torch_cuda
        self.cuda_missing = self.has_nvidia_gpu and not (
            self.hardware.ctranslate_cuda or self.hardware.torch_cuda
        )
        self.mps_available = self.hardware.mlx_available or self.hardware.torch_mps

    def check_hardware(self) -> HardwareProfile:
        self.hardware = detect_hardware()
        return self.hardware

    def recommend_model(self) -> str:
        return self.hardware.recommended_model()

    @staticmethod
    def _normalize_device(device_mode: str) -> str:
        value = (device_mode or "auto").lower()
        if "cuda" in value or "nvidia" in value:
            return "cuda"
        if "mps" in value or "metal" in value or "apple" in value:
            return "metal"
        if "cpu" in value or "processeur" in value:
            return "cpu"
        return "auto"

    def _resolve_device(self, requested: str) -> str:
        requested = self._normalize_device(requested)
        if requested == "auto":
            return self.hardware.best_device
        if requested == "cuda" and not (self.hardware.ctranslate_cuda or self.hardware.torch_cuda):
            raise RuntimeError(
                "NVIDIA GPU was requested, but no compatible CUDA AI runtime is available. "
                "Use Automatic or CPU, or repair the NVIDIA runtime."
            )
        if requested == "metal" and not (self.hardware.mlx_available or self.hardware.torch_mps):
            raise RuntimeError("Apple GPU was requested, but MLX/MPS is not available. Use Automatic or CPU.")
        return requested

    def load_model(self, model_id: str, device_mode: str = "auto") -> EngineStatus:
        requested_model = model_id if model_id != AUTO_MODEL_ID else self.recommend_model()
        get_model(requested_model)  # Normalize unknown ids through the catalogue.
        requested_device = self._normalize_device(device_mode)
        target_device = self._resolve_device(requested_device)

        if target_device == "metal" and self.hardware.mlx_available:
            # MLX loads lazily inside transcribe(); retaining a marker keeps the
            # same lifecycle as the other backends without duplicating memory.
            backend, compute = "mlx", "float16"
            if self.model_name != requested_model or self.backend != backend or self.device != target_device:
                self.unload_model()
                self.model = True
        else:
            backend = "faster-whisper"
            fw_device = "cuda" if target_device == "cuda" else "cpu"
            compute = self.hardware.compute_type(fw_device)
            if (
                self.model_name != requested_model
                or self.backend != backend
                or self.device != target_device
                or self.compute_type != compute
            ):
                self.unload_model()
                try:
                    from faster_whisper import WhisperModel

                    self.model = WhisperModel(
                        requested_model,
                        device=fw_device,
                        compute_type=compute,
                        cpu_threads=max(1, min(self.hardware.cpu_threads, 12)),
                        download_root=str(self.model_cache),
                    )
                except Exception as faster_error:
                    logging.exception("faster-whisper model load failed")
                    if target_device in {"cuda", "metal"}:
                        try:
                            self._load_openai_fallback(requested_model, target_device)
                            backend = "openai-whisper"
                            compute = "float16"
                        except Exception as fallback_error:
                            raise RuntimeError(
                                f"The accelerated engine could not start ({faster_error}). "
                                f"The compatibility engine also failed ({fallback_error})."
                            ) from fallback_error
                    else:
                        raise RuntimeError(
                            f"The local transcription engine could not load {requested_model}: {faster_error}"
                        ) from faster_error

        self.model_name = requested_model
        self.device = target_device
        self.backend = backend
        self.compute_type = compute
        logging.info(
            "Loaded model=%s backend=%s device=%s compute=%s",
            requested_model,
            backend,
            target_device,
            compute,
        )
        return EngineStatus(
            model_id=requested_model,
            requested_device=requested_device,
            device=target_device,
            backend=backend,
            compute_type=compute,
        )

    def _load_openai_fallback(self, model_id: str, device: str) -> None:
        import whisper

        torch_device = "mps" if device == "metal" else device
        self.model = whisper.load_model(
            model_id,
            device=torch_device,
            download_root=str(self.model_cache / "openai"),
        )

    def unload_model(self) -> None:
        self.model = None
        self.model_name = None
        try:
            import torch

            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            if hasattr(torch, "mps") and hasattr(torch.mps, "empty_cache"):
                torch.mps.empty_cache()
        except (ImportError, RuntimeError):
            pass

    def transcribe_file(
        self,
        filepath: str | os.PathLike[str],
        options: TranscriptionOptions | None = None,
        progress_callback: ProgressCallback | None = None,
    ) -> dict[str, Any]:
        return self._transcribe(str(filepath), options or TranscriptionOptions(), progress_callback)

    def transcribe_audio(
        self,
        audio_data: np.ndarray,
        options: TranscriptionOptions | None = None,
        progress_callback: ProgressCallback | None = None,
    ) -> dict[str, Any]:
        data = np.asarray(audio_data, dtype=np.float32).reshape(-1)
        return self._transcribe(data, options or TranscriptionOptions(), progress_callback)

    def _transcribe(
        self,
        source: str | np.ndarray,
        options: TranscriptionOptions,
        progress_callback: ProgressCallback | None,
    ) -> dict[str, Any]:
        if self.model is None or not self.model_name:
            raise RuntimeError("Model not loaded")

        duration = self.audio_duration(source)
        started = time.monotonic()
        if self.backend == "faster-whisper":
            result = self._transcribe_faster(source, options, duration, progress_callback)
        elif self.backend == "mlx":
            result = self._transcribe_mlx(source, options, progress_callback)
        elif self.backend == "openai-whisper":
            result = self._transcribe_openai(source, options, progress_callback)
        else:
            raise RuntimeError(f"Unknown transcription backend: {self.backend}")
        result["duration"] = duration
        result["processing_seconds"] = time.monotonic() - started
        result["model"] = self.model_name
        result["device"] = self.device
        result["backend"] = self.backend
        if progress_callback:
            progress_callback(1.0)
        return result

    def _transcribe_faster(
        self,
        source: str | np.ndarray,
        options: TranscriptionOptions,
        duration: float,
        progress_callback: ProgressCallback | None,
    ) -> dict[str, Any]:
        language = None if options.language in {None, "", "auto"} else options.language
        segments_iter, info = self.model.transcribe(
            source,
            task=options.task,
            language=language,
            beam_size=max(1, int(options.beam_size)),
            vad_filter=bool(options.vad_filter),
            vad_parameters={"min_silence_duration_ms": 500},
            word_timestamps=bool(options.word_timestamps),
            initial_prompt=options.initial_prompt or None,
            condition_on_previous_text=True,
        )
        segments: list[dict[str, Any]] = []
        for item in segments_iter:
            words = []
            for word in item.words or []:
                words.append(
                    {
                        "start": float(word.start),
                        "end": float(word.end),
                        "word": word.word,
                        "probability": float(word.probability),
                    }
                )
            segment = {
                "start": float(item.start),
                "end": float(item.end),
                "text": item.text.strip(),
                "words": words,
            }
            segments.append(segment)
            if progress_callback and duration > 0:
                progress_callback(min(0.99, segment["end"] / duration))
        return {
            "text": " ".join(item["text"] for item in segments).strip(),
            "segments": segments,
            "language": getattr(info, "language", language),
            "language_probability": getattr(info, "language_probability", None),
        }

    def _transcribe_mlx(
        self,
        source: str | np.ndarray,
        options: TranscriptionOptions,
        progress_callback: ProgressCallback | None,
    ) -> dict[str, Any]:
        import mlx_whisper

        language = None if options.language in {None, "", "auto"} else options.language
        result = mlx_whisper.transcribe(
            source,
            path_or_hf_repo=mlx_repository(self.model_name or "large-v3"),
            task=options.task,
            language=language,
            word_timestamps=bool(options.word_timestamps),
            initial_prompt=options.initial_prompt or None,
            condition_on_previous_text=True,
            fp16=True,
            verbose=False,
        )
        if progress_callback:
            progress_callback(0.99)
        return self._normalize_result(result)

    def _transcribe_openai(
        self,
        source: str | np.ndarray,
        options: TranscriptionOptions,
        progress_callback: ProgressCallback | None,
    ) -> dict[str, Any]:
        language = None if options.language in {None, "", "auto"} else options.language
        result = self.model.transcribe(
            source,
            task=options.task,
            language=language,
            beam_size=max(1, int(options.beam_size)),
            word_timestamps=bool(options.word_timestamps),
            initial_prompt=options.initial_prompt or None,
            fp16=self.device in {"cuda", "metal"},
            verbose=False,
        )
        if progress_callback:
            progress_callback(0.99)
        return self._normalize_result(result)

    @staticmethod
    def _normalize_result(result: dict[str, Any]) -> dict[str, Any]:
        normalized: list[dict[str, Any]] = []
        for item in result.get("segments", []):
            normalized.append(
                {
                    "start": float(item.get("start", 0.0)),
                    "end": float(item.get("end", 0.0)),
                    "text": str(item.get("text", "")).strip(),
                    "words": item.get("words", []),
                }
            )
        return {
            "text": str(result.get("text", "")).strip(),
            "segments": normalized,
            "language": result.get("language"),
        }

    @staticmethod
    def audio_duration(source: str | np.ndarray) -> float:
        if isinstance(source, np.ndarray):
            return float(source.size) / 16000.0
        try:
            import av

            with av.open(source) as container:
                stream = next((item for item in container.streams if item.type == "audio"), None)
                if stream and stream.duration is not None and stream.time_base is not None:
                    return float(stream.duration * stream.time_base)
                if container.duration is not None:
                    return float(container.duration) / 1_000_000.0
        except (OSError, StopIteration, ValueError):
            pass
        return 0.0

    @staticmethod
    def cleanup_text(text: str) -> str:
        text = re.sub(r"\s+", " ", text).strip()
        if not text:
            return ""
        normalized = re.sub(r"[^\w\s]", "", text.lower()).strip()
        known_silence_hallucinations = {
            "thank you",
            "thanks for watching",
            "subscribe",
            "sous titres réalisés para la communauté damaraorg",
        }
        if normalized in known_silence_hallucinations:
            return ""
        words = normalized.split()
        if len(words) >= 5 and len(set(words)) <= 2:
            return ""
        # Collapse an exact phrase repeated three or more times.
        repeated = re.fullmatch(r"(.{3,80}?)(?:\s+\1){2,}", text, flags=re.IGNORECASE)
        return repeated.group(1).strip() if repeated else text

    def cache_roots(self) -> list[Path]:
        roots = [
            self.model_cache,
            Path.home() / ".cache" / "whisper",
            Path.home() / ".cache" / "huggingface" / "hub",
            Path.home() / "Library" / "Caches" / "huggingface" / "hub",
        ]
        unique: list[Path] = []
        for root in roots:
            resolved = root.expanduser()
            if resolved not in unique:
                unique.append(resolved)
        return unique

    @staticmethod
    def _folder_size(path: Path) -> int:
        if path.is_file():
            try:
                return path.stat().st_size
            except OSError:
                return 0
        size = 0
        for root, _, files in os.walk(path):
            for name in files:
                try:
                    size += (Path(root) / name).stat().st_size
                except OSError:
                    pass
        return size

    def get_downloaded_models(self) -> list[dict[str, Any]]:
        found: list[dict[str, Any]] = []
        seen: set[Path] = set()
        model_tokens = {spec.model_id.replace("-", "--") for spec in MODEL_CATALOG}
        for root in self.cache_roots():
            if not root.exists():
                continue
            candidates: Iterable[Path]
            if root.name == "hub":
                candidates = root.glob("models--*whisper*")
            else:
                candidates = root.iterdir()
            for path in candidates:
                if path in seen:
                    continue
                lower = path.name.lower()
                if "whisper" not in lower and not any(token in lower for token in model_tokens):
                    continue
                seen.add(path)
                size = self._folder_size(path)
                found.append(
                    {
                        "name": path.name,
                        "size": f"{size / 1024**3:.2f} GB" if size >= 1024**3 else f"{size / 1024**2:.1f} MB",
                        "bytes": size,
                        "path": str(path),
                    }
                )
        return sorted(found, key=lambda item: item["bytes"], reverse=True)

    def delete_model_file(self, path: str | os.PathLike[str]) -> bool:
        candidate = Path(path).expanduser().resolve()
        allowed = False
        for root in self.cache_roots():
            try:
                candidate.relative_to(root.resolve())
                allowed = True
                break
            except (OSError, ValueError):
                continue
        if not allowed or not candidate.exists():
            return False
        try:
            if candidate.is_dir():
                shutil.rmtree(candidate)
            else:
                candidate.unlink()
            return True
        except OSError:
            logging.exception("Could not delete model cache item: %s", candidate)
            return False


# Compatibility values for older integrations. The v2 UI uses src.models.
MODEL_SIZES = {spec.model_id: spec.model_id for spec in MODEL_CATALOG}
REVERSE_MODEL_MAP = dict(MODEL_SIZES)
