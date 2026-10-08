"""Pinned MADLAD target tokens, with generated English/French display names."""
from __future__ import annotations

import json
from pathlib import Path

LANGUAGE_DATA = json.loads((Path(__file__).parent / "data/translation_languages.json").read_text(encoding="utf-8"))
LANGUAGE_BY_CODE = {item["code"]: item for item in LANGUAGE_DATA["languages"]}
ASR_LANGUAGES = set(LANGUAGE_DATA["asr_languages"])
# Quick access, not a claim about an individual speaker's language or origin.
QUICK_LANGUAGES = "fr en ht pa hi fa es ar zh bn ur ta ln yo so ha ig ti am ps sw tr".split()


def normalize_language(code: str | None) -> str | None:
    return {"jw": "jv", "tl": "fil", "yue": "zh", "nb": "no", "iw": "he"}.get(code, code)


def language_label(code: str, ui_language: str = "fr") -> str:
    item = LANGUAGE_BY_CODE.get(code)
    return f"{item.get(ui_language, item['en'])} · {code}" if item else code


def language_choices(ui_language: str = "fr", speech_only: bool = False) -> list[tuple[str, str]]:
    return sorted(((code, language_label(code, ui_language)) for code in LANGUAGE_BY_CODE
                   if not speech_only or code in ASR_LANGUAGES),
                  key=lambda row: (QUICK_LANGUAGES.index(row[0]) if row[0] in QUICK_LANGUAGES else 1000, row[1].casefold()))
