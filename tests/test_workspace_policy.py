import json
from types import SimpleNamespace

import pytest

from src.gui import TranscriberApp
from src.hardware import HardwareProfile
from src.i18n import Translator
from src.settings import SettingsStore
from src.transcriber import EngineStatus


@pytest.mark.parametrize(
    "schema,model,expected",
    [
        (7, "auto-multilingual", "auto-best"),
        (8, "auto-multilingual", "auto-multilingual"),
        (7, "qwen3-asr-1.7b", "qwen3-asr-1.7b"),
        (7, "large-v3", "large-v3"),
        (7, "auto-fast", "auto-fast"),
    ],
)
def test_live_default_migrates_once_and_keeps_explicit_model_choices(tmp_path, schema, model, expected):
    path = tmp_path / "settings.json"
    path.write_text(
        json.dumps(
            {
                "schema_version": schema,
                "model": model,
                "preset": "universal",
                "speech_click_live": False,
                "translation_target": "ar",
            }
        ),
        "utf-8",
    )
    store = SettingsStore(path)
    assert store.get("model") == expected
    assert store.get("translation_target") == "ar"
    assert store.get("speech_click_live") is False
    store.save()
    assert SettingsStore(path).get("model") == expected


@pytest.mark.parametrize("task", ["files", "link"])
def test_non_microphone_tasks_do_not_open_an_input_stream(task):
    def unexpected(*_args):
        pytest.fail("A non-microphone task tried to open an audio input")

    app = SimpleNamespace(
        running=True, preset=task, recorder=SimpleNamespace(recording=False, start_monitor=unexpected)
    )
    TranscriberApp._start_microphone_monitor(app)


@pytest.mark.parametrize("requested,expected", [("auto-best", "tiny"), ("medium", "large-v3")])
def test_model_summary_uses_loaded_status_only_for_the_current_request(requested, expected):
    captured = {}
    app = SimpleNamespace(
        selected_model_id="auto-best",
        selected_device="auto",
        hardware=HardwareProfile("Windows", "11", "AMD64", "CPU", 8, 32, available_ram_gb=16),
        engine=SimpleNamespace(model_name="tiny", cached_model_ids=lambda: []),
        last_engine_status=EngineStatus("tiny", "auto", "cpu", "faster-whisper", "int8", requested),
        simple_auto_summary_label=SimpleNamespace(configure=lambda **values: captured.update(values)),
        t=Translator("en"),
    )
    TranscriberApp._update_model_indicators(app)
    assert expected in captured["text"]
    assert "CPU" in captured["text"]
