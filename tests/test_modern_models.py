import threading
from types import SimpleNamespace

import numpy as np
import pytest

from src.hardware import HardwareProfile
from src.jobs import JobCancelled
from src.models import AUTO_FAST_MODEL_ID, AUTO_MODEL_ID, get_model
from src.modern_backends import transcribe_modern, word_segments
from src.transcriber import TranscriptionOptions


def gpu(**changes):
    values = dict(os_name="Windows", os_version="11", architecture="AMD64", cpu_name="CPU", cpu_threads=16,
                  ram_gb=64, available_ram_gb=32, gpu_vram_gb=12, gpu_vram_free_gb=10,
                  nvidia_detected=True, ctranslate_cuda=True, torch_cuda=True, qwen_available=True,
                  torch_cpu_available=True, parakeet_available=True)
    values.update(changes)
    return HardwareProfile(**values)


def test_twelve_gb_gpu_keeps_large_qwen_with_context_overhead():
    assert gpu(gpu_vram_free_gb=7.9).recommended_model() == "qwen3-asr-1.7b"
    assert gpu(gpu_vram_free_gb=7.0).recommended_model() == "qwen3-asr-0.6b"


def test_powerful_gpu_selects_recent_multilingual_model():
    assert gpu().resolve_model(AUTO_MODEL_ID) == "qwen3-asr-1.7b"


def test_busy_gpu_selects_smaller_recent_model():
    assert gpu(gpu_vram_free_gb=6).resolve_model(AUTO_MODEL_ID) == "qwen3-asr-0.6b"


def test_zero_free_gpu_memory_is_not_treated_as_full_capacity():
    assert not gpu(gpu_vram_free_gb=0).model_compatibility("large-v3", "cuda").supported


def test_zero_free_ram_is_not_treated_as_total_memory():
    assert not gpu(available_ram_gb=0).model_compatibility("tiny", "cpu").supported


def test_ctranslate_cuda_does_not_admit_a_torch_only_model():
    assert not gpu(torch_cuda=False).model_compatibility("qwen3-asr-1.7b", "cuda").supported


@pytest.mark.parametrize("requested", [AUTO_MODEL_ID, AUTO_FAST_MODEL_ID, "qwen3-asr-1.7b", "large-v3-turbo", "tiny.en"])
def test_translation_keeps_a_real_translation_model(requested):
    model = gpu().resolve_model(requested, task="translate", language="fr")
    assert get_model(model).translation
    assert get_model(model).family == "whisper"


def test_english_only_checkpoint_is_excluded_from_auto_detect_translation():
    model = gpu().resolve_model("tiny.en", task="translate", language=None)
    assert get_model(model).multilingual and get_model(model).translation


def test_language_outside_qwen_coverage_uses_whisper():
    assert gpu().resolve_model(AUTO_MODEL_ID, language="uk") == "large-v3"


def test_cpu_auto_does_not_choose_slow_large_autoregressive_engine():
    assert gpu().resolve_model(AUTO_MODEL_ID, "cpu") == "large-v3"


def test_fast_mode_has_a_native_windows_cpu_backend():
    assert gpu().resolve_model(AUTO_FAST_MODEL_ID) == "parakeet-tdt-0.6b-v3"


def test_optional_runtime_missing_keeps_whisper_functional():
    assert gpu(qwen_available=False, parakeet_available=False).recommended_model() == "large-v3"


def test_unknown_saved_model_cannot_reach_a_model_downloader():
    assert gpu().resolve_model("user/remote-code-model") == "qwen3-asr-1.7b"
    with pytest.raises(ValueError):
        get_model("user/remote-code-model")


def test_cancellation_happens_between_audio_windows(monkeypatch):
    event = threading.Event()
    calls = []

    def transcribe(audio, options):
        calls.append(len(audio))
        event.set()
        return "fr", [{"start": 0, "end": 1, "text": "Bonjour", "words": []}], "chunk"

    backend = SimpleNamespace(transcribe_chunk=transcribe)
    options = TranscriptionOptions(vad_filter=False, cancel_event=event)
    with pytest.raises(JobCancelled):
        transcribe_modern(backend, np.ones(40 * 16000, dtype=np.float32), options, 40, None)
    assert len(calls) == 1


def test_silence_never_calls_recognition_backend():
    backend = SimpleNamespace(transcribe_chunk=lambda *_: pytest.fail("Silent audio reached ASR"))
    result = transcribe_modern(backend, np.zeros(2 * 16000, dtype=np.float32), TranscriptionOptions(), 2, None)
    assert result["segments"] == []


def test_sentence_segments_preserve_punctuation_and_word_timing():
    words = [{"start": 0, "end": 0.5, "word": "Bonjour."}, {"start": 1, "end": 2, "word": "Merci !"}]
    segments = word_segments(words)
    assert len(segments) == 2
    assert segments[1]["start"] == 1
    assert segments[1]["text"] == "Merci!"
