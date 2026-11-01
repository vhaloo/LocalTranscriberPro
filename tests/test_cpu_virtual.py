import json
import sys
import threading
from types import SimpleNamespace

import pytest

from src.cpu_worker import AUTH_ENV, CPUWorkerClient, options_payload
from src.hardware import HardwareProfile
from src.jobs import JobCancelled
from src.settings import SettingsStore
from src.transcriber import TranscriberEngine, TranscriptionOptions
from src.translation import TranslationEngine, TranslationResourceError


def low_memory(**values):
    profile = HardwareProfile("Windows", "11", "AMD64", "CPU", 4, 4,
                              available_ram_gb=0.2, commit_free_gb=0.1, disk_free_gb=100)
    for key, value in values.items():
        setattr(profile, key, value)
    return profile


def test_explicit_cpu_paging_bypasses_only_physical_memory_floors():
    profile = low_memory()
    assert not profile.model_compatibility("large-v3", "cpu", True).supported
    forced = profile.model_compatibility("large-v3", "cpu-virtual", True)
    assert forced.supported and forced.device == "cpu" and forced.reason_code == "cpu_virtual"
    profile.cpu_backend_available = False
    assert profile.model_compatibility("large-v3", "cpu-virtual", True).reason_code == "cpu_runtime"
    profile.cpu_backend_available = True
    profile.disk_free_gb = 0
    assert profile.model_compatibility("large-v3", "cpu-virtual").reason_code == "disk"
    assert profile.model_compatibility("large-v3", "cpu-virtual", True).supported


def test_explicit_cpu_model_is_not_replaced_for_language_or_runtime():
    profile = low_memory(parakeet_available=False)
    assert profile.resolve_model("parakeet-tdt-0.6b-v3", "cpu-virtual", language="ar") == "parakeet-tdt-0.6b-v3"
    with pytest.raises(ValueError):
        profile.resolve_model("missing-model", "cpu-virtual")
    assert profile.resolve_model("large-v3", "cpu") != "large-v3"


def test_forced_native_cpu_failure_does_not_attempt_a_smaller_model(tmp_path, monkeypatch):
    calls = []
    def fail(model, **kwargs):
        calls.append((model, kwargs["device"]))
        raise MemoryError("OS commit limit")
    monkeypatch.setitem(sys.modules, "faster_whisper", SimpleNamespace(WhisperModel=fail))
    monkeypatch.setattr("src.transcriber.user_cache_dir", lambda *_: str(tmp_path))
    hardware = low_memory()
    hardware.refresh_resources = lambda: None
    engine = TranscriberEngine(hardware, isolated_cpu=False)
    with pytest.raises(RuntimeError, match="OS commit limit"):
        engine.load_model("large-v3", "cpu-virtual", options=TranscriptionOptions(offline=True))
    assert calls == [("large-v3", "cpu")]
    assert engine.model is None


def test_cpu_worker_uses_a_separate_process_and_cleans_up():
    import os
    worker = CPUWorkerClient()
    try:
        result = worker.call("ping")
        assert result == {"pid": worker.pid, "cpu_only": True}
        assert worker.pid != os.getpid()
        assert AUTH_ENV not in os.environ
    finally:
        worker.close()
        worker.close()
    assert not worker.alive


def test_cancel_terminates_owned_cpu_process_before_an_operation():
    worker = CPUWorkerClient()
    event = threading.Event()
    event.set()
    try:
        with pytest.raises(JobCancelled):
            worker.call("ping", cancel_event=event)
        assert not worker.alive
    finally:
        worker.close()


def test_native_worker_exit_is_recoverable_in_the_parent():
    worker = CPUWorkerClient()
    try:
        worker.call("ping")
        worker._process.terminate()
        worker._process.wait(timeout=10)
        with pytest.raises(RuntimeError, match="not replaced"):
            worker.call("ping")
    finally:
        worker.close()


def test_options_send_no_callbacks_or_threading_objects():
    payload = options_payload(TranscriptionOptions(cancel_event=threading.Event(),
        activity_callback=lambda *_: None, original_callback=lambda *_: None, target_language="fr"))
    assert "cancel_event" not in payload and "activity_callback" not in payload and "original_callback" not in payload
    assert json.loads(json.dumps(payload))["target_language"] == "fr"


def test_translation_paging_uses_cpu_and_retains_disk_checks(tmp_path, monkeypatch):
    hardware = low_memory(ctranslate_cuda=True, gpu_vram_free_gb=12)
    hardware.refresh_resources = lambda: None
    devices = []
    monkeypatch.setitem(sys.modules, "ctranslate2", SimpleNamespace(Translator=lambda _, **kwargs:
        devices.append((kwargs["device"], kwargs["compute_type"])) or object()))
    monkeypatch.setitem(sys.modules, "sentencepiece", SimpleNamespace(SentencePieceProcessor=lambda **_: object()))
    engine = TranslationEngine(tmp_path, isolated_cpu=False)
    engine.prepare = lambda *_: tmp_path
    engine._complete = lambda: True
    with pytest.raises(TranslationResourceError):
        engine.load(hardware, allow_download=False)
    engine.load(hardware, allow_download=False, allow_cpu_virtual_memory=True)
    assert devices == [("cpu", "int8")]
    engine.unload()
    engine._complete = lambda: False
    monkeypatch.setattr("shutil.disk_usage", lambda _: SimpleNamespace(free=0))
    with pytest.raises(RuntimeError, match="Go libres"):
        engine.load(hardware, allow_download=False, allow_cpu_virtual_memory=True)


def test_settings_keep_paging_and_explicit_update_preferences(tmp_path):
    path = tmp_path / "settings.json"
    path.write_text(json.dumps({"schema_version": 8, "device": "cpu-virtual", "model": "large-v3",
        "check_updates": False, "auto_install_updates": False}), "utf-8")
    store = SettingsStore(path)
    assert store.get("device") == "cpu-virtual" and store.get("model") == "large-v3"
    assert store.get("check_updates") is False and store.get("auto_install_updates") is False
    assert SettingsStore(tmp_path / "new.json").get("auto_install_updates") is True


def test_remote_overlap_keeps_each_language_confidence_and_reverse_translation():
    import numpy as np

    result = {"text": "مرحبا Bonjour", "language": "fr", "overlap_experimental": True, "segments": [
        {"text": "مرحبا", "language": "ar", "language_probability": 0.9, "recognition_index": 87,
         "start": 0, "end": 2, "overlap_experimental": True},
        {"text": "Bonjour", "language": "fr", "language_probability": 0.9, "recognition_index": 91,
         "start": 0, "end": 2, "overlap_experimental": True},
    ]}
    pairs = []
    def transcribe(*_args, **kwargs):
        pairs.append(kwargs["conversation_pair"])
        return result
    engine = object.__new__(TranscriberEngine)
    engine.model, engine.model_name, engine.backend, engine.device = object(), "tiny", "faster-whisper", "cpu"
    engine.audio_duration = lambda _: 2
    engine._cpu_worker = SimpleNamespace(transcribe=transcribe)
    engine.translator = TranslationEngine()
    engine.translator.reset_conversation("fr", "ar")
    engine.translator.translate = lambda text, target, *_: f"{target}:{text}"
    translated = engine._transcribe_locked(np.zeros(32000), TranscriptionOptions(
        conversation=True, overlap_separation=True, target_language="fr"), None)
    assert pairs == [("fr", "ar")]
    assert [item["target_language"] for item in translated["segments"]] == ["fr", "ar"]
    assert [item["source_language"] for item in translated["segments"]] == ["ar", "fr"]
    assert [item["recognition_index"] for item in translated["segments"]] == [87, 91]


@pytest.mark.parametrize("preset", ["files", "universal", "conference"])
def test_switching_simple_tasks_keeps_the_explicit_cpu_model(preset):
    from src.gui import TranscriberApp
    variable = SimpleNamespace(set=lambda *_: None)
    app = SimpleNamespace(selected_model_id="large-v3", selected_device="cpu-virtual", simple_quality="best",
        maximum_quality_beam=8, maximum_quality_chunk=30, beam_var=variable, chunk_var=variable,
        vad_var=variable, cleanup_var=variable, smart_subtitles_var=variable, translate_var=variable,
        speaker_var=variable)
    TranscriberApp._apply_maximum_quality_defaults(app, preset)
    assert app.selected_model_id == "large-v3" and app.selected_device == "cpu-virtual"
