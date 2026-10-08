# Language documentation inputs

These files document coverage and aggregate diagnostics. They are not runtime model files and do not change the installed application's catalogues.

- `omnilingual_languages.json`: all 1,672 official language/script/variety entries (1,650 distinct language codes) from Meta's `supported_langs`, revision `a7fb36017a46eee8953f76bd628c174d51aefeef`, checked on 2026-10-08. Four entries have additional variety suffixes, preserved verbatim. The publisher's file history contains this original list, unchanged since 2025-11-10; it is also linked from the pinned CTC v2 export's model card. Source URL and SHA-256 are preserved in the snapshot. The entries are coverage claims, not application validation results. Meta publishes its code/models under [Apache 2.0](https://github.com/facebookresearch/omnilingual-asr/blob/main/LICENSE).
- Language names are ISO names and available French translations from [pycountry 26.2.16](https://github.com/pycountry/pycountry), which uses the iso-codes databases, licensed LGPL 2.1 or later. Untranslated names remain in English. Names identify the official code; they do not imply equivalence between a macrolanguage and each of its varieties.
- `whisper_codes` records the 100 engine language IDs from the installed faster-whisper tokenizer. The application normalizes Javanese/Tagalog codes and merges Cantonese into the Chinese routing code. [OpenAI's authoritative language IDs](https://github.com/openai/whisper/blob/main/whisper/tokenizer.py) explain the model's own labels. The generation check compares normalized IDs with the application's speech catalogue.
- `language_diagnostics.json`: aggregate edit counts/reference lengths for 35 groups, two clips each, for Whisper large-v3 CUDA and Omnilingual CTC 1B v2 CPU. Each local report's SHA-256 is recorded. No audio, reference sentences, recognized text, translated text or private conversation is included. The [validation report](../VALIDATION_3.1.md) documents corpus sources, normalization, limitations and reproduction. Percentages are calculated from counts, not hand-entered scores. No semantic reliability or translation-accuracy percentage has been measured.

The current application JSON catalogues supply MADLAD's 452 translation tokens/variants and all 47 local voice choices. `src/models.py` supplies Qwen and Parakeet coverage. Regenerate the complete embedded README lists with:

```text
python scripts/generate_language_readme.py
python scripts/generate_language_readme.py --check
```

CI and desktop builds run `--check`. Refresh the publisher inventory and provenance deliberately when changing the pinned Omnilingual export. Keep recognition measurements attached to the exact tested model, corpus group and sample size. Do not transfer published 7B LLM benchmark scores to the application's 1B CTC model or convert CER into a probability of correct meaning.
