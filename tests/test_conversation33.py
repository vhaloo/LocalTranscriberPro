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
from src.review import audience_lines, correct_segment, retranslate_segment, review_flags
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
