"""Selected-checkpoint downloads, low-memory quality and network-free browsing."""
import sys
import threading
from types import SimpleNamespace

import pytest

from src.gui import TranscriberApp
from src.hardware import HardwareProfile
from src.i18n import Translator
from src.jobs import JobCancelled
from src.model_cache import prepare_mlx_model, snapshot
from src.models import AUTO_MODEL_ID, get_model
from src.transcriber import TranscriberEngine, TranscriptionOptions


def hardware(**changes):
    values = dict(os_name="Windows", os_version="11", architecture="AMD64", cpu_name="CPU",
                  cpu_threads=4, ram_gb=4, available_ram_gb=0.2, disk_free_gb=50)
    values.update(changes)
    result = HardwareProfile(**values)
    result.refresh_resources = lambda: None
    return result


@pytest.mark.parametrize("ram", [2, 4, 8])
def test_accuracy_trades_speed_for_the_full_checkpoint_on_small_computers(ram):
    profile = hardware(ram_gb=ram)
    choice = profile.selection_compatibility(AUTO_MODEL_ID)
    assert choice.model_id == "large-v3" and choice.supported
    assert choice.device == "cpu" and choice.reason_code == "cpu_virtual"


def test_quality_does_not_choose_a_cached_tiny_instead_of_downloadable_large():
    profile = hardware(ram_gb=32, available_ram_gb=20)
    assert profile.resolve_model(AUTO_MODEL_ID, cached_model_ids={"tiny"}) == "large-v3"


def test_paging_keeps_disk_runtime_and_forced_gpu_checks():
    profile = hardware(disk_free_gb=0)
    assert not profile.selection_compatibility(AUTO_MODEL_ID).supported
    assert profile.selection_compatibility(AUTO_MODEL_ID, cached_model_ids={"large-v3"}).model_id == "large-v3"
    profile.cpu_backend_available = False
    assert not profile.selection_compatibility(AUTO_MODEL_ID, cached_model_ids={"large-v3"}).supported
    profile.cpu_backend_available = True
    assert not profile.selection_compatibility(AUTO_MODEL_ID, "cuda", {"large-v3"}).supported


def test_32bit_profile_does_not_automatically_attempt_large_paging():
    assert hardware(architecture="x86", available_ram_gb=2).recommended_model() == "tiny"


def test_automatic_paging_uses_the_owned_worker_and_retains_the_user_profile(tmp_path, monkeypatch):
    calls = []
    class Worker:
        pid = 12345
        alive = True
        def call(self, operation, payload, **_kwargs):
            calls.append((operation, payload["model"]))
            return dict(model_id=payload["model"], requested_device="cpu-virtual", device="cpu",
                        backend="faster-whisper", compute_type="int8")
        def close(self):
            self.alive = False
    monkeypatch.setattr("src.cpu_worker.CPUWorkerClient", Worker)
    monkeypatch.setattr("src.transcriber.user_cache_dir", lambda *_: str(tmp_path))
    engine = TranscriberEngine(hardware())
    status = engine.load_model(AUTO_MODEL_ID)
    assert calls == [("load_asr", "large-v3")]
    assert status.requested_model_id == AUTO_MODEL_ID and status.requested_device == "auto"
    assert status.memory_mode == "virtual" and status.worker_pid == 12345
    assert engine.is_ready(AUTO_MODEL_ID)
    engine.unload_model()


def test_failed_gpu_and_cpu_do_not_download_other_checkpoints(tmp_path, monkeypatch):
    calls = []
    def fail(model, **values):
        calls.append((model, values["device"]))
        raise RuntimeError("Native runtime failed")
    monkeypatch.setitem(sys.modules, "faster_whisper", SimpleNamespace(WhisperModel=fail))
    monkeypatch.setattr("src.transcriber.user_cache_dir", lambda *_: str(tmp_path))
    profile = hardware(ram_gb=32, available_ram_gb=20, nvidia_detected=True,
                       ctranslate_cuda=True, gpu_vram_gb=8, gpu_vram_free_gb=8)
    engine = TranscriberEngine(profile, isolated_cpu=False)
    with pytest.raises(RuntimeError, match="No other speech model"):
        engine.load_model(AUTO_MODEL_ID)
    assert calls == [("large-v3", "cuda"), ("large-v3", "cpu")]
    assert engine.model is None


def test_modern_model_failure_never_fetches_a_whisper_fallback(tmp_path, monkeypatch):
    def fail(*_args, **_kwargs):
        raise RuntimeError("Qwen runtime failed")
    monkeypatch.setattr("src.modern_backends.QwenBackend", fail)
    monkeypatch.setitem(sys.modules, "faster_whisper", SimpleNamespace(
        WhisperModel=lambda *_args, **_kwargs: pytest.fail("Another checkpoint reached its downloader")))
    monkeypatch.setattr("src.transcriber.user_cache_dir", lambda *_: str(tmp_path))
    engine = TranscriberEngine(hardware(ram_gb=32, available_ram_gb=20, torch_cpu_available=True,
                                       qwen_available=True))
    with pytest.raises(RuntimeError, match="no other speech model"):
        engine.load_model("qwen3-asr-1.7b", "cpu")
    assert engine.model is None


def test_cancellation_stops_before_any_model_or_retry(tmp_path, monkeypatch):
    event = threading.Event()
    event.set()
    monkeypatch.setattr("src.transcriber.user_cache_dir", lambda *_: str(tmp_path))
    monkeypatch.setitem(sys.modules, "faster_whisper", SimpleNamespace(
        WhisperModel=lambda *_args, **_kwargs: pytest.fail("Cancelled work reached a downloader")))
    with pytest.raises(JobCancelled):
        TranscriberEngine(hardware()).load_model(AUTO_MODEL_ID, options=TranscriptionOptions(cancel_event=event))


def test_offline_missing_model_fails_before_a_downloader(tmp_path, monkeypatch):
    monkeypatch.setattr("src.transcriber.user_cache_dir", lambda *_: str(tmp_path))
    monkeypatch.setattr("src.modern_backends.ParakeetBackend",
                        lambda *_args, **_kwargs: pytest.fail("Offline missing model reached downloader"))
    engine = TranscriberEngine(hardware(parakeet_available=True, available_ram_gb=2))
    with pytest.raises(RuntimeError, match="not prepared for offline"):
        engine.load_model("parakeet-tdt-0.6b-v3", "cpu", options=TranscriptionOptions(offline=True))


@pytest.mark.parametrize("mlx", [False, True])
def test_incomplete_cached_snapshot_in_offline_mode_never_contacts_network(tmp_path, monkeypatch, mlx):
    calls = []
    def cached_only(_repository, **options):
        calls.append(options)
        assert options.get("local_files_only") is True
        return str(tmp_path)
    monkeypatch.setattr("huggingface_hub.snapshot_download", cached_only)
    with pytest.raises(FileNotFoundError):
        if mlx:
            prepare_mlx_model(tmp_path, "large-v3", allow_download=False)
        else:
            snapshot(tmp_path, "Qwen/Qwen3-ASR-1.7B", "pinned", ["*.safetensors"], allow_download=False)
    assert len(calls) == 1


def test_mlx_prepares_only_the_selected_repository_then_reuses_it_offline(tmp_path, monkeypatch):
    calls = []
    def download(repository, **options):
        calls.append((repository, options))
        if not options.get("local_files_only"):
            (tmp_path / "config.json").write_text("{}")
            (tmp_path / "weights.npz").write_bytes(b"weights")
        return str(tmp_path)
    monkeypatch.setattr("huggingface_hub.snapshot_download", download)
    assert prepare_mlx_model(tmp_path, "large-v3") == tmp_path
    assert prepare_mlx_model(tmp_path, "large-v3", allow_download=False) == tmp_path
    assert {item[0] for item in calls} == {"mlx-community/whisper-large-v3-mlx"}
    assert sum(not item[1].get("local_files_only", False) for item in calls) == 1


def test_navigation_neither_loads_models_nor_starts_downloads():
    states = []
    control = SimpleNamespace(configure=lambda **values: states.append(values))
    profile = hardware()
    app = SimpleNamespace(
        closing=False, busy=False, recorder=SimpleNamespace(recording=False),
        preload_generation=0, model_preloading=False, hardware=profile,
        engine=SimpleNamespace(cached_model_ids=lambda: set(), is_ready=lambda *_: False,
                               load_model=lambda *_: pytest.fail("Navigation started a model download")),
        selected_model_id=AUTO_MODEL_ID, selected_device="auto", selected_language="auto",
        prepare_model_button=control, cancel_button=control, record_button=control,
        _update_model_indicators=lambda: None, _set_status=lambda value: states.append(value), t=Translator("fr"),
    )
    for model in (AUTO_MODEL_ID, "auto-fast", "small", "tiny", AUTO_MODEL_ID):
        app.selected_model_id = model
        TranscriberApp.preload_selected_model(app)
    assert app.preload_generation == 5 and app.model_preloading is False
    assert any(isinstance(value, str) and "premier usage" in value for value in states)
    assert get_model(profile.resolve_model(AUTO_MODEL_ID)).model_id == "large-v3"


def test_shared_hub_snapshot_is_loaded_directly_without_another_download(tmp_path, monkeypatch):
    shared = tmp_path / "shared" / "models--Systran--faster-whisper-large-v3" / "snapshots" / "offline-revision"
    shared.mkdir(parents=True)
    for name in ("model.bin", "config.json", "tokenizer.json"):
        (shared / name).write_text("local fixture")
    calls = []
    def load(model, **options):
        assert model == str(shared) and options["local_files_only"] is True
        calls.append(model)
        return object()
    monkeypatch.setitem(sys.modules, "faster_whisper", SimpleNamespace(WhisperModel=load))
    monkeypatch.setattr("src.transcriber.user_cache_dir", lambda *_: str(tmp_path / "app"))
    engine = TranscriberEngine(hardware(ram_gb=32, available_ram_gb=20))
    engine.cache_roots = lambda: [engine.model_cache, tmp_path / "shared"]
    status = engine.load_model(AUTO_MODEL_ID, "cpu", options=TranscriptionOptions(offline=True))
    assert status.model_id == "large-v3" and calls == [str(shared)]
