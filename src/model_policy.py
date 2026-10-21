"""Conservative per-language routing. Coverage is not measured accuracy.

Small historical diagnostics never drive automatic quality choices. An
explicit benchmark profile must cover >=20 utterances and >=5 speakers.
"""
from __future__ import annotations

from src.models import MODEL_BY_ID, get_model


def measured_choice(language, profiles, hardware, cached=()):
    eligible = []
    for row in profiles:
        if (row.get("language") != language or row.get("utterances", 0) < 20
                or row.get("speakers", 0) < 5 or not row.get("dataset_revision")):
            continue
        model = row.get("model")
        error = row.get("cer")
        if (model not in MODEL_BY_ID or not isinstance(error, (int, float)) or not 0 <= error < 10
                or not get_model(model).supports(language, "transcribe")):
            continue
        if hardware.model_compatibility(model, "auto", model in cached).supported:
            eligible.append((error, model))
    return min(eligible)[1] if eligible else None


def conversation_model(language, hardware, cached=(), profiles=()):
    measured = measured_choice(language, profiles, hardware, cached)
    if measured:
        return measured
    # Once a language is known, general accuracy has priority over the number
    # of languages in an engine's catalogue. Unsupported languages retain Omni.
    return hardware.recommended_model("auto", cached, language, "transcribe")
