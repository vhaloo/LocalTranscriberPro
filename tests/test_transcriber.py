import sys
from types import SimpleNamespace

import pytest

from src.hardware import HardwareProfile
from src.models import AUTO_MODEL_ID
from src.transcriber import EngineStatus, TranscriberEngine


def test_preloaded_engine_reports_when_recording_is_armed():
    hardware = HardwareProfile(
        os_name="Windows",
        os_version="11",
        architecture="AMD64",
        cpu_name="Test CPU",
        cpu_threads=4,
        ram_gb=16,
        available_ram_gb=10,
    )
    engine = TranscriberEngine(hardware)
    engine.model = object()
    engine.model_name = "large-v3"
    engine.device = "cpu"
    engine.backend = "faster-whisper"
    engine.current_status = EngineStatus(
        model_id="large-v3",
        requested_device="cpu",
        device="cpu",
        backend="faster-whisper",
        compute_type="int8",
        requested_model_id=AUTO_MODEL_ID,
    )

    assert engine.is_ready(AUTO_MODEL_ID, "cpu")
    assert not engine.is_ready("large-v3", "cpu")
    assert engine.load_model(AUTO_MODEL_ID, "cpu") is engine.current_status


@pytest.mark.parametrize("backend,device,has_model,available,expected", [
    ("none", "cpu", False, True, 0),
    ("faster-whisper", "cpu", True, True, 0),
    ("mlx-whisper", "metal", True, True, 0),
    ("qwen3-asr", "metal", True, True, 1),
    ("openai-whisper", "metal", True, True, 1),
    ("qwen3-asr", "metal", True, False, 0),
])
def test_unloading_cpu_or_mlx_does_not_enter_an_unused_mps_allocator(
        tmp_path, monkeypatch, backend, device, has_model, available, expected):
    calls = []
    torch = SimpleNamespace(
        cuda=SimpleNamespace(is_available=lambda: False),
        backends=SimpleNamespace(mps=SimpleNamespace(is_available=lambda: available)),
        mps=SimpleNamespace(empty_cache=lambda: calls.append("mps")),
    )
    monkeypatch.setitem(sys.modules, "torch", torch)
    monkeypatch.setattr("src.transcriber.user_cache_dir", lambda *_args: str(tmp_path))
    hardware = HardwareProfile("macOS", "14", "arm64", "Test", 8, 16, torch_mps=available)
    engine = TranscriberEngine(hardware)
    engine.model = object() if has_model else None
    engine.backend, engine.device = backend, device
    engine.unload_model()
    assert len(calls) == expected
    assert engine.model is None and engine.model_name is None and engine.current_status is None
