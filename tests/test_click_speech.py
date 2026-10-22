import json
import queue
import sys
import threading
from types import SimpleNamespace

import pytest

from src.click_speech import ClickSpeechBinding, selected_lines, speech_language
from src.editing import apply_text_edits
from src.gui import TranscriberApp
from src.review import audience_lines
from src.settings import SettingsStore
from src.transcript_format import TranscriptFormat, plain_segments


@pytest.mark.parametrize("saved,expected", [({}, (False, True)),
    ({"speech_click": True, "speech_click_live": False}, (True, False)),
    ({"speech_click": "false", "speech_click_live": None}, (False, True))])
def test_old_settings_enable_live_reading_without_overriding_explicit_choices(tmp_path, saved, expected):
    path = tmp_path / "settings.json"
    path.write_text(json.dumps({"schema_version": 6, **saved}), "utf-8")
    store = SettingsStore(path)
    assert (store.get("speech_click"), store.get("speech_click_live")) == expected
    assert store.get("schema_version") == 7
    store.save()
    assert SettingsStore(path).data == store.data


def test_live_and_other_mode_preferences_are_independent_and_survive_mode_changes(tmp_path):
    app = object.__new__(TranscriberApp)
    app.settings, app.preset = SettingsStore(tmp_path / "settings.json"), "files"
    value = {"enabled": False}
    app.speech_click_var = SimpleNamespace(get=lambda: value["enabled"], set=lambda v: value.update(enabled=v))
    app._switch_click_speech_mode("universal")
    app.preset = "universal"
    assert value["enabled"] is True
    value["enabled"] = False
    app._switch_click_speech_mode("conference")
    app.preset = "conference"
    assert value["enabled"] is False
    value["enabled"] = True
    app._switch_click_speech_mode("universal")
    assert value["enabled"] is False
    assert app.settings.get("speech_click") is True


def test_plain_blocks_keep_language_metadata_and_never_merge_different_languages():
    values = [{"text": "Bonjour", "language": "fr", "start": 0, "end": 1},
              {"text": "à tous.", "language": "fr", "start": 1, "end": 2},
              {"text": "مرحبا", "language": "ar", "start": 2, "end": 3}]
    result = plain_segments(values, TranscriptFormat())
    assert [(item["text"], speech_language(item)) for item in result] == [("Bonjour à tous.", "fr"), ("مرحبا", "ar")]
    assert values[0]["text"] == "Bonjour"
    translated = {"text": "Hello", "source_language": "ar", "target_language": "en"}
    assert speech_language(translated) == "en"
    assert audience_lines([translated])[0][:2] == ("en", "Hello")


def test_file_recognition_persists_text_language_for_later_clicks():
    from src.transcriber import TranscriberEngine, TranscriptionOptions

    engine = object.__new__(TranscriberEngine)
    engine.model, engine.model_name, engine.device, engine.backend = object(), "tiny", "cpu", "faster-whisper"
    engine.audio_duration = lambda _: 2
    engine._transcribe_faster = lambda *_: {"text": "Bonjour", "language": "fr", "segments": [
        {"start": 0, "end": 1, "text": "Bonjour"}, {"start": 1, "end": 2, "text": "à tous"}]}
    result = engine._transcribe_locked("example.wav", TranscriptionOptions(), None)
    assert [speech_language(item) for item in result["segments"]] == ["fr", "fr"]
    result = engine._transcribe_locked("example.wav", TranscriptionOptions(task="translate"), None)
    assert speech_language(result["segments"][0]) == "en"


def test_multiline_selection_reads_each_utterance_once_but_preserves_repeated_turns():
    first = ("Hello\nworld", "en")
    another = tuple(["Hello\nworld", "en"])
    mapping = {1: first, 2: first, 4: another, 5: another}
    assert selected_lines(mapping, 1, 5) == [first, another]
    assert selected_lines(mapping, 2, 4) == [first, another]


def test_enabling_click_reading_after_a_whole_line_edit_keeps_every_replacement_word():
    values = [{"start": 0, "end": 2, "text": "Bonjour.", "language": "fr"},
              {"start": 2, "end": 4, "text": "Hello.", "language": "en"}]
    before = "[00:00:00] Bonjour.\n\n[00:00:02] Hello."
    result = apply_text_edits(values, before, "Texte corrigé.\n\n[00:00:02] Hello.")
    assert result[0]["text"] == "Texte corrigé."
    assert result[1]["text"] == "Hello." and result[0]["language"] == "fr"


def test_click_reads_logical_language_even_with_a_different_manually_selected_voice(monkeypatch):
    app = object.__new__(TranscriberApp)
    app.voice_choice = "local:en"
    app.slow_voice_var = SimpleNamespace(get=lambda: False)
    app.system_voices = []
    spoken = []
    app.speech_output = SimpleNamespace(ready=lambda _: True, supports=lambda _: True,
        synthesize=lambda text, code, *a, **k: (spoken.append((text, code)) or [0., 0.], 16000))
    started = []
    app._start_speech_operation = lambda op, **kw: started.append((op, kw))
    monkeypatch.setitem(sys.modules, "sounddevice", SimpleNamespace(play=lambda *_: None,
        get_stream=lambda: SimpleNamespace(active=False)))
    app.speak_items([("مرحبا بكم", "ar"), ("Bonjour", "fr"), ("Hello", "en")], follow_language=True, replace=True)
    started[0][0](threading.Event())
    assert spoken == [("مرحبا بكم", "ar"), ("Bonjour", "fr"), ("Hello", "en")]
    assert started[0][1] == {"replace": True}


def test_missing_local_voice_can_be_declined_without_starting_speech(monkeypatch):
    app = object.__new__(TranscriberApp)
    app.voice_choice, app.system_voices = "auto", []
    app.speech_output = SimpleNamespace(ready=lambda _: False, supports=lambda _: True)
    app.t = lambda key, **kw: key
    app._voice_download_message = lambda _: "download?"
    monkeypatch.setattr("src.speech_output_ui.messagebox.askyesno", lambda *a, **k: False)
    app._start_speech_operation = lambda *_a, **_k: pytest.fail("Must not speak/download after refusal")
    app.speak_items([("مرحبا", "ar")], follow_language=True, replace=True)


@pytest.mark.parametrize("status", ["speech_playing_idle", "speech_failed"])
def test_finished_speech_updates_feedback_without_hiding_an_error(status):
    app = object.__new__(TranscriberApp)
    app.voice_cancel = threading.Event()
    app._pending_speech_operation, app.playback_pause_owned, app.closing = None, False, False
    app._speech_status = "speech_playing_idle"
    app.status_label = SimpleNamespace(cget=lambda _: status)
    app.t = lambda key: key
    shown = []
    app._set_status = shown.append
    app._speech_finished(app.voice_cancel)
    assert shown == (["speech_finished"] if status == "speech_playing_idle" else [])


@pytest.mark.parametrize("already_paused", [False, True])
def test_new_click_replaces_pending_playback_and_resumes_only_owned_capture_pause(monkeypatch, already_paused):
    app = object.__new__(TranscriberApp)
    callbacks, calls = queue.Queue(), []
    app.speech_thread, app._pending_speech_operation = None, None
    app.playback_pause_owned, app.closing = False, False
    app.recorder = SimpleNamespace(recording=True, paused=already_paused)
    def pause():
        calls.append("pause")
        app.recorder.paused = True
    def resume():
        calls.append("resume")
        app.recorder.paused = False
    app.recorder.pause, app.recorder.resume = pause, resume
    app.t, app._set_status = lambda key: key, lambda _: None
    app._safe_ui = lambda fn, *a: callbacks.put((fn, a))
    app.after = lambda _ms, fn, *a: callbacks.put((fn, a))
    monkeypatch.setitem(sys.modules, "sounddevice", SimpleNamespace(stop=lambda: None))
    started = threading.Event()
    def first(cancel):
        calls.append("first")
        started.set()
        assert cancel.wait(3)
    app._start_speech_operation(first)
    assert started.wait(3)
    # Hold a completed worker until the UI has both replacements queued.
    app._start_speech_operation(lambda _: calls.append("discarded"), replace=True)
    app._start_speech_operation(lambda _: calls.append("latest"), replace=True)
    app.speech_thread.join(3)
    for _ in range(20):
        if callbacks.empty():
            break
        fn, args = callbacks.get(timeout=3)
        fn(*args)
        app.speech_thread.join(3)
    assert "latest" in calls and "discarded" not in calls
    assert calls.count("pause") == calls.count("resume") == (0 if already_paused else 1)


@pytest.mark.parametrize("lock_state", [0, 8 if sys.platform == "win32" else 16])
def test_click_gestures_ignore_metadata_selection_modifiers_and_stale_rows(lock_state):
    pending, spoken = {}, []
    mapping = {1: ("مرحبا", "ar")}
    widget = SimpleNamespace(index=lambda _: "1.0", dlineinfo=lambda _: (0, 10, 100, 24, 20),
        tag_ranges=lambda _: (), after=lambda _ms, callback: pending.update(read=callback) or "timer",
        after_cancel=lambda _: pending.clear(), winfo_exists=lambda: True,
        tag_remove=lambda *a: None, tag_add=lambda *a: None)
    binding = object.__new__(ClickSpeechBinding)
    binding.widget, binding.textbox = widget, SimpleNamespace(_speech_lines=mapping)
    binding.enabled, binding.speak, binding.press, binding.pending = lambda: True, spoken.append, None, None
    event = SimpleNamespace(x=20, y=20, state=lock_state)
    binding._press(event)
    binding._release(event)
    pending.pop("read")()
    assert spoken == [("مرحبا", "ar")]
    for change in (lambda: setattr(event, "state", 1), lambda: setattr(event, "y", 100),
                   lambda: mapping.clear()):
        event.state, event.y = 0, 20
        change()
        binding._press(event)
        binding._release(event)
        assert not pending
    mapping[1] = ("Bonjour", "fr")
    event.y = 20
    binding._press(event)
    mapping[1] = ("Other turn", "en")
    binding._release(event)
    assert not pending and len(spoken) == 1
