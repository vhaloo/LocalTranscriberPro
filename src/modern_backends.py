"""Offline Qwen3-ASR and Parakeet adapters, using packaged model code only."""

from __future__ import annotations

import re
from collections.abc import Callable
from pathlib import Path
from typing import Any

import numpy as np

from src.jobs import check_cancelled
from src.media import SAMPLE_RATE, iter_audio_chunks
from src.model_cache import aligner_path, modern_model_path
from src.models import ModelSpec

QWEN_LANGUAGES = dict(zip(
    "zh en yue ar de fr es pt id it ko ru th vi ja tr hi ms nl sv da fi pl cs fil fa el hu mk ro".split(),
    "Chinese English Cantonese Arabic German French Spanish Portuguese Indonesian Italian Korean Russian Thai Vietnamese Japanese Turkish Hindi Malay Dutch Swedish Danish Finnish Polish Czech Filipino Persian Greek Hungarian Macedonian Romanian".split(),
    strict=True,
))
ALIGNER_LANGUAGES = {"zh", "en", "yue", "fr", "de", "it", "ja", "ko", "pt", "ru", "es"}


def word_segments(words: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Readable sentences with true word timing, suitable for subtitle exports."""
    segments: list[dict[str, Any]] = []
    pending: list[dict[str, Any]] = []
    for word in words:
        pending.append(word)
        punctuation = str(word["word"]).rstrip().endswith((".", "!", "?", "。", "！", "？"))
        if punctuation or len(pending) >= 16 or float(word["end"]) - float(pending[0]["start"]) >= 7:
            segments.append(_sentence(pending))
            pending = []
    if pending:
        segments.append(_sentence(pending))
    return segments


def _sentence(words: list[dict[str, Any]]) -> dict[str, Any]:
    text = " ".join(str(word["word"]).strip() for word in words)
    text = re.sub(r"\s+([,.!?;:])", r"\1", text)
    return {"start": words[0]["start"], "end": words[-1]["end"], "text": text, "words": list(words)}


class QwenBackend:
    def __init__(self, spec: ModelSpec, device: str, cache: Path):
        import torch
        from qwen_asr import Qwen3ASRModel, Qwen3ForcedAligner

        self.device = "mps" if device == "metal" else device
        dtype = torch.float16 if device != "cpu" else torch.float32
        self.model = Qwen3ASRModel.from_pretrained(
            str(modern_model_path(cache, spec)), dtype=dtype, device_map=self.device,
            attn_implementation="sdpa", max_inference_batch_size=1, max_new_tokens=512,
            local_files_only=True,
        )
        self.aligner = Qwen3ForcedAligner.from_pretrained(
            str(aligner_path(cache)), dtype=dtype, device_map=self.device,
            attn_implementation="sdpa", local_files_only=True,
        )

    def transcribe_chunk(self, audio: np.ndarray, options: Any) -> tuple[str | None, list[dict[str, Any]], str]:
        language = QWEN_LANGUAGES.get(options.language)
        result = self.model.transcribe(audio=(audio, SAMPLE_RATE), language=language,
                                       context=options.initial_prompt or "")[0]
        code = next((key for key, name in QWEN_LANGUAGES.items() if name.lower() == result.language.lower()), None)
        text = result.text.strip()
        if not text:
            return code, [], "word"
        if options.word_timestamps and code in ALIGNER_LANGUAGES:
            alignment = self.aligner.align(audio=(audio, SAMPLE_RATE), text=text, language=result.language)[0]
            words = [{"start": max(0.0, float(item.start_time)),
                      "end": min(len(audio) / SAMPLE_RATE, float(item.end_time)),
                      "word": item.text} for item in alignment]
            if words:
                # Alignment normalizes punctuation. Put each original text
                # slice back onto its aligned token so recognition stays exact.
                positions = []
                cursor = 0
                for word in words:
                    position = text.casefold().find(word["word"].casefold(), cursor)
                    if position < 0:
                        break
                    positions.append(position)
                    cursor = position + len(word["word"])
                if len(positions) == len(words):
                    for index, word in enumerate(words):
                        end = positions[index + 1] if index + 1 < len(words) else len(text)
                        word["word"] = text[positions[index]:end].strip()
                    return code, word_segments(words), "word"
                return code, [{"start": words[0]["start"], "end": words[-1]["end"],
                               "text": text, "words": words}], "segment"
        return code, [{"start": 0.0, "end": len(audio) / SAMPLE_RATE, "text": text, "words": []}], "chunk"


class ParakeetBackend:
    def __init__(self, spec: ModelSpec, cache: Path, threads: int):
        import sherpa_onnx

        path = modern_model_path(cache, spec)
        self.recognizer = sherpa_onnx.OfflineRecognizer.from_transducer(
            encoder=str(path / "encoder.int8.onnx"), decoder=str(path / "decoder.int8.onnx"),
            joiner=str(path / "joiner.int8.onnx"), tokens=str(path / "tokens.txt"),
            num_threads=max(1, min(threads, 8)), sample_rate=SAMPLE_RATE, feature_dim=80,
            model_type="nemo_transducer", decoding_method="greedy_search", provider="cpu",
        )

    def transcribe_chunk(self, audio: np.ndarray, options: Any) -> tuple[str | None, list[dict[str, Any]], str]:
        stream = self.recognizer.create_stream()
        stream.accept_waveform(SAMPLE_RATE, audio)
        self.recognizer.decode_stream(stream)
        result = stream.result
        text = result.text.strip()
        if not text:
            return options.language, [], "token"
        tokens = list(result.tokens)
        timestamps = list(result.timestamps)
        duration = len(audio) / SAMPLE_RATE
        words: list[dict[str, Any]] = []
        for index, (token, start) in enumerate(zip(tokens, timestamps, strict=True)):
            end = timestamps[index + 1] if index + 1 < len(timestamps) else min(duration, start + 0.4)
            piece = str(token).replace("▁", " ")
            if piece.startswith(" ") or not words:
                words.append({"start": float(start), "end": float(end), "word": piece.strip()})
            else:
                words[-1]["word"] += piece
                words[-1]["end"] = float(end)
        segments = word_segments(words) if words else [{"start": 0., "end": duration, "text": text, "words": []}]
        return options.language, segments, "token"


def transcribe_modern(backend: Any, source: str | np.ndarray, options: Any, duration: float,
                      progress: Callable[[float], None] | None) -> dict[str, Any]:
    segments: list[dict[str, Any]] = []
    language = options.language
    precision = "word"
    for offset, audio in iter_audio_chunks(source):
        check_cancelled(options.cancel_event)
        if not np.isfinite(audio).all():
            raise ValueError("The audio contains invalid samples")
        speech = True
        if options.vad_filter:
            from faster_whisper.vad import VadOptions, get_speech_timestamps

            speech = bool(get_speech_timestamps(audio, VadOptions(min_silence_duration_ms=500)))
        if speech:
            detected, items, precision = backend.transcribe_chunk(audio, options)
            language = detected or language
            for item in items:
                item = dict(item, start=item["start"] + offset, end=item["end"] + offset)
                item["words"] = [dict(word, start=word["start"] + offset, end=word["end"] + offset)
                                 for word in item.get("words", [])]
                segments.append(item)
        check_cancelled(options.cancel_event)
        if progress and duration > 0:
            progress(min(0.99, (offset + len(audio) / SAMPLE_RATE) / duration))
    return {"text": " ".join(item["text"] for item in segments).strip(), "segments": segments,
            "language": language, "timestamp_precision": precision}
