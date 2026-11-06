import json
from string import Formatter

import pytest

from src import i18n
from src.guided_setup import SetupAnswers, setup_plan
from src.i18n_37 import MESSAGES
from src.settings import SettingsStore


@pytest.mark.parametrize("native,expected", [("fr-CA", "fr"), ("fr_FR", "fr"), ("en-GB", "en"),
                                             ("es-ES", "en"), ("ar-SA", "en")])
def test_system_display_language_and_documented_fallback(monkeypatch, native, expected):
    monkeypatch.setattr(i18n, "_native_ui_locale", lambda: native.replace("_", "-"))
    monkeypatch.setenv("LANG", "fr_CA.UTF-8")
    assert i18n.Translator("auto").language == expected


def test_posix_locale_precedence_and_auto_following(monkeypatch):
    monkeypatch.setattr(i18n, "_native_ui_locale", lambda: "")
    monkeypatch.setenv("LC_ALL", "en_GB.UTF-8")
    monkeypatch.setenv("LC_MESSAGES", "fr_CA.UTF-8")
    monkeypatch.setenv("LANG", "fr_FR.UTF-8")
    assert i18n.detect_ui_language() == "en"
    monkeypatch.delenv("LC_ALL")
    assert i18n.detect_ui_language() == "fr"
    assert i18n.Translator("en").language == "en"


def test_automatic_language_is_saved_as_a_preference_not_its_resolved_value(tmp_path, monkeypatch):
    path = tmp_path / "settings.json"
    store = SettingsStore(path)
    assert store.first_run and store.get("ui_language") == "auto"
    store.save()
    monkeypatch.setattr(i18n, "_native_ui_locale", lambda: "fr-CA")
    reloaded = SettingsStore(path)
    assert not reloaded.first_run and reloaded.get("ui_language") == "auto"
    assert i18n.Translator(reloaded.get("ui_language")).language == "fr"
    monkeypatch.setattr(i18n, "_native_ui_locale", lambda: "en-US")
    assert i18n.Translator(SettingsStore(path).get("ui_language")).language == "en"


@pytest.mark.parametrize("language", ["en", "fr"])
def test_upgrade_preserves_existing_manual_language_model_and_tuning(tmp_path, language):
    path = tmp_path / "settings.json"
    before = dict(schema_version=9, ui_language=language, model="small", device="cpu-virtual",
                  ui_mode="simple", preset="universal", chunk_seconds=45, beam_size=3,
                  translation_target="fr", conversation_partner="ar", speech_click_live=False)
    path.write_text(json.dumps(before), "utf-8")
    store = SettingsStore(path)
    assert all(store.get(key) == value for key, value in before.items() if key != "schema_version")
    assert store.get("schema_version") == 10 and not store.first_run
    assert not store.get("guided_setup_done")


@pytest.mark.parametrize("profile,model", [("best", "auto-best"), ("fast", "auto-fast"), ("coverage", "auto-multilingual")])
def test_reviewed_priority_prepares_a_plan_without_loading_a_model(profile, model):
    plan = setup_plan(SetupAnswers(profile=profile))
    assert plan["model"] == model and plan["device"] == "auto"
    assert plan["guided_setup_done"] and plan["ui_language"] == "auto"
    assert not {"output_folder", "check_updates", "auto_install_updates", "vocabulary", "translation_glossary"} & plan.keys()


def test_keep_profile_preserves_manual_cpu_model_and_fine_tuning(tmp_path):
    store = SettingsStore(tmp_path / "settings.json")
    store.update(dict(model="large-v3", device="cpu-virtual", beam_size=3, chunk_seconds=45,
                      ui_mode="advanced", voice_choice="local:fr", speech_slow=True))
    answers = SetupAnswers.from_settings(store)
    assert answers.profile == "keep" and answers.advanced
    plan = setup_plan(answers)
    assert not {"model", "device", "simple_quality", "voice_choice", "speech_slow"} & plan.keys()
    store.update(plan)
    assert store.get("model") == "large-v3" and store.get("device") == "cpu-virtual"
    assert store.get("beam_size") == 3 and store.get("chunk_seconds") == 45
    assert store.get("voice_choice") == "local:fr" and store.get("speech_slow")


def test_universal_plan_keeps_bidirectional_and_third_language_preferences():
    plan = setup_plan(SetupAnswers(preset="universal", spoken_language="en", speakers=True,
                                   target="fr", partner="ar", third="en", click_speech=True))
    assert plan["translate"] and plan["spoken_language"] == "auto" and not plan["speaker_detection"]
    assert plan["translation_target"] == "fr" and plan["conversation_partner"] == "ar"
    assert plan["translation_third"] == "en" and plan["speech_click_live"]
    assert "speech_click" not in plan


@pytest.mark.parametrize("changes", [dict(preset="other"), dict(profile="other"), dict(target="bad-code"),
                                      dict(ui_language="bad"), dict(preset="universal", target="fr", partner="fr")])
def test_invalid_answers_are_rejected_before_any_preferences_can_be_written(changes):
    with pytest.raises(ValueError):
        setup_plan(SetupAnswers(**changes))


def test_setup_bounds_only_the_reviewed_numeric_preferences():
    plan = setup_plan(SetupAnswers(font_size=999, effort=999, chunk_seconds=0))
    assert plan["conversation_font_size"] == 48 and plan["beam_size"] == 10 and plan["chunk_seconds"] == 5


def test_new_interface_messages_preserve_their_placeholders_in_both_languages():
    def names(value):
        return {field for _literal, field, _format, _conversion in Formatter().parse(value) if field}
    for key, (english, french) in MESSAGES.items():
        assert names(english) == names(french), key
