"""Logical Unicode bilingual edits and selective retranslation, without UI."""
from __future__ import annotations

import copy
import re
from datetime import UTC, datetime


def review_flags(item):
    flags = []
    if item.get("language_uncertain"):
        flags.append("language")
    if item.get("overlap_experimental"):
        flags.append("overlap")
    if item.get("translation_pending"):
        flags.append("pending")
    original = str(item.get("source_text", item.get("text", "")))
    translated = str(item.get("text", ""))
    # These are prompts for review, never semantic correctness estimates.
    def digits(text):
        import unicodedata
        normalized = "".join(str(unicodedata.digit(char)) if char.isdecimal() else char for char in text)
        return sorted(re.findall(r"\d+(?:[.,]\d+)?", normalized))
    if "source_text" in item and not item.get("translation_pending") and digits(original) != digits(translated):
        flags.append("numbers")
    return flags


def correct_segment(segment, source, translation=None, source_language=None, speaker=None, target_language=None):
    if len(source) > 20000 or (translation is not None and len(translation) > 20000):
        raise ValueError("A reviewed turn must stay under 20,000 characters")
    result = copy.deepcopy(segment)
    before = {key: result.get(key) for key in ("source_text", "text", "source_language", "target_language", "speaker")}
    bilingual = "source_text" in result
    previous = result.get("source_text" if bilingual else "text", "")
    result["source_text" if bilingual else "text"] = source.strip()
    language_changed = bool(source_language and source_language != result.get("source_language" if bilingual else "language"))
    target_changed = bool(bilingual and target_language and target_language != result.get("target_language"))
    if target_changed:
        result["target_language"] = target_language
    if source_language:
        result["source_language" if bilingual else "language"] = source_language
    if language_changed:
        result.update(language_probability=None, language_uncertain=False, language_detection="manual")
    if speaker is not None:
        result["speaker"] = speaker.strip()[:100]
    if source.strip() != previous or language_changed or target_changed:
        result.update(words=[], source_words=[], recognition_index=None, edited=True)
        if bilingual:
            result.update(translation_pending=True, translation_index=None, third_translation_index=None,
                          third_text="", text="")
    if translation is not None and bilingual:
        result.update(text=translation.strip(), translation_pending=False, translation_index=None,
                      translation_edited=True)
    after = {key: result.get(key) for key in before}
    if after != before:
        result.setdefault("revisions", []).append({"at": datetime.now(UTC).isoformat(),
                                                   "before": before, "after": after})
    result["review_flags"] = review_flags(result)
    return result


def retranslate_segment(segment, translator, cancel_event=None):
    result = copy.deepcopy(segment)
    if "source_text" not in result or not result.get("target_language"):
        raise ValueError("Choose the source and destination languages before retranslating")
    original = result["source_text"]
    source, target = result.get("source_language"), result["target_language"]
    result["text"] = original if source == target else translator.translate(original, target, cancel_event)
    result.update(translation_pending=False, translation_index=None if source == target else translator.last_index,
                  translation_edited=False)
    third = result.get("third_language")
    if third:
        result["third_text"] = original if third == source else (result["text"] if third == target
                                  else translator.translate(original, third, cancel_event))
        result["third_translation_index"] = None
    result["review_flags"] = review_flags(result)
    result["retranslated_from_revision"] = len(segment.get("revisions", []))
    result.setdefault("revisions", []).append({"at": datetime.now(UTC).isoformat(),
        "operation": "retranslate", "before": {"text": segment.get("text", "")}, "after": {"text": result["text"]}})
    return result
