import math

import pytest

from src.confidence import annotate_recognition, confidence_caption, model_index
from src.i18n import Translator
from src.segments import validate_segments


def test_indices_are_unavailable_without_model_evidence():
    result = annotate_recognition({"language": "fr", "segments": [{"text": "Bonjour"}]})
    item = result["segments"][0]
    assert item["recognition_index"] is None
    assert "indisponible" in confidence_caption(item, Translator("fr"))
    assert model_index(float("nan")) is None
    assert model_index(None) is None


def test_token_index_and_uncertain_language_are_kept_separate():
    item = annotate_recognition({"language_probability": 0.4, "segments": [
        {"avg_logprob": math.log(0.8), "words": [{"probability": 0.99}]}]})["segments"][0]
    assert item["recognition_index"] == 80
    assert item["language_uncertain"]
    assert "Langue à confirmer" in confidence_caption(item, Translator("fr"))


def test_bad_confidence_metadata_is_rejected_before_display():
    for value in (float("nan"), "certain", -1, 101):
        with pytest.raises(ValueError, match="recognition_index"):
            validate_segments([{"start": 0, "end": 1, "text": "Hello", "recognition_index": value}])
