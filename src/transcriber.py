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
LoadStatusCallback = Callable[[str, str, str], None]


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
    requested_model_id: str = ""
    fallback_reason: str = ""


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
        return self.hardware.recommended_model(cached_model_ids=self.cached_model_ids())

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

    def load_model(
        self,
        model_id: str,
        device_mode: str = "auto",
        status_callback: LoadStatusCallback | None = None,
    ) -> EngineStatus:
        def report(stage: str, selected_model: str, device: str) -> None:
            if status_callback:
                status_callback(stage, selected_model, device)

        report("resource_check", model_id, device_mode)
        self.hardware.refresh_resources()
        cached = self.cached_model_ids()
        requested_model = self.hardware.resolve_model(model_id, device_mode, cached)
        get_model(requested_model)
        requested_device = self._normalize_device(device_mode)
        compatibility = self.hardware.model_compatibility(
            requested_model, device_mode, requested_model in cached
        )
        if not compatibility.supported:
            raise RuntimeError(
                f"No speech model can be started safely ({compatibility.reason_code}: "
                f"{compatibility.detected:.1f}/{compatibility.required:.1f} GB)."
            )
        target_device = compatibility.device
        fallback_reason = "" if model_id in {AUTO_MODEL_ID, requested_model} else "hardware_guard"
        report("model_cached" if requested_model in cached else "model_download", requested_model, target_device)

        if target_device == "metal" and self.hardware.mlx_available:
            # MLX loads lazily inside transcribe(); retaining a marker keeps the
            # same lifecycle as the other backends without duplicating memory.
            backend, compute = "mlx", "float16"
            if self.model_name != requested_model or self.backend != backend or self.device != target_device:
                self.unload_model()
                self.model = True
        else:
            backend = "faster-whisper"
            compute = self.hardware.compute_type(target_device)
            if (
                self.model_name != requested_model
                or self.backend != backend
                or self.device != target_device
                or self.compute_type != compute
            ):
                self.unload_model()
                attempts: list[tuple[str, str]] = [(requested_model, target_device)]
                if target_device in {"cuda", "metal"}:
                    cpu_check = self.hardware.model_compatibility(
                        requested_model, "cpu", requested_model in cached
                    )
                    if cpu_check.supported:
                        attempts.append((requested_model, "cpu"))
                requested_rank = get_model(requested_model).quality_rank
                for spec in sorted(MODEL_CATALOG, key=lambda item: item.quality_rank, reverse=True):
                    if not spec.multilingual or spec.quality_rank >= requested_rank:
                        continue
                    check = self.hardware.model_compatibility(
                        spec.model_id, device_mode, spec.model_id in cached
                    )
                    candidate = (spec.model_id, check.device)
                    if check.supported and candidate not in attempts:
                        attempts.append(candidate)
                    if len(attempts) >= 3:
                        break

                errors: list[Exception] = []
                loaded = False
                for attempt_model, attempt_device in attempts:
                    attempt_compute = self.hardware.compute_type(attempt_device)
                    report("engine_start", attempt_model, attempt_device)
                    try:
                        from faster_whisper import WhisperModel

                        self.model = WhisperModel(
                            attempt_model,
                            device="cuda" if attempt_device == "cuda" else "cpu",
                            compute_type=attempt_compute,
                            cpu_threads=max(1, min(self.hardware.cpu_threads, 12)),
                            download_root=str(self.model_cache),
                        )
                        if (attempt_model, attempt_device) != attempts[0]:
                            fallback_reason = "engine_retry"
                            report("safe_fallback", attempt_model, attempt_device)
                        requested_model = attempt_model
                        target_device = attempt_device
                        compute = attempt_compute
                        loaded = True
                        break
                    except Exception as faster_error:
                        errors.append(faster_error)
                        logging.exception(
                            "faster-whisper load failed for model=%s device=%s",
                            attempt_model,
                            attempt_device,
                        )
                if not loaded and target_device in {"cuda", "metal"}:
                    spec = get_model(requested_model)
                    enough_headroom = (
                        target_device == "metal"
                        or self.hardware.effective_free_vram_gb >= spec.vram_gb * 1.5
                    )
                    if enough_headroom:
                        try:
                            self._load_openai_fallback(requested_model, target_device)
                            backend = "openai-whisper"
                            compute = "float16"
                            fallback_reason = "compatibility_engine"
                            loaded = True
                        except Exception as fallback_error:
                            errors.append(fallback_error)
                if not loaded:
                    detail = errors[-1] if errors else "unknown engine error"
                    raise RuntimeError(
                        f"The safe local engine could not load a compatible model: {detail}"
                    ) from (errors[-1] if errors else None)

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
            requested_model_id=model_id,
            fallback_reason=fallback_reason,
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

    def cached_model_ids(self) -> set[str]:
        """Identify cached checkpoints without recursively measuring their size."""
        names: list[str] = []
        for root in self.cache_roots():
            if not root.exists():
                continue
            try:
                names.extend(path.name.lower().replace("--", "-") for path in root.iterdir())
            except OSError:
                continue
        found: set[str] = set()
        for spec in sorted(MODEL_CATALOG, key=lambda item: len(item.model_id), reverse=True):
            token = spec.model_id.lower()
            if any(name.endswith(token) or name == f"{token}.pt" for name in names):
                found.add(spec.model_id)
        return found

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
