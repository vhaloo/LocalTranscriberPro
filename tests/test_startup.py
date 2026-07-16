from src.startup import STARTUP_TEXT, startup_language


def test_startup_messages_match_in_both_languages():
    assert set(STARTUP_TEXT["en"]) == set(STARTUP_TEXT["fr"])


def test_startup_language_follows_french_environment(monkeypatch):
    monkeypatch.setenv("LANG", "fr_CA.UTF-8")
    monkeypatch.delenv("LC_ALL", raising=False)
    assert startup_language() == "fr"
