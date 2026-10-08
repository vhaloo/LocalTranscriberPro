"""Regenerate pinned, human-readable translation language metadata (development only)."""
from __future__ import annotations

import json
import re
import urllib.request
from pathlib import Path

import pycountry
from babel import Locale, UnknownLocaleError
from faster_whisper.tokenizer import _LANGUAGE_CODES

ROOT = Path(__file__).resolve().parents[1]
URL = "https://huggingface.co/santhosh/madlad400-3b-ct2/resolve/c32ad0cf118807ea6258d14be137547155842723/shared_vocabulary.json"


def main():
    with urllib.request.urlopen(URL, timeout=60) as response:
        vocabulary = json.load(response)
    codes = [token[2:-1] for token in vocabulary if token.startswith("<2") and token.endswith(">")
             and re.fullmatch(r"[a-z]{2,3}(?:_[A-Z][a-z]{3})?(?:_[A-Z]{2})?", token[2:-1])]
    rows = []
    for code in codes:
        base = code.split("_")[0]
        country = pycountry.languages.get(alpha_2=base) or pycountry.languages.get(alpha_3=base)
        row = {"code": code}
        for language in ("en", "fr"):
            fallback = Locale(language).languages.get(base) or (country.name if country else base)
            fallback += (" (" + code.split("_", 1)[1] + ")") if "_" in code else ""
            try:
                name = Locale.parse(code).get_display_name(language) or fallback
            except (ValueError, LookupError, UnknownLocaleError):
                name = fallback
            row[language] = name[0].upper() + name[1:]
        rows.append(row)
    asr = sorted(set({"jw": "jv", "tl": "fil", "yue": "zh"}.get(code, code) for code in _LANGUAGE_CODES))
    data = {"repository": "santhosh/madlad400-3b-ct2", "revision": "c32ad0cf118807ea6258d14be137547155842723",
            "kind": "Language and script/region variants; control tokens excluded", "languages": rows,
            "asr_languages": asr}
    destination = ROOT / "src/data/translation_languages.json"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Generated {len(rows)} translation languages/variants and {len(asr)} normalized speech codes")


if __name__ == "__main__":
    main()
