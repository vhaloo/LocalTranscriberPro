import hashlib
import json
from types import SimpleNamespace

import pytest

from src.exports import write_bundle
from src.hardware import HardwareProfile
from src.models import AUTO_MULTILINGUAL_MODEL_ID, get_model
from src.segments import shift_segments
from src.settings import SettingsStore
from src.translation import ConversationRouter, TranslationEngine
from src.translation_languages import LANGUAGE_BY_CODE, language_choices, normalize_language
from src.translation_ui import display_line


def utterance(language, text, probability=0.99):
    return {"text": text, "language": language, "language_probability": probability,
            "segments": [{"start": 0, "end": 2, "text": text, "words": []}]}


def translator():
    engine = TranslationEngine()
    engine.translate = lambda text, target, _cancel=None: f"{target}: {text}"
    return engine


def test_universal_automatic_prefers_coverage_before_general_accuracy():
    hardware = HardwareProfile("Windows", "11", "AMD64", "CPU", 16, 64, available_ram_gb=32,
                               gpu_vram_gb=12, gpu_vram_free_gb=10, nvidia_detected=True,
                               ctranslate_cuda=True, torch_cuda=True, qwen_available=True, parakeet_available=True)
    assert hardware.resolve_model("auto-best") == "qwen3-asr-1.7b"
    assert hardware.resolve_model(AUTO_MULTILINGUAL_MODEL_ID) == "omnilingual-1b-v2"
    hardware.available_ram_gb = 8
    assert hardware.resolve_model(AUTO_MULTILINGUAL_MODEL_ID) == "large-v3"
    assert get_model("large-v3").coverage_score == 10
    assert get_model("qwen3-asr-1.7b").language_count == 30
    assert get_model("tiny.en").coverage_score == 0.1


def test_automatic_pair_completes_first_line_and_reverses_direction():
    engine = translator()
    first = engine.translate_result(utterance("fr", "Bonjour, comment allez-vous ?"), "fr", True, "en")
    assert first["segments"][0]["translation_pending"]
    second = engine.translate_result(utterance("ar", "أنا بخير شكراً"), "fr", True, "en")
    assert second["segments"][0]["target_language"] == "fr"
    completed = engine.complete_conversation(first["segments"])
    assert completed[0]["target_language"] == "ar"
    assert completed[0]["source_text"] == first["segments"][0]["source_text"]
    assert completed[0]["third_language"] == "en"
    assert first["segments"][0]["translation_pending"]  # immutable snapshot


def test_pair_reroutes_initial_default_translation_when_actual_pair_differs():
    engine = translator()
    first = engine.translate_result(utterance("ar", "مرحبا كيف حالك"), "fr", True)
    engine.translate_result(utterance("en", "I am doing well."), "fr", True)
    completed = engine.complete_conversation(first["segments"])
    assert completed[0]["target_language"] == "en"


def test_low_confidence_and_short_noise_do_not_lock_an_automatic_pair():
    router = ConversationRouter("fr")
    router.destination("ar", 0.1, "مرحبا")
    router.destination("zh", 0.99, "好")
    assert not router.pair


def test_manual_pair_is_stable_and_regional_destination_matches_base_speech():
    router = ConversationRouter("fr", "ar")
    assert router.destination("ar", 0.1, "نعم") == "fr"
    assert router.destination("fr", 0.1, "Oui") == "ar"
    assert router.destination("de", 0.99, "Guten Tag") == "fr"
    assert router.pair == ("fr", "ar")


def test_third_language_reuses_original_or_existing_translation():
    engine = translator()
    calls = []
    engine.translate = lambda text, language, _cancel=None: calls.append(language) or f"{language}: {text}"
    result = engine.translate_result(utterance("ar", "مرحبا"), "fr", False, "fr")
    assert calls == ["fr"]
    assert result["segments"][0]["third_text"] == result["segments"][0]["text"]


def test_one_turn_preserves_full_sentence_context_and_original_word_times():
    engine = translator()
    source = utterance("ar", "مرحبا. كيف حالك؟")
    source["segments"].append({"start": 2, "end": 4, "text": "كيف حالك؟", "words": [
        {"word": "كيف", "start": 2, "end": 2.5}]})
    result = engine.translate_result(source, "fr", True)
    assert len(result["segments"]) == 1
    assert result["segments"][0]["end"] == 4
    shifted = shift_segments(result["segments"], 10)
    assert shifted[0]["source_words"][0]["start"] == 12


def test_bilingual_exports_preserve_both_scripts_and_third_language(tmp_path):
    engine = translator()
    segments = engine.translate_result(utterance("ar", "مرحبا بك"), "fr", True, "en")["segments"]
    write_bundle(tmp_path / "conversation", segments)
    for extension in (".txt", ".srt", ".vtt", ".csv", ".json"):
        content = (tmp_path / ("conversation" + extension)).read_text(encoding="utf-8-sig")
        assert "مرحبا بك" in content
        assert "fr:" in content and "en:" in content
    assert "source_text" in json.loads((tmp_path / "conversation.json").read_text(encoding="utf-8"))[0]


def test_visual_arabic_shaping_never_replaces_logical_export_text():
    logical = "[ar] مرحباً بكم"
    visible, rtl = display_line(logical)
    assert rtl and visible != logical
    assert display_line("[fr] Bonjour") == ("[fr] Bonjour", False)


def test_full_language_prefix_and_eos_are_encoded_together():
    engine = TranslationEngine()
    encoded = []
    engine.tokenizer = SimpleNamespace(encode=lambda value, **_: encoded.append(value) or [value],
                                       decode=lambda tokens: " ".join(tokens))
    batches = []
    engine.model = SimpleNamespace(translate_batch=lambda batch, **_: batches.extend(batch) or [
        SimpleNamespace(hypotheses=[["Bonjour !"]])])
    assert engine.translate("Hello!", "fr") == "Bonjour !"
    assert encoded[-1] == "<2fr> Hello!"
    assert batches == [["<2fr> Hello!", "</s>"]]


def test_prepared_model_is_strictly_local_and_detects_corrupt_files(tmp_path, monkeypatch):
    import src.translation as module

    data = b"local test weights"
    monkeypatch.setattr(module, "FILES", {"model.bin": (len(data), hashlib.sha256(data).hexdigest())})
    (tmp_path / "model.bin").write_bytes(data)
    engine = TranslationEngine(tmp_path)
    assert engine.prepare(allow_download=False) == tmp_path
    (tmp_path / "model.bin").write_bytes(b"corrupt test model")
    with pytest.raises(RuntimeError, match="checksum"):
        engine.prepare(allow_download=False)


def test_missing_offline_model_fails_without_downloading(tmp_path):
    with pytest.raises(RuntimeError, match="préparé"):
        TranslationEngine(tmp_path).prepare(allow_download=False)


def test_old_english_translation_preference_migrates_and_font_is_bounded(tmp_path):
    path = tmp_path / "settings.json"
    path.write_text(json.dumps({"translate": True, "conversation_font_size": 200}), encoding="utf-8")
    settings = SettingsStore(path)
    assert settings.get("translation_target") == "en"
    assert settings.get("conversation_font_size") == 48


def test_destination_catalog_and_speech_list_are_distinct():
    assert len(LANGUAGE_BY_CODE) == 452
    assert len(language_choices("fr", speech_only=True)) == 99
    assert normalize_language("iw") == "he"
    assert normalize_language("jw") == "jv"


def test_translation_gpu_admission_does_not_reclaim_resident_asr_memory(tmp_path, monkeypatch):
    import sys

    devices = []
    monkeypatch.setitem(sys.modules, "ctranslate2", SimpleNamespace(Translator=lambda _, **kwargs:
        devices.append(kwargs["device"]) or object()))
    monkeypatch.setitem(sys.modules, "sentencepiece", SimpleNamespace(SentencePieceProcessor=lambda **_: object()))
    engine = TranslationEngine(tmp_path)
    engine.prepare = lambda *_: tmp_path
    engine._complete = lambda: True
    hardware = SimpleNamespace(refresh_resources=lambda: None, effective_available_ram_gb=12,
        ram_gb=32, ctranslate_cuda=True, gpu_vram_free_gb=1, gpu_vram_gb=12,
        effective_free_vram_gb=9, cpu_threads=8)
    engine.load(hardware, allow_download=False)
    assert devices == ["cpu"]


def test_original_becomes_available_before_translation_finishes():
    import numpy as np

    from src.transcriber import TranscriberEngine, TranscriptionOptions

    engine = object.__new__(TranscriberEngine)
    engine.model, engine.model_name, engine.backend, engine.device = object(), "large-v3", "faster-whisper", "cpu"
    engine._transcribe_faster = lambda *_: utterance("fr", "Bonjour tout le monde.")
    events = []
    engine.translator = SimpleNamespace(device="cpu", translate_result=lambda result, *_:
        events.append("translation_done") or result)
    options = TranscriptionOptions(target_language="ar", original_callback=lambda result:
        events.append("original:" + result["text"]), activity_callback=events.append)
    engine._transcribe_locked(np.zeros(16000), options, None)
    assert events == ["transcribing", "original:Bonjour tout le monde.", "translating", "translation_done"]
