from src.i18n import STRINGS, Translator


def test_translator_switches_language_and_formats_values():
    translator = Translator("en")
    assert translator("progress_file", name="audio.wav", index=1, total=2).startswith("Transcribing")
    translator.set_language("fr")
    assert translator("progress_file", name="audio.wav", index=1, total=2).startswith("Transcription")


def test_english_and_french_interfaces_have_the_same_messages():
    assert set(STRINGS["en"]) == set(STRINGS["fr"])
