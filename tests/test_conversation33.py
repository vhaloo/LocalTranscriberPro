import base64
import copy
import json
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace

import pytest
from cryptography.exceptions import InvalidTag

from src.gui import TranscriberApp
from src.private_session import decrypt_segments, encrypt_segments, save_private
from src.release_signature import verify_manifest
from src.review import audience_lines, correct_segment, retranslate_segment, review_flags, review_values
from src.session import PreviewScheduler, SessionController, identified
from src.translation import TranslationEngine


def turn():
    return identified([{"start": 1., "end": 3., "source_text": "عندي ١٢ كتابا", "source_language": "ar",
                        "target_language": "fr", "text": "J’ai 12 livres.", "third_language": "en",
                        "third_text": "I have 12 books.", "words": [], "recognition_index": 90}])[0]


def test_live_snapshot_keeps_edits_and_typed_replies_without_duplicates():
    controller = SessionController()
    original = turn()
    edited = correct_segment(original, "عندي ١٣ كتابا", speaker="Personne A")
    controller.correct(edited)
    reply = identified([{"start": 3., "end": 3., "text": "Merci", "input_mode": "typed"}])[0]
    controller.add_reply(reply)
    result = controller.snapshot([original])
    assert result[0]["source_text"] == "عندي ١٣ كتابا"
    assert original["text"] == "J’ai 12 livres."
    assert len(controller.snapshot(result)) == 2
    result[0]["revisions"].clear()
    assert controller.snapshot([original])[0]["revisions"]


def test_language_commands_are_atomic_and_applied_once():
    controller = SessionController()
    with ThreadPoolExecutor(max_workers=4) as pool:
        list(pool.map(lambda value: controller.configure_languages("fr", value, "en"), ["ar", "ht", "fa", "ur"] * 10))
    generation, command = controller.language_command(0)
    assert generation == 40 and command[0] == "fr" and command[2] == "en"
    assert controller.language_command(generation)[1] is None
    with pytest.raises(ValueError):
        controller.configure_languages("fr", "fr")


def test_original_edit_invalidates_translation_indices_but_keeps_timing_and_audit():
    item = turn()
    result = correct_segment(item, "عندي ١٣ كتابا", source_language="ar")
    assert result["start"] == 1 and result["end"] == 3
    assert result["translation_pending"] and result["text"] == "" and result["third_text"] == ""
    assert result["recognition_index"] is None and result["revisions"][0]["before"]["text"] == item["text"]
    assert not item.get("revisions")


def test_paired_editor_preserves_an_explicit_translation_entered_with_a_source_edit():
    item = turn()
    unchanged_translation = review_values(item, "مرحبا", item["text"], "ar", target_language="fr")
    assert unchanged_translation["translation_pending"] and unchanged_translation["text"] == ""
    both_edited = review_values(item, "مرحبا", "Bonjour", "ar", target_language="fr")
    assert both_edited["text"] == "Bonjour" and not both_edited["translation_pending"]
    assert both_edited["source_text"] == "مرحبا" and both_edited["recognition_index"] is None


def test_typed_reply_reads_that_reply_and_updates_completed_exports(tmp_path):
    from src.transcript_format import TranscriptFormat

    app = object.__new__(TranscriberApp)
    app.session_controller = SessionController()
    app.transcript_data = [turn()]
    app.current_session_base = tmp_path / "conversation"
    app.private_mode, app.busy = False, False
    app.recorder = SimpleNamespace(recording=False)
    app.render_transcript = lambda: None
    app._save_backup = lambda: None
    app.transcript_format_options = lambda: TranscriptFormat()
    spoken = []
    app.speak_items = lambda items: spoken.extend(items)
    reply = identified([{"start": 0., "end": 0., "source_text": "Bonjour", "source_language": "fr",
                         "text": "مرحبا", "target_language": "ar", "input_mode": "typed"}])[0]
    app._accept_reply(reply, app.session_controller)
    assert app.transcript_data[-1]["segment_id"] != reply["segment_id"]
    assert spoken == [("مرحبا", "ar")]
    assert "مرحبا" in (tmp_path / "conversation.json").read_text("utf-8")
    app._accept_reply(reply, SessionController())
    assert len(spoken) == 1


def test_manual_translation_and_retranslation_only_change_selected_turn():
    first, second = turn(), turn()
    original = copy.deepcopy(second)
    edited = correct_segment(first, first["source_text"], "Treize livres.")
    translator = SimpleNamespace(translate=lambda text, language, cancel=None: language + ": " + text, last_index=72)
    result = retranslate_segment(edited, translator)
    assert result["text"].startswith("fr:") and result["third_text"].startswith("en:")
    assert result["source_text"] == first["source_text"] and second == original
    assert result["revisions"][-1]["operation"] == "retranslate"


def test_numeric_review_normalizes_arabic_indic_digits_without_claiming_semantics():
    item = turn()
    assert "numbers" not in review_flags(item)
    item["text"] = "J’ai 13 livres."
    assert "numbers" in review_flags(item)


def test_provisional_scheduler_yields_to_final_audio_and_adapts_to_inference_cost():
    scheduler = PreviewScheduler()
    assert not scheduler.due(10, 3, pending=1)
    assert scheduler.due(10, 3)
    scheduler.completed(10, 3, 4)
    assert not scheduler.due(15, 6)
    assert scheduler.due(19, 6)
    scheduler.reset_turn()
    assert scheduler.duration == 0


def test_provisional_decode_is_lightweight_without_changing_final_accuracy_options():
    import queue

    import numpy as np

    from src.recording_ui import RecordingMixin
    from src.transcriber import TranscriptionOptions

    calls, shown = [], []
    def decode(_audio, options):
        calls.append(options)
        return {"text": "Bonjour", "language": "fr"}
    recorder = SimpleNamespace(preview_audio=lambda: np.zeros(32000, dtype="float32"),
                               audio_queue=queue.Queue(), available_seconds=lambda: 2)
    app = SimpleNamespace(recorder=recorder, engine=SimpleNamespace(transcribe_audio=decode),
        _safe_ui=lambda callback, *args: callback(*args), _show_live_preview=lambda *args: shown.append(args))
    final = TranscriptionOptions(beam_size=8, target_language="fr", conversation=True)
    RecordingMixin._try_provisional(app, final, PreviewScheduler())
    assert shown == [("Bonjour", "fr")]
    assert calls[0].beam_size == 1 and not calls[0].word_timestamps and calls[0].target_language is None
    assert final.beam_size == 8 and final.conversation and final.target_language == "fr"
    recorder.audio_queue.put(np.zeros(100))
    RecordingMixin._try_provisional(app, final, PreviewScheduler())
    assert len(calls) == 1


def test_unscored_recognizer_uses_real_local_language_hints_without_overriding_disagreement():
    from src.transcriber import TranscriberEngine, TranscriptionOptions

    engine = object.__new__(TranscriberEngine)
    engine.model_name = "qwen3-asr-0.6b"
    engine.language_identifier = SimpleNamespace(predict=lambda text: [
        {"language": "fr", "probability": 0.91}, {"language": "en", "probability": 0.08}])
    result = {"language": "fr", "text": "Bonjour à tous", "segments": [{}]}
    options = TranscriptionOptions(conversation=True)
    engine._annotate_text_language(result, options)
    assert result["language_probability"] == 0.91 and result["language_detection"] == "text-glotlid-v3"
    result["language"] = "ar"
    engine._annotate_text_language(result, options)
    assert result["language"] == "ar" and result["language_probability"] == 0
    engine.language_identifier = None
    unscored = {"language": "fr", "text": "Bonjour", "segments": [{}]}
    engine._annotate_text_language(unscored, options)
    assert "language_probability" not in unscored
    engine.language_identifier = SimpleNamespace(predict=lambda text: (_ for _ in ()).throw(RuntimeError("Unavailable")))
    engine._annotate_text_language(unscored, options)
    assert "language_probability" not in unscored and unscored["text"] == "Bonjour"


def test_automatic_conversation_reserves_translation_memory_before_reselecting_asr():
    import threading

    from src.transcriber import EngineStatus, TranscriberEngine, TranscriptionOptions
    from src.translation import TranslationResourceError

    events = []
    engine = object.__new__(TranscriberEngine)
    engine._load_lock = threading.RLock()
    engine.current_status = None
    engine.hardware = object()
    engine.language_identifier = None
    def load_asr(*_args):
        model = "omnilingual-1b-v2" if not events else "large-v3"
        events.append("asr:" + model)
        engine.backend = "omnilingual-onnx" if model.startswith("omni") else "faster-whisper"
        status = EngineStatus(model, "auto", "cpu", engine.backend, "int8", "auto-multilingual")
        engine.current_status = status
        return status
    def load_translation(*_args, **kwargs):
        assert kwargs["allow_download"] is False
        events.append("mt")
        if events.count("mt") == 1:
            raise TranslationResourceError("Combined memory")
    engine._load_model_unlocked = load_asr
    engine.unload_model = lambda: events.append("unload-asr")
    engine.translator = SimpleNamespace(unload=lambda: None, configure=lambda *_: None, load=load_translation)
    result = engine.load_model("auto-multilingual", options=TranscriptionOptions(
        target_language="fr", conversation=True, offline=True))
    assert events == ["asr:omnilingual-1b-v2", "mt", "unload-asr", "mt", "asr:large-v3"]
    assert result.model_id == "large-v3" and "translation_memory_reservation" in result.fallback_reason


def test_live_adaptation_never_replaces_a_working_arabic_pair_with_european_only_asr(monkeypatch):
    from src.recording_ui import RecordingMixin
    from src.transcriber import TranscriptionOptions

    hardware = SimpleNamespace(refreshed=False)
    hardware.refresh_resources = lambda: setattr(hardware, "refreshed", True)
    def choose(*_args):
        assert hardware.refreshed, "Refresh resources after the translator has become resident"
        return "parakeet-tdt-0.6b-v3"
    monkeypatch.setattr("src.recording_ui.conversation_model", choose)
    def forbidden_load(*_args):
        raise AssertionError("Keep the working engine when the candidate lacks Arabic")
    engine = SimpleNamespace(translator=SimpleNamespace(router=SimpleNamespace(pair=("fr", "ar"))),
        cached_model_ids=lambda: {"omnilingual-1b-v2", "parakeet-tdt-0.6b-v3"},
        model_name="omnilingual-1b-v2", _load_model_unlocked=forbidden_load)
    app = SimpleNamespace(engine=engine, hardware=hardware)
    RecordingMixin._adapt_conversation_model(app, TranscriptionOptions(conversation=True))
    assert engine.model_name == "omnilingual-1b-v2"


def test_unknown_language_cannot_silently_resolve_to_an_unsupported_tiny_model(tmp_path, monkeypatch):
    from src.hardware import HardwareProfile
    from src.transcriber import TranscriberEngine, TranscriptionOptions

    hardware = HardwareProfile("Windows", "11", "AMD64", "CPU", 8, 4, available_ram_gb=2)
    hardware.refresh_resources = lambda: None
    monkeypatch.setattr("src.transcriber.user_cache_dir", lambda *_args: str(tmp_path))
    engine = TranscriberEngine(hardware)
    engine.cached_model_ids = lambda: set()
    with pytest.raises(RuntimeError, match="supports the requested language"):
        engine._load_model_unlocked("auto-best", "cpu", options=TranscriptionOptions(language="xxxx"))


@pytest.mark.parametrize("language,backend_code", [("fil", "tl"), ("jv", "jw")])
def test_whisper_adaptor_accepts_language_picker_codes(language, backend_code):
    from src.transcriber import TranscriberEngine, TranscriptionOptions

    engine = object.__new__(TranscriberEngine)
    def transcribe(_source, **kwargs):
        assert kwargs["language"] == backend_code
        return iter([]), SimpleNamespace(language=backend_code)
    engine.model = SimpleNamespace(transcribe=transcribe)
    engine.translator = SimpleNamespace(router=None)
    result = engine._transcribe_faster("not-opened-by-fake-backend", TranscriptionOptions(language=language), 1, None)
    assert result["language"] == backend_code


def test_switching_language_pair_does_not_rewrite_previous_routed_turns():
    translator = TranslationEngine()
    translator.translate = lambda text, code, cancel=None: code + ": " + text
    translator.reset_conversation("fr", "ar")
    first = translator.translate_result({"text": "Bonjour", "language": "fr", "segments": [{"start": 0, "end": 2, "text": "Bonjour"}]}, "fr", True)["segments"]
    original = copy.deepcopy(first)
    translator.reset_conversation("fr", "ht")
    assert translator.complete_conversation(first) == original


def test_confidential_mode_never_creates_progressive_plaintext(tmp_path):
    app = object.__new__(TranscriberApp)
    app.private_mode = True
    app.transcript_data = [turn()]
    app.backup_file = tmp_path / "recovery.json"
    app.active_recording_base = tmp_path / "Conversation"
    app._save_backup()
    assert not list(tmp_path.iterdir())


def test_encrypted_session_round_trip_unicode_tamper_and_wrong_password(tmp_path):
    original = [correct_segment(turn(), "مرحبا", "Bonjour")]
    password = "long secret password"
    content = encrypt_segments(original, password)
    assert "مرحبا".encode() not in content and b"Bonjour" not in content
    assert decrypt_segments(content, password) == original
    for bad in (content[:-1], content[:-1] + bytes([content[-1] ^ 1])):
        with pytest.raises((InvalidTag, ValueError)):
            decrypt_segments(bad, password)
    with pytest.raises((InvalidTag, ValueError)):
        decrypt_segments(content, "another long password")
    path = tmp_path / "session.ltps"
    save_private(path, original, password)
    assert decrypt_segments(path.read_bytes(), password) == original
    assert not list(tmp_path.glob(".ltp-private-*"))


def test_private_format_rejects_short_password_and_unbounded_input():
    with pytest.raises(ValueError):
        encrypt_segments([turn()], "short")
    with pytest.raises(ValueError):
        decrypt_segments(b"not a private file", "long password")


def test_ed25519_signature_binds_version_filename_size_and_bytes():
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    key = Ed25519PrivateKey.generate()
    public = base64.b64encode(key.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)).decode()
    content = json.dumps({"version": "3.3.0", "assets": [{"name": "setup.exe", "size": 99, "sha256": "a" * 64}]}).encode()
    signature = base64.b64encode(key.sign(content))
    assert verify_manifest(content, signature, "3.3.0", "setup.exe", 99, public) == "a" * 64
    for data, version, name, size in ((content + b" ", "3.3.0", "setup.exe", 99), (content, "3.4.0", "setup.exe", 99),
                                     (content, "3.3.0", "evil.exe", 99), (content, "3.3.0", "setup.exe", 100)):
        with pytest.raises(ValueError, match="signature"):
            verify_manifest(data, signature, version, name, size, public)


def test_current_updater_requires_signature_and_keeps_cpu_flavor(monkeypatch):
    from src.updater import parse_release
    monkeypatch.setattr("src.runtime_flavor.cpu_only", lambda: True)
    base = "https://github.com/vhaloo/LocalTranscriberPro/releases/download/v3.4.0/"
    names = ["LocalTranscriberPro-3.4.0-Windows-x64-CPU-Setup.exe", "SHA256SUMS.txt"]
    payload = {"tag_name": "v3.4.0", "assets": [{"name": name, "size": 99, "browser_download_url": base + name} for name in names]}
    with pytest.raises(ValueError, match="signed"):
        parse_release(payload, "3.3.0")
    for name in ("release-manifest.json", "release-manifest.sig"):
        payload["assets"].append({"name": name, "size": 90, "browser_download_url": base + name})
    result = parse_release(payload, "3.3.0")
    assert result.signature_required and "CPU-Setup.exe" in result.filename


def test_missing_context_marker_falls_back_without_repeating_previous_turn():
    translator = TranslationEngine()
    translator.context_enabled = True
    translator.context = [("en", "Previous sentence")]
    calls = []
    def translate(text, target, cancel=None):
        calls.append(text)
        return "Précédente et nouvelle" if "987654321" in text else "Nouvelle phrase"
    translator.translate = translate
    assert translator.translate_contextual("New sentence", "fr", "en") == "Nouvelle phrase"
    assert calls[-1] == "New sentence"


def test_language_correction_invalidates_previous_detection_and_destination():
    original = turn()
    result = correct_segment(original, original["source_text"], source_language="fa", target_language="en")
    assert result["translation_pending"] and result["target_language"] == "en"
    assert result["language_probability"] is None and result["language_detection"] == "manual"
    assert result["revisions"][0]["before"]["target_language"] == "fr"


def test_windows_commit_limit_can_reject_model_despite_free_physical_ram():
    from src.hardware import HardwareProfile
    hardware = HardwareProfile("Windows", "11", "AMD64", "CPU", 8, 64, available_ram_gb=32, commit_free_gb=4)
    assert hardware.effective_available_ram_gb == 2
    assert not hardware.model_compatibility("omnilingual-1b-v2", "cpu", True).supported


def test_audience_readback_uses_visible_language_and_logical_unicode():
    item = turn()
    french = audience_lines([item], "fr")
    assert french == [("fr", "J’ai 12 livres.", "translated")]
    arabic = audience_lines([item], "ar")
    assert arabic == [("ar", item["source_text"], "original")]
    assert len(audience_lines([item])) == 3


def test_manual_bilingual_text_export_never_uses_display_glyphs_or_confidence(tmp_path):
    from src.transcript_format import TranscriptFormat
    app = object.__new__(TranscriberApp)
    app.transcript_format_options = lambda: TranscriptFormat()
    def forbidden_display_read():
        raise AssertionError("Bilingual exports must use logical segment text")
    app._editor_text = forbidden_display_read
    item = turn()
    path = tmp_path / "conversation.txt"
    app._write_export(path, [item])
    text = path.read_text("utf-8")
    assert item["source_text"] in text and item["text"] in text
    assert "90/100" not in text
