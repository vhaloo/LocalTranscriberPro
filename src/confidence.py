"""Uncalibrated model indices, never probabilities of factual correctness."""
from __future__ import annotations

import math


def model_index(log_probability):
    try:
        value = float(log_probability)
        return round(100 * math.exp(min(0, value))) if math.isfinite(value) else None
    except (TypeError, ValueError, OverflowError):
        return None


def annotate_recognition(result):
    language_probability = result.get("language_probability")
    for item in result.get("segments", []):
        item["language_probability"] = language_probability
        item["language"] = result.get("language")
        item["language_uncertain"] = language_probability is not None and language_probability < 0.65
        score = model_index(item.get("avg_logprob"))
        if score is None:
            values = [word.get("probability") for word in item.get("words", [])]
            values = [value for value in values if isinstance(value, (int, float)) and math.isfinite(value) and 0 <= value <= 1]
            score = round(100 * sum(values) / len(values)) if values else None
        item["recognition_index"] = score
    return result


def confidence_caption(item, t):
    fields = [t("confidence_asr", value=item["recognition_index"]) if item.get("recognition_index") is not None
              else t("confidence_asr_unavailable")]
    if item.get("language_probability") is not None:
        fields.append(t("confidence_language", value=round(100 * item["language_probability"])))
    if "source_text" in item and not item.get("translation_pending"):
        fields.append(t("confidence_mt", value=item["translation_index"]) if item.get("translation_index") is not None
                      else t("confidence_mt_unavailable"))
    if item.get("third_text") and item.get("third_language") not in {item.get("source_language"), item.get("target_language")}:
        value = (t("confidence_mt", value=item["third_translation_index"]) if item.get("third_translation_index") is not None
                 else t("confidence_mt_unavailable"))
        fields.append(f"{item['third_language']} : {value}")
    if item.get("language_uncertain"):
        fields.append(t("confidence_confirm"))
    if item.get("overlap_experimental"):
        fields.append(t("overlap_review"))
    return "  ·  ".join(fields)
